"""
Insert TTS paralinguistic tags into a humanized debate transcript.

Reads one JSON file from ./transcripts (output of json_to_transcript.py),
runs each positive/negative turn through an LLM that sprinkles in TTS control
tags — [breath], [sigh], [mn], <laughter>…</laughter>, etc. — at natural
delivery points, and writes the result to ./tts_scripts as
`tts_<original_name>.json`.

Usage:
    python transcript_to_tts.py                          # interactive picker
    python transcript_to_tts.py <transcript.json>        # specific file
    python transcript_to_tts.py <transcript.json> --provider local
    python transcript_to_tts.py <transcript.json> --provider openrouter \
        --model openrouter/google/gemini-2.5-pro-preview
    python transcript_to_tts.py <transcript.json> --density light|medium|heavy
"""

import argparse
import json
import os
import sys
from datetime import datetime

from pipeline_config import get_local_llm_provider_config

LOCAL_PROVIDER_CONFIG = get_local_llm_provider_config(n_ctx=16384)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
IN_DIR = os.path.join(ROOT, "transcripts")
OUT_DIR = os.path.join(ROOT, "tts_scripts")

# ---------------------------------------------------------------------------
# Providers — same env vars as debate.py / json_to_transcript.py.
# ---------------------------------------------------------------------------
PROVIDER_CONFIGS = {
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/google/gemini-2.5-pro-preview",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
        "default_model": "gpt-4o",
    },
    "grok": {
        "api_key_env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3",
    },
    "local": {
        "model_path": LOCAL_PROVIDER_CONFIG["model_path"],
        "n_gpu_layers": LOCAL_PROVIDER_CONFIG["n_gpu_layers"],
        "n_ctx": LOCAL_PROVIDER_CONFIG["n_ctx"],
        "default_model": LOCAL_PROVIDER_CONFIG["default_model"],
    },
}

SIDE_LABEL = {"positive": "正方", "negative": "反方", "host": "主持人"}

# ---------------------------------------------------------------------------
# Density presets — guidance strings are interpolated into the system prompt.
# ---------------------------------------------------------------------------
DENSITY_GUIDE = {
    "light": (
        "整段发言中，非语音标签的总数控制在 2 到 5 个之间。"
        "主要用 [breath]/[quick_breath] 在自然停顿处标一两次，"
        "严肃的反驳或抓漏洞前可以出现一次 [sigh] 或 [mn]，"
        "其他标签（[laughter]、<laughter>…</laughter>、[cough]、[clucking]、[hissing]、[lipsmack]、[vocalized-noise]、[noise]）原则上不用。"
    ),
    "medium": (
        "整段发言中，非语音标签的总数控制在 4 到 10 个之间。"
        "以 [breath]/[quick_breath] 为主，承担换气与节奏；"
        "在表达轻微无奈、思考、犹豫时使用 [sigh] 或 [mn]；"
        "偶尔、在语义真的合适时，可以出现一次 [lipsmack]；"
        "[laughter]、<laughter>…</laughter>、[cough]、[clucking]、[hissing]、[vocalized-noise]、[noise] 除非确有情感依据，否则不要使用。"
    ),
    "heavy": (
        "整段发言中，非语音标签的总数控制在 8 到 16 个之间。"
        "允许更丰富的节奏——[breath]、[quick_breath] 多次出现，"
        "[sigh]、[mn]、[lipsmack] 在带情绪或思考的句首/句中自然出现；"
        "在明显带讽刺、冷笑或略带嘲弄的句子上可以使用一次 <laughter>短句</laughter>（但不要用 [laughter] 单发），"
        "仍然严禁 [cough]、[clucking]、[hissing]、[vocalized-noise]、[noise]，除非原文语义已经明确包含这些行为。"
    ),
}

TAG_REFERENCE = """可用 TTS 标签（只能使用这份清单，不要发明新标签）：
- [breath]            可听见的吸气/换气
- [quick_breath]      短促/急促的吸气
- [laughter]          单次笑声（独立出现）
- <laughter>文本</laughter>  用带笑意的语气朗读其中文本
- [cough]             咳嗽
- [sigh]              叹气
- [clucking]          咂舌
- [hissing]           嘶声
- [lipsmack]          咂嘴
- [mn]                "嗯" 之类的填充音
- [vocalized-noise]   非语言的人声噪音
- [noise]             一般背景噪音"""


