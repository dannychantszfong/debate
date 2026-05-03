"""
Humanize a debate JSON log into a natural spoken-style debate transcript.

Reads one JSON log from ./logs, runs each positive/negative turn through an LLM
to rewrite the rigid, markdown-heavy debater prose into how a real debater
would actually sound on stage, and writes the result to ./transcripts as
`debate_transcript_<original_name>.json`.

Usage:
    python json_to_transcript.py                       # interactive picker
    python json_to_transcript.py <logfile.json>        # specific file
    python json_to_transcript.py <logfile.json> --provider local
    python json_to_transcript.py <logfile.json> --provider openrouter --model openrouter/google/gemini-2.5-pro-preview
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

from pipeline_config import get_local_llm_provider_config

LOCAL_PROVIDER_CONFIG = get_local_llm_provider_config(n_ctx=16384)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")
OUT_DIR = os.path.join(ROOT, "transcripts")

# ---------------------------------------------------------------------------
# Providers — mirrors debate.py so you can use the same env vars.
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
FREE_DEBATE_MAX_SENTENCES_PER_POINT = 6
FREE_DEBATE_REWRITE_LIMIT = 8
FREE_DEBATE_EXCHANGE_REWRITE_LIMIT = 3

FREE_DEBATE_SCAFFOLDING_HEADINGS = {
    "具体场景",
    "制度后果",
    "制度/社会后果",
    "社会后果",
    "前提变化",
    "前提变化下的立场调整",
    "立场调整",
    "回到原题",
    "具体问题挑战",
    "总结与挑战",
    "核心问题",
    "最终挑战",
}

LEADING_BOILERPLATE_PATTERNS = (
    r"^好的[，,。]?\s*我(?:将|会|来)?(?:按照|按|根据)[^。！？!?\n]{0,120}"
    r"(?:组织回答|回答|展开|重写|处理|输出)[^。！？!?\n]{0,120}[。！？!?]?\s*",
    r"^好的[，,。]?\s*我将按要求组织回答[^。！？!?\n]{0,120}[。！？!?]?\s*",
    r"^以下是[^。！？!?\n]{0,80}(?:改写|重写|正文)[：:。]?\s*",
)

SYSTEM_PROMPT = """你是一名资深辩论赛速记员兼剪辑师。你的任务是把一份"像论文"的文字稿改写成一份"像真人在辩论现场讲话"的口述稿。

输入：某一轮辩手（正方或反方）在书面状态下写出的发言，通常带有：
- Markdown 格式（**加粗**、编号列表、小标题）
- 学术化的长句、堆砌术语、机械排比
- 过于工整的"首先/其次/最后"结构
- 内联的元层级标签、括号里的逻辑类别

输出：同一位辩手在真实辩论现场会怎么把这些话讲出来。保持其立场、论点、推理链、例子与质询问题不变，但让语言变得：
1. 自然、口语化、有呼吸感，像在说话而不是在排版
2. 带一点现场感：适度的停顿、短句、反问、强调、口头连接词（"那么"、"其实"、"我想说的是"、"先讲一点"），但不要滥用到像表演
3. 保留思辨的锋利与冷静，不要演讲腔，也不要寒暄奉承
4. 不使用任何 Markdown 语法（不要 **加粗**、不要编号列表、不要小标题、不要 Markdown 分隔线）
5. 段落可以长短错落，用空行分段，不要把一切挤成一整块；自由辩论阶段可以把原文拆成多次短促发言
6. 保留对手可引用的原话段落：如果原文有"你方上一轮的核心论断是……"这种引述，可以改成口语化的转述，但不要删除

现场协作（重点，严格遵守）：
- 如果提示说"这是立论发言"，请在发言一开始用一两句自然、简短的承接带入——例如"谢谢主持人"、"接着主持人刚才点出的冲突"之类，不要用"尊敬的各位"这种套话，也不要长篇寒暄；承接完必须明确说出你方立场是什么，再给出两到三个核心理由。
- 如果提示说"这是自由辩论发言"，你是在把一大段书面攻防剪成几次现场拿麦。必须短促、直接。原文只有一个攻防点时，就输出一个自然段；原文确实包含多个攻防点时，可以拆成多个自然段，每个自然段会被后续流程视为一次独立短发言。每个自然段只处理一个点，每个点最多六句话。可以压缩重复铺垫、合并同义表达、删掉书面转场，但不能删掉关键攻防点。不要写成长篇立论，不要把多个新方向混在同一个自然段里。
- 如果提示说"这是该辩手的收尾发言（closing statement）"，就不要再以追问或质询对手的方式结尾。把原文可能存在的"我的问题是……"之类的反问自然吸收进正文（例如转成"我方至今没有得到对方正面回应的是……"），然后让发言收在一个明确的收束上：重申立场、挑出本场最站得住脚的两到三个判断、落在一个有分量的结束句。语气是合上话筒前最后一段话，不要留悬念，也不要以问号结尾。

