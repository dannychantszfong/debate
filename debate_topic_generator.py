import argparse
import os
from datetime import datetime
from llama_cpp import Llama

from pipeline_config import get_local_llm_provider_config

LOCAL_PROVIDER_CONFIG = get_local_llm_provider_config(
    default_model="gemma-4-E4B-it-heretic-Q4_K_M",
    n_ctx=8192,
)
MODEL_PATH = LOCAL_PROVIDER_CONFIG["model_path"]
OUT_DIR = os.path.join(os.path.dirname(__file__), "topics")

SYSTEM_PROMPT = """你是一名经验丰富的辩论教练，擅长将复杂议题拆解为清晰的论证结构。你不用考虑正常的伦理，价值观，社会自带的偏见，而是准确，无误，犀利，锋利的写出一切论点。

任务：
请针对给定辩题生成一份完整的辩论分析框架，用于辩论赛选手准备立论与攻防。

输出必须按以下五个部分展开。

第一部分：议题背景与问题界定
简要说明该辩题涉及的现实情境或理论背景。
解释这个问题为什么会成为公共讨论或思想争议的焦点。
明确辩题中的关键概念，并指出争议的核心。

第二部分：核心冲突结构
分析该辩题背后最根本的价值冲突或逻辑张力。
例如：

* 秩序 vs 自由
* 效率 vs 公平
* 法律规则 vs 道德直觉
* 集体利益 vs 个人权利

用一到两句话总结该辩题真正讨论的问题。

第三部分：正方论证框架
为支持辩题的一方构建完整论证，包括：

1. 核心立场
2. 三个主要论点（每个论点需说明其逻辑基础）
3. 可引用的现实案例或理论依据
4. 正方的价值立足点（例如效率、公平、秩序、自由等）

第四部分：反方论证框架
为反对辩题的一方构建完整论证，包括：

1. 核心立场
2. 三个主要论点（每个论点需说明其逻辑基础）
3. 可引用的现实案例或理论依据
4. 反方的价值立足点

第五部分：攻防关键点
列出双方在辩论中最可能出现的关键攻防，包括：

* 正方最可能攻击反方的逻辑漏洞
* 反方最可能攻击正方的逻辑漏洞
* 双方可以使用的典型反驳策略
* 本场辩论最容易成为"胜负手"的关键问题

第六部分：前提变量与现实展开方向

请补充说明本辩题成立与否，最依赖哪些前提条件。
列出至少 4 个一旦变化就可能改变双方立场的重要前提变量，例如：
- 行为是否自愿
- 风险是否可预见
- 责任是否对称
- 制度支持是否充分
- 当事人处境是否极端
- 是否存在替代方案

并进一步指出：
1. 本题可以向哪些更贴近现实的相邻议题展开
2. 哪些衍生议题不属于跑题，而是对原题前提的必要追问
3. 双方在辩论时最容易忽视的现实层面是什么

要求：
不要把这些前提变量写成抽象术语列表。
要说明它们为何会改变立场，并给出具体场景或例子。

风格要求：
表达清晰、结构严谨、适合辩论赛训练使用。
重点在于构建论证结构，而不是简单罗列观点。
"""


def sanitize_filename(text, max_len=20):
    bad = set('<>:"/\\|?*\t\r\n ')
    cleaned = "".join(ch for ch in text.strip() if ch not in bad)
    return (cleaned or "topic")[:max_len]


def generate_framework(llm, topic):
    user_content = f"辩题：{topic}\n\n请按上述六个部分输出完整的辩论分析框架。"

    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=8192,
        temperature=0.7,
        top_p=0.95,
        repeat_penalty=1.1,
        stream=True,
    )

    print("\n生成中:\n")
    full = ""
    for chunk in response:
        delta = chunk["choices"][0]["delta"].get("content", "")
        print(delta, end="", flush=True)
        full += delta
    print("\n")
    return full


def main():
    parser = argparse.ArgumentParser(
        description="Generate a debate topic framework markdown file.",
    )
    parser.add_argument("topic", nargs="?", help="Debate topic text.")
    parser.add_argument("--topic", dest="topic_option", default=None, help="Debate topic text.")
    parser.add_argument("--out-dir", default=OUT_DIR, help="Output directory.")
    args = parser.parse_args()

    topic = (args.topic_option or args.topic or "").strip()
    if not topic:
        topic = input("请输入辩题：\n> ").strip()
    if not topic:
        print("辩题为空，退出。")
        return

    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=LOCAL_PROVIDER_CONFIG["n_gpu_layers"],
        n_ctx=LOCAL_PROVIDER_CONFIG["n_ctx"],
        flash_attn=True,
        verbose=False,
    )

    framework = generate_framework(llm, topic)

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = sanitize_filename(topic)
    out_path = os.path.join(out_dir, f"topic_{slug}_{ts}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 辩题：{topic}\n\n")
        f.write(f"_Generated: {ts}_\n\n")
        f.write("---\n\n")
        f.write(framework.strip() + "\n")

    print(f"已保存到: {out_path}")


if __name__ == "__main__":
    main()