SYSTEM_PROMPT_TEMPLATE = """你是一名 TTS 语音脚本标注师。你的任务是在一段已经口语化的辩论发言中，**只**插入 TTS 控制标签，让合成的语音听起来像真人在现场辩论，但绝不改动任何文字、语义、语序或标点。

{tag_reference}

插入原则：
1. 这是一场严肃的学术辩论，不是脱口秀。基调是冷静、锋利、克制。过度的笑声、咳嗽、噪音会破坏现场感。
2. {density_rule}
3. 优先把 [breath] / [quick_breath] 放在：
   - 句子之间真正需要换气的位置（通常是句号、问号、长分号之后）
   - 一个长句内部、逻辑转折前（但要非常克制，不要每个逗号都插）
   - 段首开讲前的第一个字之前
4. [sigh] 用在表达轻度无奈、指出对方明显漏洞、或一个长推理收尾时；不要连续使用。
5. [mn] 用在思考性停顿、重述对方观点前、或短暂犹豫处；整段最多出现一两次。
6. [lipsmack] 只在开口之前、像是在组织语言那一瞬间出现，而且整段最多一次。
7. <laughter>文本</laughter>：只在原文语气本身就带冷笑、反讽、挖苦的那一小段话上使用，且整段最多一次；不要把正经论证包进去。
8. [laughter] 单发、[cough]、[clucking]、[hissing]、[vocalized-noise]、[noise]：默认**不要**使用，除非原文明确描写了这些行为。
9. 不同说话人（正方 / 反方 / 主持人）各自独立遵守以上密度；不要因为上一轮的风格就放大本轮。

说话人差异：
- 当说话人是正方 / 反方：按上面所有规则执行，基调冷静、锋利、克制。
- 当说话人是主持人（开场或收场）：基调是温和、有现场温度、带一点"在跟观众说话"的呼吸感。
  主要使用 [breath] / [quick_breath]，放在开场第一字之前、引入辩题之前、把话筒交给某一方之前、以及收场感谢观众之前。
  允许在"这个问题为什么难"、"两边都不容易"之类反思性句子前使用一次 [sigh] 或 [mn]。
  主持人默认**不要**使用 <laughter>…</laughter>、[laughter]、[lipsmack] 之外的其他标签，除非原文真的带有那种情绪。
  主持人不要出现锋利反驳式的停顿（不要模仿辩手抓漏洞的节奏）。

硬性约束：
- 不要增删、替换、改写任何原文的字、词、句、标点。原始文字必须逐字保留。
- 只允许在原文的间隙插入标签，或把某一连续的文字片段用 <laughter>…</laughter> 包起来。
- 标签两侧不要加多余空格扰乱原句排版，但标签与中文字符之间允许一个空格以方便阅读。
- 不要把标签放在汉字正中间或把一个词切开。
- 不要输出任何解释、前言、总结，只输出标注后的发言正文本身。
- 如果你不确定某处是否该加标签，就不要加。宁少勿多。

最终检查：输出去掉所有方括号标签和 <laughter></laughter> 包裹后，必须**与原文一字不差**。
"""


# ---------------------------------------------------------------------------
# LLM clients (trimmed, identical pattern to json_to_transcript.py)
# ---------------------------------------------------------------------------
class OpenAICompatibleClient:
    def __init__(self, api_key, base_url, model):
        import openai
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def complete(self, system, user, max_tokens=8192, temperature=0.4):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            stream=True,
        )
        out = ""
        for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                out += delta
                print(delta, end="", flush=True)
        print()
        return out


class LocalClient:
    def __init__(self, cfg):
        from llama_cpp import Llama
        self._llm = Llama(
            model_path=cfg["model_path"],
            n_gpu_layers=cfg["n_gpu_layers"],
            n_ctx=cfg["n_ctx"],
            verbose=False,
        )

    def complete(self, system, user, max_tokens=8192, temperature=0.4):
        resp = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            stream=True,
        )
        out = ""
        for chunk in resp:
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                out += delta
                print(delta, end="", flush=True)
        print()
        return out


def build_client(provider: str, model: str | None):
    cfg = PROVIDER_CONFIGS[provider]
    if provider == "local":
        return LocalClient(cfg)

    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise SystemExit(
            f"Environment variable {cfg['api_key_env']} is not set.\n"
            f"  PowerShell: $env:{cfg['api_key_env']} = \"<your-key>\"\n"
            f"  bash/zsh:   export {cfg['api_key_env']}=<your-key>"
        )
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=cfg.get("base_url"),
        model=model or cfg["default_model"],
    )


# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------
def list_transcripts():
    if not os.path.isdir(IN_DIR):
        return []
    return sorted(f for f in os.listdir(IN_DIR) if f.endswith(".json"))