硬性约束：
- 不要改变立场、论点、例子的实质内容与顺序核心
- 不要新增原文没有的事实、案例、法条、引用
- 不要脱离原文另写总结。自由辩论阶段可以压缩重复铺垫和同义解释，但不能省略关键推理步骤
- 输出只包含改写后的发言正文本身，不要任何前言、标题、"以下是改写"之类的说明文字
- 不要输出"好的，我将按照本轮结构要求组织回答"、"我会按要求组织回答"这类元说明；第一句话必须直接进入观点或攻防
- 语言与原文一致（中文保持中文）

你是在让一份工整的"论文式发言"，还原成一位真正站在台上的辩手正在开口说的那段话。"""


HOST_SYSTEM_PROMPT = """你是一名资深辩论节目主持人。你的任务是基于一份完整的辩题分析框架，写出你在辩论正式开始前、站在现场亲口讲出来的开场白。

要求：
1. 口语化、有现场感。像一个真正在麦前讲话的人，不是在念稿。
2. 暖场：一两句话把观众带进这个问题，让他们感到"这和我有关"，不要一上来就抛术语。
3. 点题：清楚地说出今天的辩题、正反双方分别站在哪一边。
4. 指出痛点：说明为什么这个问题难、两边的价值撕裂在哪里、现实中人会在哪里感到为难。不要只复述定义，要把张力讲出来。
5. 搭台：交代本场流程是先由正反双方各自立论，讲清自己的立场；随后进入更短促的自由辩论；最后再收束。不要替他们把论证讲完。
6. 交棒：自然地把话筒交给正方开始第一轮立论。

硬性约束：
- 不使用任何 Markdown 语法，不要加粗、列表、小标题、分隔线。
- 不要综艺腔或煽情过头，保持认真、克制、带一点温度。
- 不要暴露你在"改写框架"——不要出现"根据资料"、"按照框架"这种话。
- 只输出主持人的开场白正文，不要任何解释、标题、前言。
- 语言与辩题原文一致（中文保持中文）。
- 控制在 300 到 500 字之间。"""


HOST_CLOSING_SYSTEM_PROMPT = """你是同一位资深辩论节目主持人。刚才正反双方已经结束了最后一轮发言，轮到你在现场讲一段收束发言，为这一场辩论画上句号。

你会拿到三段上下文：这场辩论你自己开场说过什么、正方的收尾发言、反方的收尾发言。你需要基于这些，亲口讲出你的收场白。

要求：
1. 口语化、有现场感，像一个人真的在麦前说话，不是在念稿。
2. 先用一两句话自然收住——比如"好，到这里正反双方的发言就告一段落"之类，但不要套话、不要客套寒暄。
3. 指出本场辩论真正碰到的那个张力点：两边到底在哪一刀上互不相让？把这个矛盾用观众能听懂的话重新讲一遍，让他们意识到这不是定义之争，而是价值之争。
4. 分别承认正方和反方各自讲到最站得住脚的那个地方是什么。两边都要有，篇幅大致相当，不要偏袒任何一方。
5. 明确地把问题交还给观众：告诉他们这场辩论并没有一个标准答案，真正要做决定的是每个人自己；指出他们走出这间屋子后，在现实生活里会在哪些时刻重新遇到这道题。
6. 收尾一句温和、有分量的感谢与告别，让这场辩论有"合上话筒"的感觉。

硬性约束（非常重要）：
- 绝对不要评价哪一方"赢了"、"更有说服力"、"更在理"、"漏洞更少"。不要排名、不要暗示胜负。
- 不要替任何一方继续论证，也不要补充他们没讲出的论点。
- 不要使用 Markdown（不要加粗、列表、小标题、分隔线）。
- 不要综艺腔、煽情腔、鸡汤腔。保持认真、克制、带一点温度。
- 不要暴露你在"改写文本"或"参考资料"。
- 只输出主持人的收场白正文，不要任何解释、标题、前言。
- 语言与上下文一致（中文保持中文）。
- 控制在 200 到 350 字之间。"""


FREE_DEBATE_EXCHANGE_SYSTEM_PROMPT = """你是一名资深辩论节目剪辑导演。你的任务不是继续润色单方稿件，而是把已经拆成短点的自由辩论稿，二次整理成真正的现场交锋。

你每次只处理一条发言。你会拿到：
- 辩题背景
- 当前说话方
- 对手刚刚说过的一条现场发言
- 当前说话方原本准备讲的这个攻防点

你的目标：
1. 保留当前攻防点的核心判断、理由和关键词。
2. 第一优先回应对手刚刚说的话：接住对方的关键词、反问、漏洞或前提，然后再推进当前点。
3. 可以压缩、删掉书面铺垫和重复定义；必要时可以把当前点的表达顺序微调成“回应 -> 反打 -> 追问”。
4. 不要新增原文没有的事实、案例、法条、引用或新的论证方向。

硬性约束：
- 输出只包含当前这一条发言，不要标题、说明、列表、编号或 Markdown。
- 最多六句话，最好两到四句话。
- 必须保持当前说话方的阵营立场：正方支持辩题命题，反方反对辩题命题。绝对不要替对方完成论证。
- 如果当前攻防点是在转述对方观点，必须明确这是“对方说”，随后立刻反驳；不要把转述内容当成己方结论。
- 如果当前攻防点本身出现阵营漂移，必须把漂移内容改写成“对方前提”并反驳，不能照搬成己方立场。
- 第一句话必须直接接住对手刚刚的关键词或问题；不要用“我补充一点”“接下来我讲”这种自说自话开头。
- 不要复述对手整段话，只抓一个最关键的词或前提。
- 不要把多个自然段输出出来，这一条就是一次现场拿麦。
- 语气要像辩手在自由辩论中短促回应，不要像结辩、论文或主持人总结。"""


# ---------------------------------------------------------------------------
# LLM clients — slim versions of what debate.py uses.
# ---------------------------------------------------------------------------
class OpenAICompatibleClient:
    def __init__(self, api_key, base_url, model):
        import openai
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def complete(self, system, user, max_tokens=8192, temperature=0.7):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
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

    def complete(self, system, user, max_tokens=8192, temperature=0.7):
        resp = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
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
def list_logs():
    if not os.path.isdir(LOG_DIR):
        return []
    return sorted(f for f in os.listdir(LOG_DIR) if f.endswith(".json"))


def pick_log(files):
    print("Available logs:\n")
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f}")
    print()
    while True:
        choice = input(f"Select (1-{len(files)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print("Invalid selection.")


# ---------------------------------------------------------------------------
# Humanization
# ---------------------------------------------------------------------------
def infer_stage(is_opening: bool, is_closing: bool) -> str:
    """Map a debater entry to the video/transcript stage."""
    if is_opening:
        return "constructive"
    if is_closing:
        return "closing"
    return "free_debate"


def split_sentences(text: str) -> list[str]:
    """Best-effort sentence splitter for Chinese-heavy spoken text."""
    if not text:
        return []
    chunks = re.findall(r"[^。！？!?]+[。！？!?]?", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


def strip_leading_boilerplate(text: str) -> str:
    """Remove model meta-openers that should not become spoken content."""
    out = (text or "").strip()
    while out:
        updated = out
        for pattern in LEADING_BOILERPLATE_PATTERNS:
            updated = re.sub(pattern, "", updated, count=1).lstrip()
        if updated == out:
            return out
        out = updated
    return out


def _strip_markdown_markup(line: str) -> str:
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    line = re.sub(r"\$(.*?)\$", r"\1", line)
    line = line.replace(r"\rightarrow", "到")
    return line


def _strip_scaffolding_prefix(line: str) -> str:
    labels = "|".join(re.escape(label) for label in sorted(
        FREE_DEBATE_SCAFFOLDING_HEADINGS,
        key=len,
        reverse=True,
    ))
    return re.sub(rf"^({labels})[：:]\s*", "", line).strip()


def _is_scaffolding_line(line: str) -> bool:
    cleaned = _strip_markdown_markup(line)
    cleaned = re.sub(r"^[\s\-*#>]+", "", cleaned)
    cleaned = re.sub(r"^\d+[.、）)]\s*", "", cleaned)
    cleaned = cleaned.strip().strip("：:。")
    return cleaned in FREE_DEBATE_SCAFFOLDING_HEADINGS


def normalize_free_debate_text(text: str) -> str:
    """Normalize free-debate output before validation/TTS handoff."""
    text = strip_leading_boilerplate(text)
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue

        line = re.sub(r"^\s*[-*]\s+", "", line)
        line = re.sub(r"^\s*\d+[.、]\s*", "", line)
        line = re.sub(r"^\s*[（(]?\d+[）)]\s*", "", line)
        line = _strip_markdown_markup(line).strip()

        if _is_scaffolding_line(line):
            if lines and lines[-1] != "":
                lines.append("")
            continue

        line = _strip_scaffolding_prefix(line)
        line = re.sub(r"^(谢谢主持人|谢谢)[，,。.!！\s]+", "", line).strip()
        if line:
            lines.append(line)

    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return normalized


def split_free_debate_points(text: str) -> list[str]:
    normalized = normalize_free_debate_text(text)
    if not normalized:
        return []
    return [
        part.strip()
        for part in re.split(r"\n\s*\n+", normalized)
        if part.strip()
    ]


def interleave_free_debate_segments(entries: list[dict]) -> list[dict]:
    """Alternate same-turn positive/negative free-debate chunks for live rhythm."""
    if not entries:
        return []

    turn_order: list[object] = []
    by_turn: dict[object, list[dict]] = {}
    for entry in entries:
        key = entry.get("source_turn", entry.get("turn"))
        if key not in by_turn:
            turn_order.append(key)
            by_turn[key] = []
        by_turn[key].append(entry)

    out: list[dict] = []
    for key in turn_order:
        group = by_turn[key]
        by_side = {"positive": [], "negative": []}
        others: list[dict] = []
        for entry in group:
            speaker = entry.get("speaker")
            if speaker in by_side:
                by_side[speaker].append(entry)
            else:
                others.append(entry)

        if not by_side["positive"] or not by_side["negative"]:
            out.extend(group)
            continue

        first_speaker = next(
            entry["speaker"]
            for entry in group
            if entry.get("speaker") in ("positive", "negative")
        )
        side_order = (
            ("positive", "negative")
            if first_speaker == "positive"
            else ("negative", "positive")
        )
        max_segments = max(len(by_side["positive"]), len(by_side["negative"]))
        for i in range(max_segments):
            for side in side_order:
                if i < len(by_side[side]):
                    out.append(by_side[side][i])
        out.extend(others)

    return out


def free_debate_point_sentence_counts(text: str) -> list[int]:
    return [count_sentences(point) for point in split_free_debate_points(text)]


def free_debate_limit_report(text: str) -> str:
    counts = free_debate_point_sentence_counts(text)
    if not counts:
        return "0 points"
    return f"{len(counts)} points, max={max(counts)}, counts={counts}"


def free_debate_is_within_limits(text: str) -> bool:
    counts = free_debate_point_sentence_counts(text)
    return bool(counts) and max(counts) <= FREE_DEBATE_MAX_SENTENCES_PER_POINT


def enforce_free_debate_point_limit(text: str) -> str:
    """Last-resort engineering fallback: split overlong points into <=6 sentence chunks."""
    chunks: list[str] = []
    for point in split_free_debate_points(text):
        sentences = split_sentences(point)
        if len(sentences) <= FREE_DEBATE_MAX_SENTENCES_PER_POINT:
            chunks.append(point.strip())
            continue
        for i in range(0, len(sentences), FREE_DEBATE_MAX_SENTENCES_PER_POINT):
            chunk = "".join(sentences[i:i + FREE_DEBATE_MAX_SENTENCES_PER_POINT]).strip()
            if chunk:
                chunks.append(chunk)
    return "\n\n".join(chunk for chunk in chunks if chunk)


def normalize_free_debate_exchange_text(text: str) -> str:
    """Normalize one already-split free-debate exchange turn."""
    points = split_free_debate_points(text)
    if not points:
        return normalize_free_debate_text(text)
    # The exchange pass handles exactly one microphone turn, so collapse any
    # accidental multi-paragraph output back into a single short utterance.
    return " ".join(point.strip() for point in points if point.strip()).strip()


def enforce_single_exchange_limit(text: str) -> str:
    sentences = split_sentences(normalize_free_debate_exchange_text(text))
    if len(sentences) <= FREE_DEBATE_MAX_SENTENCES_PER_POINT:
        return "".join(sentences).strip()
    return "".join(sentences[:FREE_DEBATE_MAX_SENTENCES_PER_POINT]).strip()


def free_debate_exchange_is_within_limits(text: str) -> bool:
    sentences = split_sentences(normalize_free_debate_exchange_text(text))
    return bool(sentences) and len(sentences) <= FREE_DEBATE_MAX_SENTENCES_PER_POINT


def generate_host_opening(client, topic_raw: str) -> str:
    """One-shot: turn the full topic framework into a spoken host opening."""
    user_msg = (
        f"【辩题分析框架（完整资料，仅供你理解背景与张力，不要照抄）】\n"
        f"{topic_raw}\n\n"
        f"请输出主持人的现场开场白正文。字数 300~500，说明流程：正反双方先立论，"
        f"随后进入每次最多六句话的自由辩论，最后收束。收尾处自然地把话筒交给正方。"
    )
    return client.complete(HOST_SYSTEM_PROMPT, user_msg).strip()


def generate_host_free_debate_intro() -> str:
    """Deterministic host bridge between constructive speeches and short-form clash."""
    return (
        "好，双方的基本立场已经摆出来了。接下来我们进入自由辩论。"
        "从这里开始，请两边不要再完整重写自己的立论，而是抓住对方刚才最关键的一点，"
        "短一点、直接一点，一来一回把问题打清楚。"
    )


def generate_host_closing(client, host_opening: str,
                          positive_closing: str, negative_closing: str) -> str:
    """Produce a neutral host wrap-up anchored in what was actually said."""
    parts = []
    if host_opening:
        parts.append(f"【你自己的开场白（刚才你就是这样开场的）】\n{host_opening}")
    if positive_closing:
        parts.append(f"【正方刚刚的收尾发言】\n{positive_closing}")
    if negative_closing:
        parts.append(f"【反方刚刚的收尾发言】\n{negative_closing}")
    user_msg = (
        "\n\n".join(parts)
        + "\n\n请输出主持人的现场收场白正文。字数 200~350。"
          "记住：不评价胜负，两边各自承认一次最站得住脚的地方，最后把问题交还给观众并自然收束。"
    )
    return client.complete(HOST_CLOSING_SYSTEM_PROMPT, user_msg).strip()


def rewrite_free_debate_exchange_entry(client, topic_hint: str, entry: dict,
                                       opponent_entry: dict | None,
                                       same_side_entry: dict | None) -> str:
    """Rewrite one split/interleaved free-debate point into an actual reply."""
    side = SIDE_LABEL.get(entry["speaker"], entry["speaker"])
    if entry.get("speaker") == "positive":
        side_constraint = (
            "你是正方，必须支持辩题命题，也就是维护女性身体自主权优先。"
            "你的典型反打方向是：胎儿生命权不能只凭“存在本身”自动压过女性主体性。"
            "你可以转述反方观点，但必须把它作为要反驳的对象。"
            "你的输出不能得出“胎儿生命权应优先”的结论。"
        )
    elif entry.get("speaker") == "negative":
        side_constraint = (
            "你是反方，必须反对辩题命题，也就是维护胎儿生命权优先。"
            "你的典型反打方向是：身体自主权不能只凭“主体性”自动压过生命的基础价值。"
            "你可以转述正方观点，但必须把它作为要反驳的对象。"
            "你的输出不能得出“女性身体自主权应优先”的结论。"
        )
    else:
        side_constraint = "必须保持当前说话方原有立场。"

    opponent_label = "对手"
    opponent_text = "这是自由辩论的第一下发言。请直接抛出一个可被对方接住的攻防点。"
    if opponent_entry:
        opponent_label = SIDE_LABEL.get(opponent_entry["speaker"], opponent_entry["speaker"])
        opponent_text = opponent_entry.get("content", "")

    same_side_block = ""
    if same_side_entry:
        same_side_stage = same_side_entry.get("stage")
        same_side_label = (
            "你方上一条自由辩论发言（供你避免重复，不要复述）"
            if same_side_stage == "free_debate"
            else "你方基本立场材料（只用于防止站错边，不要复述）"
        )
        same_side_text = same_side_entry.get("content", "")
        same_side_block = f"\n【{same_side_label}】\n{same_side_text[:900]}\n"

    user_msg = (
        f"辩题背景（极简提示，仅供定位，不要照搬）：\n{topic_hint}\n\n"
        f"当前说话方：{side}\n\n"
        f"【阵营锁定】\n{side_constraint}\n\n"
        f"【{opponent_label}刚刚说过的话】\n{opponent_text}\n"
        f"{same_side_block}\n"
        f"【当前说话方原本准备讲的攻防点】\n{entry.get('content', '')}\n\n"
        "请把“当前说话方原本准备讲的攻防点”改写成真正接住对方上一句话的自由辩论发言。"
        "只输出这一条发言正文。"
    )

    rewritten = client.complete(
        FREE_DEBATE_EXCHANGE_SYSTEM_PROMPT,
        user_msg,
        max_tokens=1024,
        temperature=0.45,
    ).strip()
    rewritten = normalize_free_debate_exchange_text(rewritten)

    rewrite_count = 0
    while not free_debate_exchange_is_within_limits(rewritten):
        if rewrite_count >= FREE_DEBATE_EXCHANGE_REWRITE_LIMIT:
            fallback = enforce_single_exchange_limit(rewritten)
            print(
                "[free_debate_exchange] 达到重写上限，启用单条发言裁剪："
                f"{count_sentences(rewritten)} -> {count_sentences(fallback)}"
            )
            return fallback

        rewrite_count += 1
        print(
            f"[free_debate_exchange] 第 {rewrite_count}/{FREE_DEBATE_EXCHANGE_REWRITE_LIMIT} 次重写："
            f"{count_sentences(rewritten)} 句，限制 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句"
        )
        retry_msg = (
            f"{user_msg}\n\n"
            f"【上一版输出不符合限制：必须是一条发言，最多 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句话】\n"
            f"{rewritten}\n\n"
            "请压缩重写。第一句话仍然要接住对手刚刚说的话；不要分段，不要列表，不要解释。"
        )
        rewritten = client.complete(
            FREE_DEBATE_EXCHANGE_SYSTEM_PROMPT,
            retry_msg,
            max_tokens=768,
            temperature=0.35,
        ).strip()
        rewritten = normalize_free_debate_exchange_text(rewritten)

    return rewritten


def rewrite_free_debate_exchange_segments(client, topic_hint: str,
                                          entries: list[dict],
                                          seed_contexts: dict[str, dict] | None = None) -> list[dict]:
    """Make interleaved free-debate segments respond to the previous opponent."""
    if not entries:
        return []

    last_by_side = dict(seed_contexts or {})
    out: list[dict] = []
    for index, entry in enumerate(entries, 1):
        side = entry.get("speaker")
        opponent = "negative" if side == "positive" else "positive"
        opponent_entry = last_by_side.get(opponent)
        same_side_entry = last_by_side.get(side)

        print(
            f"[free_debate_exchange] {index}/{len(entries)} "
            f"{SIDE_LABEL.get(side, side)} 接招重写"
        )
        rewritten = rewrite_free_debate_exchange_entry(
            client,
            topic_hint,
            entry,
            opponent_entry,
            same_side_entry,
        )
        new_entry = dict(entry)
        new_entry["content_before_exchange_rewrite"] = entry.get("content", "")
        new_entry["content"] = rewritten
        new_entry["exchange_rewritten"] = True
        out.append(new_entry)
        if side in ("positive", "negative"):
            last_by_side[side] = new_entry

    return out


def humanize_entry(client, topic_hint, entry, prev_humanized,
                   host_opening=None, stage="free_debate"):
    side = SIDE_LABEL.get(entry["speaker"], entry["speaker"])
    turn = entry.get("turn", "?")

    role_notes = []
    if stage == "constructive":
        role_notes.append(
            "这是立论发言。请在开头用一两句自然、简短的承接带入"
            "（例如'谢谢主持人'或顺着主持人刚才点出的冲突往下说），不要寒暄客套，"
            "承接完必须明确讲清楚你方立场是什么，并用两到三个核心理由完成立论。"
        )
    elif stage == "closing":
        role_notes.append(
            "这是该辩手的收尾发言（closing statement）。不要以追问或质询对手的方式结尾。"
            "把原文里可能存在的'我的问题是……'之类反问，自然吸收进正文。"
            "结尾必须落在一个明确的收束上：重申立场、挑出本场最站得住脚的判断、"
            "给出一个有分量的结束句，不要以问号结尾，也不要留悬念。"
        )
    else:
        role_notes.append(
            f"这是自由辩论发言。必须直面对手上一轮，像现场攻防一样短促、锋利。"
            "你不是在保留一个完整书面回合，而是在把它剪成若干次观众能听懂的现场拿麦。"
            "如果原文只有一个攻防点，就输出一个自然段；如果原文确实有多个攻防点，"
            "可以拆成多个自然段，每个自然段只处理一个点，后续流程会把每个自然段拆成一次独立短发言。"
            f"每个点最多 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句话，"
            "可以少于六句，也可以是两三句；总句数可以超过六句。"
            "允许压缩重复铺垫、删掉书面转场、合并同义解释；不要写成长篇立论，不要同时把三四条新线塞进同一个自然段。"
            "不要输出'好的，我将按照本轮结构要求组织回答'这类元说明，第一句话直接进入攻防。"
        )
    role_block = "【本轮角色提示】\n" + "\n".join(f"- {n}" for n in role_notes)

    host_block = ""
    if stage == "constructive" and host_opening:
        host_block = (
            f"\n【主持人刚才的开场白（供你自然承接，不要复述它）】\n{host_opening}\n"
        )

    prev_block = ""
    if prev_humanized and prev_humanized.get("speaker") != "host":
        prev_label = SIDE_LABEL.get(prev_humanized["speaker"], prev_humanized["speaker"])
        prev_block = (
            f"\n【对手上一轮已经口述化的发言（仅供你判断上下文，不要复述它）】\n"
            f"{prev_label}：\n{prev_humanized['content']}\n"
        )

    user_msg = (
        f"辩题背景（极简提示，仅供定位，不要照搬）：\n{topic_hint}\n\n"
        f"当前发言：第 {turn} 轮，{side}，阶段：{stage}\n\n"
        f"{role_block}\n"
        f"{host_block}"
        f"{prev_block}\n"
        f"【需要口述化改写的原始书面发言】\n{entry['content']}\n\n"
        f"请输出这段发言的口述版本（只输出正文，不要任何说明）。"
    )
    rewritten = client.complete(SYSTEM_PROMPT, user_msg).strip()
    if stage == "free_debate":
        rewritten = normalize_free_debate_text(rewritten)

    if stage == "free_debate":
        rewrite_count = 0
        while not free_debate_is_within_limits(rewritten):
            if rewrite_count >= FREE_DEBATE_REWRITE_LIMIT:
                fallback = enforce_free_debate_point_limit(rewritten)
                print(
                    "[free_debate_limit] 达到重写上限，启用工程兜底切分："
                    f"{free_debate_limit_report(rewritten)} -> "
                    f"{free_debate_limit_report(fallback)}"
                )
                return fallback

            rewrite_count += 1
            print(
                f"[free_debate_limit] 第 {rewrite_count}/{FREE_DEBATE_REWRITE_LIMIT} 次重写："
                f"{free_debate_limit_report(rewritten)}，"
                f"每点限制 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句"
            )
            retry_msg = (
                f"{user_msg}\n\n"
                f"【上一版输出仍然不符合每个攻防点最多 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句话的限制，必须重写】\n"
                f"{rewritten}\n\n"
                "请重写为一个或多个自然段。每个自然段只讲一个攻防点，"
                f"每个自然段最多 {FREE_DEBATE_MAX_SENTENCES_PER_POINT} 句话。"
                "如果原文有多个点，可以拆成多个自然段；不要为了卡总句数而删掉关键点。"
                "必须删掉铺垫、标题、编号、Markdown 和'好的，我将按照本轮结构要求组织回答'这类元说明。"
                "输出只包含重写后的正文，不要解释，不要列清单，第一句话直接进入观点。"
            )
            rewritten = client.complete(
                SYSTEM_PROMPT,
                retry_msg,
                max_tokens=2048,
                temperature=0.4,
            ).strip()
            rewritten = normalize_free_debate_text(rewritten)

    return rewritten


def extract_topic_hint(topic_raw: str, max_chars: int = 400) -> str:
    """Grab the first real sentence/headline of the topic block, not the whole framework."""
    if not topic_raw:
        return ""
    # Pull the first non-empty line that isn't a pure markdown heading marker.
    for line in topic_raw.splitlines():
        s = line.strip().lstrip("#").strip()
        if s and not s.startswith("【") and len(s) > 4:
            return s[:max_chars]
    return topic_raw.strip()[:max_chars]


def process(
    source_path: str,
    out_path: str,
    client,
    *,
    split_free_debate: bool = True,
    interleave_free_debate: bool = True,
    rewrite_free_debate_exchanges: bool = True,
    add_free_debate_intro: bool = True,
):
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    transcript = data.get("transcript", [])
    topic_raw = data.get("topic", "")
    topic_hint = extract_topic_hint(topic_raw)

    debate_entries = [e for e in transcript if e.get("speaker") in ("positive", "negative")]

    # Track each side's first and last appearance in the surviving debate_entries.
    first_idx_per_side, last_idx_per_side = {}, {}
    for i, e in enumerate(debate_entries):
        side = e["speaker"]
        first_idx_per_side.setdefault(side, i)
        last_idx_per_side[side] = i

    humanized = []

    # --- Host opening -------------------------------------------------------
    print("\n--- [host] 主持人开场白 ---\n")
    host_opening = generate_host_opening(client, topic_raw) if topic_raw else ""
    if host_opening:
        humanized.append({
            "turn": 0,
            "speaker": "host",
            "stage": "host_opening",
            "content": host_opening,
        })

    # --- Debater turns ------------------------------------------------------
    prev_human = None
    free_debate_intro_inserted = False
    free_debate_buffer: list[dict] = []

    def flush_free_debate_buffer():
        nonlocal free_debate_buffer
        if not free_debate_buffer:
            return
        if interleave_free_debate:
            ordered = interleave_free_debate_segments(free_debate_buffer)
        else:
            ordered = list(free_debate_buffer)

        if rewrite_free_debate_exchanges:
            seed_contexts: dict[str, dict] = {}
            for existing in humanized:
                speaker = existing.get("speaker")
                if speaker in ("positive", "negative"):
                    seed_contexts[speaker] = existing
            ordered = rewrite_free_debate_exchange_segments(
                client,
                topic_hint,
                ordered,
                seed_contexts=seed_contexts,
            )

        humanized.extend(ordered)
        free_debate_buffer = []

    total = len(debate_entries)
    for i, entry in enumerate(debate_entries, 1):
        side_key = entry["speaker"]
        side = SIDE_LABEL.get(side_key, side_key)
        is_opening = (i - 1) == first_idx_per_side.get(side_key)
        is_closing = (i - 1) == last_idx_per_side.get(side_key)
        stage = infer_stage(is_opening, is_closing)
        if stage != "free_debate":
            flush_free_debate_buffer()
        tag = []
        tag.append(stage)
        tag_str = f" [{'+'.join(tag)}]" if tag else ""
        print(f"\n--- [{i}/{total}] 第 {entry.get('turn')} 轮 · {side}{tag_str} ---\n")

        if (
            stage == "free_debate"
            and add_free_debate_intro
            and not free_debate_intro_inserted
        ):
            bridge = {
                "turn": entry.get("turn"),
                "speaker": "host",
                "stage": "host_free_debate_intro",
                "content": generate_host_free_debate_intro(),
            }
            humanized.append(bridge)
            free_debate_intro_inserted = True

        rewritten = humanize_entry(
            client, topic_hint, entry, prev_human,
            host_opening=host_opening,
            stage=stage,
        )
        if stage == "free_debate" and split_free_debate:
            points = split_free_debate_points(rewritten) or [rewritten]
            for segment_index, point in enumerate(points, 1):
                new_entry = {
                    "turn": entry.get("turn"),
                    "source_turn": entry.get("turn"),
                    "speaker": side_key,
                    "stage": stage,
                    "segment_index": segment_index,
                    "segment_count": len(points),
                    "content": point,
                }
                free_debate_buffer.append(new_entry)
                prev_human = new_entry
        else:
            new_entry = {
                "turn": entry.get("turn"),
                "source_turn": entry.get("turn"),
                "speaker": side_key,
                "stage": stage,
                "content": rewritten,
            }
            humanized.append(new_entry)
            prev_human = new_entry

    flush_free_debate_buffer()

    # --- Host closing -------------------------------------------------------
    pos_closing, neg_closing = "", ""
    for e in humanized:
        if e["speaker"] == "positive":
            pos_closing = e["content"]
        elif e["speaker"] == "negative":
            neg_closing = e["content"]
    if pos_closing or neg_closing:
        print("\n--- [host] 主持人收场白 ---\n")
        host_closing = generate_host_closing(
            client, host_opening, pos_closing, neg_closing
        )
        if host_closing:
            debate_turns = [e["turn"] for e in humanized
                            if e["speaker"] != "host" and isinstance(e["turn"], int)]
            closing_turn = (max(debate_turns) + 1) if debate_turns else 0
            humanized.append({
                "turn": closing_turn,
                "speaker": "host",
                "stage": "host_closing",
                "content": host_closing,
            })

    out = {
        "source_log": os.path.basename(source_path),
        "topic": topic_raw,
        "original_model": data.get("model", ""),
        "original_timestamp": data.get("timestamp", ""),
        "original_version": data.get("version", ""),
        "turns": data.get("turns", len({e["turn"] for e in humanized if e["speaker"] != "host"})),
        "transcript_entries": len(humanized),
        "split_free_debate": split_free_debate,
        "interleave_free_debate": interleave_free_debate,
        "rewrite_free_debate_exchanges": rewrite_free_debate_exchanges,
        "transcription_generated_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "transcript": humanized,
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
                        help="JSON log filename inside ./logs (interactive picker if omitted).")
    parser.add_argument("--provider", default="openrouter",
                        choices=list(PROVIDER_CONFIGS.keys()))
    parser.add_argument("--model", default=None,
                        help="Model id for the chosen provider (falls back to provider default).")
    parser.add_argument("--out-dir", default=OUT_DIR,
                        help=f"Output directory (default: {OUT_DIR}).")
    parser.add_argument("--split-free-debate", dest="split_free_debate",
                        action="store_true", default=True,
                        help="Split free-debate paragraphs into separate short transcript entries (default).")
    parser.add_argument("--no-split-free-debate", dest="split_free_debate",
                        action="store_false",
                        help="Keep each original free-debate speaker turn as one transcript entry.")
    parser.add_argument("--interleave-free-debate", dest="interleave_free_debate",
                        action="store_true", default=True,
                        help="Alternate same-turn positive/negative free-debate chunks after splitting (default).")
    parser.add_argument("--no-interleave-free-debate", dest="interleave_free_debate",
                        action="store_false",
                        help="Keep split free-debate chunks in original speaker-block order.")
    parser.add_argument("--rewrite-free-debate-exchanges", dest="rewrite_free_debate_exchanges",
                        action="store_true", default=True,
                        help="After splitting/interleaving, rewrite each free-debate chunk to respond to the previous opponent chunk (default).")
    parser.add_argument("--no-rewrite-free-debate-exchanges", dest="rewrite_free_debate_exchanges",
                        action="store_false",
                        help="Skip the second-pass exchange rewrite and keep split chunks as-is.")
    parser.add_argument("--host-free-debate-intro", dest="host_free_debate_intro",
                        action="store_true", default=True,
                        help="Insert a host bridge before the first free-debate exchange (default).")
    parser.add_argument("--no-host-free-debate-intro", dest="host_free_debate_intro",
                        action="store_false",
                        help="Do not insert the host bridge before free debate.")
    args = parser.parse_args()

    files = list_logs()
    if not files:
        print(f"No JSON logs found in {LOG_DIR}")
        sys.exit(1)

    if args.filename:
        target = args.filename if args.filename.endswith(".json") else args.filename + ".json"
        target = os.path.basename(target)
        if target not in files:
            print(f"'{target}' not found in {LOG_DIR}")
            sys.exit(1)
        selected = target
    else:
        selected = pick_log(files)

    source_path = os.path.join(LOG_DIR, selected)
    out_name = f"debate_transcript_{os.path.splitext(selected)[0]}.json"
    out_path = os.path.join(args.out_dir, out_name)

    print(f"\nInput : {source_path}")
    print(f"Output: {out_path}")
    print(f"LLM   : {args.provider} / {args.model or PROVIDER_CONFIGS[args.provider].get('default_model')}\n")

    client = build_client(args.provider, args.model)
    process(
        source_path,
        out_path,
        client,
        split_free_debate=args.split_free_debate,
        interleave_free_debate=args.interleave_free_debate,
        rewrite_free_debate_exchanges=args.rewrite_free_debate_exchanges,
        add_free_debate_intro=args.host_free_debate_intro,
    )

    print(f"\nDone. Wrote: {out_path}")


if __name__ == "__main__":
    main()