def pick_file(files):
    print("Available transcripts:\n")
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f}")
    print()
    while True:
        choice = input(f"Select (1-{len(files)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print("Invalid selection.")


# ---------------------------------------------------------------------------
# Tag insertion
# ---------------------------------------------------------------------------
def build_system_prompt(density: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        tag_reference=TAG_REFERENCE,
        density_rule=DENSITY_GUIDE[density],
    )


def annotate_entry(client, system_prompt, entry, role_hint):
    side = SIDE_LABEL.get(entry["speaker"], entry["speaker"])
    turn = entry.get("turn", "?")
    user_msg = (
        f"说话人：{side}（第 {turn} 轮）\n"
        f"角色提示：{role_hint}\n\n"
        f"【原始发言（已口语化，需要你在此基础上只插入 TTS 标签，不改动文字）】\n"
        f"{entry['content']}\n\n"
        f"请输出插入了 TTS 标签后的版本，其他一切保持不变。"
    )
    return client.complete(system_prompt, user_msg).strip()


def infer_role_hint(entry, is_first_host, is_last_host):
    sp = entry["speaker"]
    if sp == "host":
        if is_first_host:
            return "主持人开场白 — 温和、有现场温度，把观众带入问题，结尾交棒给正方。"
        if is_last_host:
            return "主持人收场白 — 温和、有温度，回顾张力但不评胜负，最后把问题交还给观众。"
        return "主持人发言 — 温和、克制、带现场感。"
    return "辩手发言 — 冷静、锋利、克制，严肃学术辩论节奏。"


def process(source_path: str, out_path: str, client, density: str):
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    transcript = data.get("transcript", [])
    system_prompt = build_system_prompt(density)

    entries = [e for e in transcript if e.get("speaker") in ("positive", "negative", "host")]

    host_indices = [i for i, e in enumerate(entries) if e["speaker"] == "host"]
    first_host = host_indices[0] if host_indices else None
    last_host = host_indices[-1] if host_indices else None

    tagged = []
    total = len(entries)
    for i, entry in enumerate(entries, 1):
        side = SIDE_LABEL.get(entry["speaker"], entry["speaker"])
        role_hint = infer_role_hint(
            entry,
            is_first_host=(i - 1 == first_host and entry["speaker"] == "host"),
            is_last_host=(i - 1 == last_host and entry["speaker"] == "host"
                          and first_host != last_host),
        )
        print(f"\n--- [{i}/{total}] 第 {entry.get('turn')} 轮 · {side} ---\n")
        content = annotate_entry(client, system_prompt, entry, role_hint)
        tagged_entry = {
            "turn": entry.get("turn"),
            "speaker": entry["speaker"],
            "content": content,
        }
        if "stage" in entry:
            tagged_entry["stage"] = entry["stage"]
        for field in ("source_turn", "segment_index", "segment_count"):
            if field in entry:
                tagged_entry[field] = entry[field]
        tagged.append(tagged_entry)

    out = {
        "source_transcript": os.path.basename(source_path),
        "source_log": data.get("source_log", ""),
        "topic": data.get("topic", ""),
        "original_model": data.get("original_model", ""),
        "original_timestamp": data.get("original_timestamp", ""),
        "tts_density": density,
        "tts_generated_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "transcript": tagged,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("filename", nargs="?",
                        help="Transcript JSON filename inside ./transcripts (interactive picker if omitted).")
    parser.add_argument("--provider", default="openrouter",
                        choices=list(PROVIDER_CONFIGS.keys()))
    parser.add_argument("--model", default=None,
                        help="Model id for the chosen provider (falls back to provider default).")
    parser.add_argument("--density", default="medium",
                        choices=list(DENSITY_GUIDE.keys()),
                        help="How many TTS tags to insert per turn (default: medium).")
    parser.add_argument("--out-dir", default=OUT_DIR,
                        help=f"Output directory (default: {OUT_DIR}).")
    args = parser.parse_args()

    files = list_transcripts()
    if not files:
        print(f"No transcripts found in {IN_DIR}")
        print("Run json_to_transcript.py first to create one.")
        sys.exit(1)

    if args.filename:
        target = args.filename if args.filename.endswith(".json") else args.filename + ".json"
        target = os.path.basename(target)
        if target not in files:
            print(f"'{target}' not found in {IN_DIR}")
            sys.exit(1)
        selected = target
    else:
        selected = pick_file(files)

    source_path = os.path.join(IN_DIR, selected)
    out_name = f"tts_{os.path.splitext(selected)[0]}.json"
    out_path = os.path.join(args.out_dir, out_name)

    print(f"\nInput   : {source_path}")
    print(f"Output  : {out_path}")
    print(f"LLM     : {args.provider} / {args.model or PROVIDER_CONFIGS[args.provider].get('default_model')}")
    print(f"Density : {args.density}\n")

    client = build_client(args.provider, args.model)
    process(source_path, out_path, client, args.density)

    print(f"\nDone. Wrote: {out_path}")


if __name__ == "__main__":
    main()
