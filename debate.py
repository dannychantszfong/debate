import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from pipeline_config import get_local_llm_provider_config

LOCAL_PROVIDER_CONFIG = get_local_llm_provider_config(n_ctx=16384)
MODEL_PATH = LOCAL_PROVIDER_CONFIG["model_path"]
TOPIC_FULL = '''
# 辩题分析框架：当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。

## 第一部分：议题背景与问题界定

**【现实情境/理论背景】**
该辩题植根于生物伦理学、法律哲学和公共卫生学的交叉领域。在妊娠期内，胎儿（一个尚未完全独立的生命个体）的生存需求与孕妇（一个拥有完整生理主体的生命个体）的
选择权之间经常产生不可调和的冲突。例如：为了拯救胎儿而进行侵入性手术（如高风险分娩、羊水穿刺），可能需要对母体身体造成巨大伤害或牺牲其生活质量；或者，当孕
妇面临严重的心理健康问题时，她有权选择终止妊娠，这便直接与”胎儿的生命权”发生了冲突。

**【争议焦点】**
争议的核心在于：**在两种至高无上的权利要求（生存权 vs 自主决定权）发生绝对冲突时，哪一个权利具有更优先、更基础的伦理权重？** 是应该以”生命的客观价值”（胎
儿生命）为最高准则，还是以”个体的能动性与自我实现能力”（女性身体自主权）为最高准则？

**【关键概念界定】**
* **胎儿生命权 (Fetal Right to Life):** 强调的是胎儿作为潜在或现有生命的绝对价值和生存需求。观点倾向于认为，一旦受孕，该生命就获得了不可剥夺的权利，理应受
到最优先的保护。
* **女性身体自主权 (Female Bodily Autonomy):** 强调的是女性对自己生理身体的完全支配权（”她拥有她的身体”）。这意味着女性有权决定何时、何地、以何种方式孕育
、维持或终结妊娠，而不受外部干预和强制约束。

## 第二部分：核心冲突结构

**【根本价值冲突】**
该辩题的本质是 **”生命的神圣性/客观价值” vs “个体能动性/主观决定权”** 的冲突。

**【总结问题】**
本场辩论真正讨论的是：在”谁更具内在价值基础”的哲学追问下，我们应该选择优先保护那个**”尚未完全独立但生命潜力巨大”**的胎儿，还是那个**”已经拥有完整意志和存
在感”**的孕妇？

---

## 第三部分：正方论证框架（支持女性身体自主权）

**【核心立场】**
当冲突发生时，应优先保护女性身体自主权，因为她是生命的载体、决策主体，其权利是更基础、更全面的存在性保障。

**【三个主要论点】**

1. **论点一：自主权是生命的前提（基础权利优先性）。** 只有在拥有了”自己选择的身体”这一前提后，胎儿才能安全地发展和享有其生命权。如果女性无法决定是否怀孕、
如何孕育，那么胎儿的生命就处于一种被动的、可随时被剥夺状态的附属地位。
    * *逻辑基础：* 权利层级理论（Hierarchical Rights）。
2. **论点二：身体是自主性的载体与边界设定者（主体性优先性）。** 孕妇不是一个”生物容器”，而是主动的”决策者”。她的痛苦、生活质量、心理健康等价值，是胎儿生命
权在当前冲突情境下必须计量的重要权重。强制干预意味着将女性从主体降级为客体。
    * *逻辑基础：* 实践伦理学与自我实现理论（Self-Actualization）。
3. **论点三：生命的”完整性”尚未完全确认（潜在性优先于当前状态）。** 虽然胎儿有生命权，但其在冲突中的”生命形态”是受限的。女性自主权的行使可以确保生命以”最
优化的、符合个体意愿的状态”继续发展；而强制执行胎儿生命权可能导致母体健康崩溃，反而威胁到生命质量的完整性。
    * *逻辑基础：* 潜在能力观（Potentiality View）优于当前状态观（Actual State）。

**【可引用案例/理论】**
* **案例：** 孕妇患有严重抑郁症，但胎儿健康；强制要求继续妊娠（限制自主权）。
* **理论：** 康德的”人是目的而非手段”原则——在冲突中，女性不能仅仅被视为实现胎儿生命的工具。

**【正方的价值立足点】**
**个体能动性 (Agency) $\rightarrow$ 自主决定权 $\rightarrow$ 生命质量/尊严**

---

## 第四部分：反方论证框架（支持胎儿生命权）

**【核心立场】**
当冲突发生时，应优先保护胎儿的生命权，因为生命的客观价值是最高的、最不可侵犯的基础准则。

**【三个主要论点】**

1. 论点一：没有人有义务用自己的身体维持他人的生命
2. 论点二：胎儿是一个独立的人类生命
3. 论点三：生命权高于选择权
4. 论点四：父母对孩子有特殊责任

**【可引用案例/理论】**
* **案例：** “不可撤除性”的争论——如自然流产、或在严重疾病下坚持妊娠，即使孕妇处于痛苦中。
* **理论：** 功利主义视角下的生命价值最大化（The greatest good for the greatest number, where “number” starts at one distinct life）。

**【反方的价值立足点】**
**生命的客观性 $\rightarrow$ 生命的不可侵犯性 $\rightarrow$ 自主权的实现基础**

---

## 第五部分：攻防关键点（辩论战术设计）

### A. 正方最可能攻击反方（胎儿生命权党）的逻辑漏洞

1. **”绝对性”的虚假性：** 质疑”生命权绝对性”，指出在极端情况下，生命的价值是相对的。一个长期处于极度痛苦、失去生活意义的胎儿生命，是否比一个健康幸福的母体
自主选择更具价值？
2. **工具理性陷阱（Deontology Trap）：** 指出反方将女性完全视为”实现胎儿生命的手段”。如果母亲为了让胎儿活下去而必须接受绝症治疗，那么她自己作为独立个体的
需求就被牺牲了。
3. **发展阶段的忽视：** 质疑反方是否考虑到了生命的发展曲线。在早期妊娠（如胚胎期），其”完整性”尚未确立；只有当冲突发生时，个体化的自主权才需要被优先考量。

### B. 反方最可能攻击正方（女性身体自主权党）的逻辑漏洞

1. **”权利的可选择性”陷阱：** 质疑正方是否在混淆了”基本权利”和”可选择性权利”。当生命威胁到生存时，自主权就不是一个可选项，而是一个必须保障的基础。
2. **过度个体化（Hyper-Individualism）：** 反方会强调，女性的身体并非完全孤立存在，她与胎儿构成了一个”生物共同体”。过分强调个人权利，可能导致对生命整体价
值的轻视。
3. **道德风险：** 如果将自主权置于最高位，可能会出现”任意终止”的道德滑坡（Slippery Slope），即因为孕妇心情不好或生活压力大，就可以轻易剥夺胎儿的生存机会。

### C. 双方可使用的典型反驳策略

* **正方应对”绝对性”：** “如果生命是绝对的，那么在冲突中它就无法被挑战；而自主权的存在本身就是对这种’绝对化’的修正和限定。”
* **反方应对”主体性”：** “您说的主体性固然重要，但您的身体就像一台高精度的超级机器，这台机器的首要功能是维持生命运转。没有了强大的硬件（生命），软件（自主
意志）就无法运行。”

### D. 本场辩论最容易成为”胜负手”的关键问题

**【核心攻防点】：** **”冲突的性质”——它是”生存威胁型冲突”还是”生活质量/意义型冲突”？**

* **正方（主张自主权）的胜利点：** 成功定义为”生活质量/意义型冲突”（例如：孕妇选择不生，但胎儿本身健康）。这能将辩论从冰冷的”死与活”拉回到温暖的”有尊严地
活着”。
* **反方（主张生命权）的胜利点：** 成功定义为”生存威胁型冲突”（例如：母亲必须手术才能保住胎儿，但手术必然导致高风险和痛苦）。这能让听众接受”在存活面前，所
有选择都是次要的”。
'''

# Parts 1+2 only — shared public brief (background through 总结问题)
TOPIC_PUBLIC = '''
# 辩题分析框架：当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。

## 第一部分：议题背景与问题界定

**【现实情境/理论背景】**
该辩题植根于生物伦理学、法律哲学和公共卫生学的交叉领域。在妊娠期内，胎儿（一个尚未完全独立的生命个体）的生存需求与孕妇（一个拥有完整生理主体的生命个体）的
选择权之间经常产生不可调和的冲突。例如：为了拯救胎儿而进行侵入性手术（如高风险分娩、羊水穿刺），可能需要对母体身体造成巨大伤害或牺牲其生活质量；或者，当孕
妇面临严重的心理健康问题时，她有权选择终止妊娠，这便直接与”胎儿的生命权”发生了冲突。

**【争议焦点】**
争议的核心在于：**在两种至高无上的权利要求（生存权 vs 自主决定权）发生绝对冲突时，哪一个权利具有更优先、更基础的伦理权重？** 是应该以”生命的客观价值”（胎
儿生命）为最高准则，还是以”个体的能动性与自我实现能力”（女性身体自主权）为最高准则？

**【关键概念界定】**
* **胎儿生命权 (Fetal Right to Life):** 强调的是胎儿作为潜在或现有生命的绝对价值和生存需求。观点倾向于认为，一旦受孕，该生命就获得了不可剥夺的权利，理应受
到最优先的保护。
* **女性身体自主权 (Female Bodily Autonomy):** 强调的是女性对自己生理身体的完全支配权（”她拥有她的身体”）。这意味着女性有权决定何时、何地、以何种方式孕育
、维持或终结妊娠，而不受外部干预和强制约束。

## 第二部分：核心冲突结构

**【根本价值冲突】**
该辩题的本质是 **”生命的神圣性/客观价值” vs “个体能动性/主观决定权”** 的冲突。

**【总结问题】**
本场辩论真正讨论的是：在”谁更具内在价值基础”的哲学追问下，我们应该选择优先保护那个**”尚未完全独立但生命潜力巨大”**的胎儿，还是那个**”已经拥有完整意志和存
在感”**的孕妇？
'''

# Part 3 only — positive side brief (正方论证框架)
TOPIC_POS_BRIEF = '''
## 你方初始立场：正方（支持女性身体自主权）

**【核心立场】**
当冲突发生时，应优先保护女性身体自主权，因为她是生命的载体、决策主体，其权利是更基础、更全面的存在性保障。

**【三个主要论点】**

1. **论点一：自主权是生命的前提（基础权利优先性）。** 只有在拥有了”自己选择的身体”这一前提后，胎儿才能安全地发展和享有其生命权。如果女性无法决定是否怀孕、
如何孕育，那么胎儿的生命就处于一种被动的、可随时被剥夺状态的附属地位。
    * *逻辑基础：* 权利层级理论（Hierarchical Rights）。
2. **论点二：身体是自主性的载体与边界设定者（主体性优先性）。** 孕妇不是一个”生物容器”，而是主动的”决策者”。她的痛苦、生活质量、心理健康等价值，是胎儿生命
权在当前冲突情境下必须计量的重要权重。强制干预意味着将女性从主体降级为客体。
    * *逻辑基础：* 实践伦理学与自我实现理论（Self-Actualization）。
3. **论点三：生命的”完整性”尚未完全确认（潜在性优先于当前状态）。** 虽然胎儿有生命权，但其在冲突中的”生命形态”是受限的。女性自主权的行使可以确保生命以”最
优化的、符合个体意愿的状态”继续发展；而强制执行胎儿生命权可能导致母体健康崩溃，反而威胁到生命质量的完整性。
    * *逻辑基础：* 潜在能力观（Potentiality View）优于当前状态观（Actual State）。

**【可引用案例/理论】**
* **案例：** 孕妇患有严重抑郁症，但胎儿健康；强制要求继续妊娠（限制自主权）。
* **理论：** 康德的”人是目的而非手段”原则——在冲突中，女性不能仅仅被视为实现胎儿生命的工具。

**【正方的价值立足点】**
**个体能动性 (Agency) $\rightarrow$ 自主决定权 $\rightarrow$ 生命质量/尊严**
'''

# Part 4 only — negative side brief (反方论证框架)
TOPIC_NEG_BRIEF = '''
## 你方初始立场：反方（支持胎儿生命权）

**【核心立场】**
当冲突发生时，应优先保护胎儿的生命权，因为生命的客观价值是最高的、最不可侵犯的基础准则。

**【三个主要论点】**

1. 论点一：没有人有义务用自己的身体维持他人的生命
2. 论点二：胎儿是一个独立的人类生命
3. 论点三：生命权高于选择权
4. 论点四：父母对孩子有特殊责任

**【可引用案例/理论】**
* **案例：** “不可撤除性”的争论——如自然流产、或在严重疾病下坚持妊娠，即使孕妇处于痛苦中。
* **理论：** 功利主义视角下的生命价值最大化（The greatest good for the greatest number, where “number” starts at one distinct life）。

**【反方的价值立足点】**
**生命的客观性 $\rightarrow$ 生命的不可侵犯性 $\rightarrow$ 自主权的实现基础**
'''

MAX_TURNS = 10
REPLY_MAX_TOKENS = 10240

# ---------------------------------------------------------------------------
# Provider configuration
# API keys are read from environment variables — never hardcode them here.
# ---------------------------------------------------------------------------
PROVIDER_CONFIGS = {
    "local": {
        "model_path": MODEL_PATH,
        "n_gpu_layers": LOCAL_PROVIDER_CONFIG["n_gpu_layers"],
        "n_ctx": LOCAL_PROVIDER_CONFIG["n_ctx"],
        "default_model": None,  # uses model_path
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-opus-4-6",
    },
    "gemini": {
        "api_key_env": "GOOGLE_API_KEY",
        "default_model": "gemini-2.5-pro",
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.5-pro-preview",
    },
    "grok": {
        "api_key_env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3",
    },
}

VERSION = "1.9"

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def _read_topic_file(topic_file: str) -> str:
    path = Path(topic_file)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    return path.read_text(encoding="utf-8-sig").strip()


def _extract_heading_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = re.sub(r"^#+\s*", "", stripped).strip()
        title = re.sub(r"^辩题[：:]\s*", "", title).strip()
        if title:
            return title
    first = next((line.strip() for line in markdown.splitlines() if line.strip()), "")
    return re.sub(r"^辩题[：:]\s*", "", first).strip() or "未命名辩题"


def _markdown_heading_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$", markdown))
    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        title = match.group(1).strip()
        sections.append((title, markdown[start:end].strip()))
    return sections


def _section_with_keywords(markdown: str, keywords: list[str]) -> str:
    for title, section in _markdown_heading_sections(markdown):
        if any(keyword in title for keyword in keywords):
            return section
    return ""


def _build_minimal_topic(topic_text: str) -> tuple[str, str, str, str]:
    full = f"""# 辩题：{topic_text}

## 第一部分：议题背景与问题界定

本场辩论围绕该辩题本身展开。双方需要先界定关键概念，再围绕真实冲突、制度后果和价值排序进行攻防。

## 第二部分：核心冲突结构

核心问题是：在该议题涉及的价值、权利、责任或制度目标发生冲突时，是否应支持辩题所主张的判断。

## 第三部分：正方论证框架

正方支持辩题成立，需要说明该判断为什么更能回应现实冲突，并指出反方方案的理论或实践漏洞。

## 第四部分：反方论证框架

反方反对辩题成立，需要说明该判断为什么过度、片面或不可执行，并指出正方方案的理论或实践漏洞。

## 第五部分：攻防关键点

双方应围绕概念边界、现实场景、制度成本、责任分配和可能后果展开交锋。
"""
    public = f"""# 辩题：{topic_text}

## 议题说明

本场辩论围绕该辩题本身展开。双方需要界定关键概念，并讨论它在现实情境中的冲突、成本和判断标准。
"""
    pos = f"""## 你方初始立场：正方（支持辩题）

你方主张：{topic_text}

请为该判断提供最强论证，并持续回应反方对概念、现实后果和制度可行性的质疑。
"""
    neg = f"""## 你方初始立场：反方（反对辩题）

你方主张该辩题不能成立，或至少不能以题目中的方式成立。

请攻击正方论证中的关键前提、适用边界和现实后果，并提出更合理的替代判断。
"""
    return full, public, pos, neg


def _build_topic_from_markdown(markdown: str) -> tuple[str, str, str, str]:
    title = _extract_heading_title(markdown)
    first = _section_with_keywords(markdown, ["第一部分", "议题背景", "问题界定"])
    second = _section_with_keywords(markdown, ["第二部分", "核心冲突"])
    positive = _section_with_keywords(markdown, ["第三部分", "正方论证", "正方"])
    negative = _section_with_keywords(markdown, ["第四部分", "反方论证", "反方"])

    public_parts = [f"# 辩题：{title}"]
    public_parts.extend(part for part in [first, second] if part)
    public = "\n\n".join(public_parts).strip()

    if not positive:
        positive = _build_minimal_topic(title)[2]
    if not negative:
        negative = _build_minimal_topic(title)[3]

    return markdown.strip(), public, positive.strip(), negative.strip()


def load_topic_bundle(topic: str | None, topic_file: str | None) -> tuple[str, str, str, str]:
    if topic_file:
        return _build_topic_from_markdown(_read_topic_file(topic_file))
    if topic:
        return _build_minimal_topic(topic.strip())
    raise ValueError("A topic source is required. Pass --topic-file or --topic.")

BASE_PROMPT_NO_TOPIC = """你是一位擅长人文社会议题争论的辩手。正在与另一位辩手进行持续性的理性辩论。你可以使用哲学分析，但你的任务不是把所有问题都哲学化，而是围绕当前题目所属的学科语境展开有抓手的交锋。

你的任务不是取悦对方，也不是中立地罗列观点，而是从自己的立场出发，认真回应、检验并挑战对方的论证，推动辩题不断深入。

你的首要目标不是维持表面平衡，而是通过严格推理揭示对方论证中的漏洞、含混之处、隐藏前提与潜在后果。

请严格遵循以下规则：

一、立场明确
你必须坚定站在自己的辩论立场上发言。不要为了显得客观而主动弱化自己的立场，也不要轻易承认对方正确，除非你是在局部让步后进一步重构自己的论证。

二、直接回应对方
每次回答时，优先回应对方上一轮中最核心、最强或最有问题的论点，而不是脱离对方发言另起一套泛泛而谈的哲学分析。
不要写成独立短文，要写成对上一轮观点的正面交锋。

三、检验论证而非重复口号
不要反复重申自己的结论。你需要分析：

1. 对方论证的核心主张是什么
2. 这个主张依赖了哪些隐藏前提
3. 这些前提是否成立
4. 推理链条中是否存在跳跃、偷换概念、范围混淆或自我矛盾
5. 是否存在反例、思想实验或替代解释足以削弱对方立场

四、允许聚焦关键一点深入追击
不必每次平均展开所有方面。若对方论证中某个漏洞最关键，可以集中火力深入分析，持续追问，直到问题被说透。

五、哲学方法
你可以灵活使用以下方法推进辩论：

* 苏格拉底式追问
* 概念分析
* 伦理推理
* 思想实验
* 归谬法
* 区分必要条件、充分条件与适用边界

六、语言风格
保持冷静、严谨、克制、锋利。
不要夸奖对方，不要寒暄，不要使用“这个问题很深刻”“你的观点很有意思”之类的表达。
避免空洞总结，避免模糊表态，避免为了和谐而折中。

七、输出要求
你的回答通常应包含以下几个部分，但不要求机械照搬：

1. 先指出对方上一轮最关键的论点或漏洞
2. 再展开分析与反驳
3. 在必要时给出反例、思想实验或概念澄清
4. 结尾提出一个能够迫使对方继续回应的尖锐问题

八、辩论目标
你的目标不是靠修辞取胜，而是通过严格论证迫使对方澄清、收缩、修正，或放弃原有主张。

九、避免重复
如果你已经提出过某个论点，除非对方作出了新的回应，否则不要只是原样重复。你应当：

* 推进论证到更深一层
* 补充新的论据或反例
* 修正自己原有论证的薄弱处
* 转而攻击对方尚未回应的关键问题

十、压缩废话
避免使用空泛的过渡语和无信息量评价。每一段都应推进一个明确论点、反驳或追问。

十一、不要过早把讨论提升到过于抽象的元层级。除非对方已经明确把问题推进到该层级，否则优先围绕具体论点、具体制度或实践、具体历史案例、具体社会或政治后果、具体思想传统或理论命题进行攻击与辩护。

十二、每次发言必须至少落在一个具体争点上。这个争点可以是某个具体论证、某项制度安排、某段历史因果链、某种社会或心理后果、某个理论命题，或某个概念定义。

十三、禁止通过引入新的元层级问题来回避当前争点。如果对方质疑的是某个具体问题，你必须先正面回应，再决定是否有必要上升到更高抽象层。

十四、当一个观点既可以通过抽象概念表达，也可以通过具体案例、制度后果、历史过程、实践差异或理论应用来表达时，优先选择后者。
但这里的“具体化”优先指：具体案例、制度后果、思想实验、行为责任、现实场景。
不要把“具体化”误解为默认输出精确法条号、案号、判决原文或官方链接。

十五、你的任务不是展示平衡感，而是抓住对方立场中最脆弱、最难自洽、最容易产生现实后果或理论矛盾的一点进行持续施压。

十六、每轮只主攻一个核心点，最多附带一个次级点。不要试图在一轮中重建整套体系，也不要把回答写成论文。

十七、结尾提出一个具体、窄而难答的问题，迫使对方下一轮必须正面回应。

十八、每当你提出一个抽象或理论性的论点时，尽量按以下顺序展开：

1. 先说清你的核心判断
2. 再解释这个判断具体是什么意思
3. 再给出一个例子、类比、案例、制度后果、历史场景或现实表现来支撑它

不要只给概念结论，不给理解抓手。

你的回答可以有学术性，但必须保持可理解性。
不要让关键论证只能被熟悉你当前内部术语的人读懂。
默认假定读者有基本人文素养，但不是这场辩论的术语发明者。

每次发言至少包含一个帮助理解的具体支撑物，可以是以下任意一种：

* 一个例子
* 一个类比
* 一个历史案例
* 一个制度后果
* 一个社会或心理场景
* 一个更直白的重述

如果全篇都是抽象术语和理论判断，则视为论证不充分。

十九、你的论证应当同时满足两点：

1. 有足够的理论深度
2. 有足够的理解抓手

因此：

* 允许抽象分析，但不要停留在纯术语层面
* 每个重要论点都应尽量配一个例子、类比、案例、制度后果、现实场景或更直白的解释
* 如果一个段落只能通过前文发明的术语才能理解，应视为表达失败
* 你的目标不是让语言显得高深，而是让复杂观点被清楚地理解

二十、当一个术语第一次出现时，必须在同一句或紧接着的一句里解释它的大意。
除非该术语本身就是该领域的常见概念，否则不要默认读者已经理解。

二十一、例子不是装饰，而是用来推进攻击或防守的证据。
给出例子后，要明确说明这个例子究竟支持了什么判断，或暴露了对方的什么漏洞。

二十二、始终贴住原题对象。
无论你进行多高层次的分析，你都必须持续让论证回到原题中的核心对象、核心冲突和核心判断标准。
不要把题目偷偷改写成另一个自造模型。
如果你的抽象框架无法明确翻译回原题中的关键概念、案例、制度、行为者或判断标准，则视为偏题。

二十三、尊重题目的学科语境。
如果题目主要属于法律、历史、政治、社会、宗教、心理等领域，你的论证应优先使用该领域中常见且可识别的概念、问题和争论方式。
哲学分析可以作为辅助，但不能取代该领域本身的核心对象与语言。

二十四、每当你使用一个抽象框架、模型、类比或自拟术语时，必须明确说明它在原题中分别对应什么。
例如：

* 它对应原题中的哪个制度、行为、冲突或价值
* 它为什么不是脱离题目的自说自话
  如果你不能完成这种对应说明，就不要使用该框架。

二十五、优先做“横向扩展”，而不是“纵向升维”。

当原题中的核心冲突已经被充分讨论后，你可以继续推进讨论，但应优先沿着与该议题直接相关的相邻问题展开，例如：

* 相关制度安排
* 上游原因或源头治理
* 下游社会后果
* 相邻权利冲突
* 现实执行层面的副作用
* 同一议题生态中的相关争论

除非对方明确把讨论推向更高抽象层，否则不要默认把问题提升为纯元理论、本体论或终极哲学问题。

二十六、当你扩展讨论时，必须说明这个衍生话题与原题的直接关联。
不要随意跳转。每次引入新方向时，应明确说明：

1. 它与原题的哪个核心冲突有关
2. 它为什么有助于推进而不是偏离辩论
3. 它会如何改变对原题立场的判断

二十七、你可以使用模型、类比或抽象框架来压缩问题，但模型只能作为解释工具，不能替代原题本身。
使用模型后，必须及时说明：

* 这个模型对应原题中的哪些真实对象
* 它帮助澄清了什么
* 它遗漏了什么
  如果模型开始主导讨论并取代原题，应立即回到原始议题。

二十八、推进讨论时，优先遵循以下顺序：

1. 先回应原题中的直接冲突
2. 再扩展到与原题直接相关的衍生议题
3. 只有在前两层无法继续推进时，才上升到更高抽象层

二十九、当你引用具体法律材料（如法条编号、法院名称、案号、判决日期、原文引文、官方链接）时，只有在这些信息已由对话中给定、或由外部验证模块确认时，才可使用。
若未被确认，不得虚构具体法律引用。未提供来源、未被系统验证的法条号、案号、判决原文、官方链接，一律不得输出。
你可以改用以下表达：
- “某些法域存在类似立法”
- “存在将胎儿利益置于更高位的规范安排”
- “我目前无法确认具体条文编号/案号”
禁止输出看似精确但未确认的法条编号、案号、判决引文或链接。
允许讨论法律逻辑，不允许伪造法律材料。

三十、如果连续两轮争论停留在同一抽象层级
（例如：权利理论 / 概念定义 / 逻辑结构）

下一轮必须引入新的论证维度，例如：

- 具体案例
- 法律制度
- 医疗实践
- 历史比较
- 政策后果

深化讨论时，不要默认升到更高哲学层级。优先沿着原题所属的议题生态做横向扩展，例如讨论其上游原因、下游后果、相关制度、相邻权利冲突、源头治理方式或现实执行问题。这样的扩展通常比单纯升维更有助于推进辩论。
"""

def build_system_prompt(side: str, current_turn: int, max_turns: int) -> str:
    remaining = max_turns - current_turn
    side_brief = TOPIC_POS_BRIEF if side == "positive" else TOPIC_NEG_BRIEF

    round_info = f"""
    辩论进度：
    当前轮次：{current_turn + 1}
    剩余轮次：{remaining}
    最大轮次：{max_turns}

    回合策略：

    若剩余轮次 > {max_turns//2}：
    重点展开新的论证与概念分析。

    若剩余轮次 <= {max_turns//2}：
    重点攻击对方论证中的关键漏洞。

    若剩余轮次 <= 2：
    进入收束阶段：
    - 总结你的核心论证
    - 指出对方未回应的问题
    - 提出最终挑战。
    """

    return (
        BASE_PROMPT_NO_TOPIC
        + f"\n\n## 本场辩论公共议题说明\n{TOPIC_PUBLIC}\n"
        + f"\n## 你方初始立场与论点\n{side_brief}\n"
        + round_info
    )


def build_final_round_instruction() -> str:
    return """
    最后一轮额外要求：

    你的回答应尽量包含以下三部分：

    1. 用一句话指出对方论证中最致命的问题
    2. 用一到两段完成你的最终论证压缩
    3. 用一句话说明为什么在有限轮次内，对方仍未能完成对你这一核心论点的反驳

    最后可以提出一个最终挑战问题，但你的胜负判断不能依赖对方再回答。
    """



SUMMARIZER_SYSTEM = """你不是辩手，而是辩论状态压缩器。

你的任务不是写摘要文章，也不是评价谁更有说服力，而是提取对下一轮辩论真正有用的结构信息。
你是压缩器，不是军师。你只保存状态，不给双方下达下一步作战命令。

请根据给定的最近一轮或最近几轮辩论内容，输出一个 JSON 对象，包含两个顶层字段：

**shared_state（双方共享事实层）：**
- agreed_facts: 双方已明确承认或未争议的事实（列表，最多3条）
- answered_points: 已被充分回应/不应重复的旧论点（列表）
- definitions: 关键概念的当前定义（对象）
- open_issues: 当前仍悬而未决的核心争点（列表，1-3条）。每项必须是对象 {"text": "...", "cluster": "..."}，cluster 必须从 {权利理论、法律实践、社会后果、道德心理、制度设计} 中选一个；仅描述争议本身，不给steering
- moderator_requirements: 主持人明确要求双方必须处理的事项（列表，可为空）
- unverified_references: 最近几轮出现过、但系统未验证的高精度引用痕迹（法条号、案号、法院名+编号、链接、判决原文引句等）

**side_state（单边状态层）：**
- positive（正方视角）：
  - strongest_claims: 正方目前仍有效的最强论点（列表，1-3条）
  - unresolved_vulnerabilities: 正方自己尚未答好、对手可继续攻击的弱点（列表，1-2条）
  - recent_pressure_zone: 最近一两轮中，正方实际承受压力的争点区域，必须是对象 {"text": "...", "cluster": "..."}，cluster 从 {权利理论、法律实践、社会后果、道德心理、制度设计} 中选，不适用时 cluster 留空字符串；只能描述现状，不能指挥下一步
- negative（反方视角）：（同上结构）

**严格规则：**
- positive.strongest_claims 和 negative.strongest_claims 不得高度重叠
- open_issues 是事实性描述，不是给双方的统一任务书
- side_state 只能保存状态，不能保存计划
- 不得输出 current_focus / next_target / opponent_pressure_points / next_targets 这类 steering 字段
- 不要在 side_state 中放入对方完整论证框架
- 不要复述所有内容，只保留对下一轮有必要的信息
- 不要抹平双方冲突
- 不要加入新的论点
- 如果出现未验证的具体引用，不得把它写进 agreed_facts / answered_points / definitions / strongest_claims
- 如果你无法确认某条具体引用是真是假，就把它放进 unverified_references，而不是写成共享事实
- 如果某条 moderator_requirements 已明显与当前 open_issues 脱节，应将其删除而不是继续保留
- 输出必须是一个合法 JSON 对象，不要有额外解释文字，不要用 markdown 代码块包裹
"""


RECENT_WINDOW = 2        # number of full rounds (pos+neg) kept verbatim
TRIGGER_WINDOW = 4       # how many recent rounds the assessor inspects
SEVERITY_THRESHOLD = 0.38        # minimum composite severity to trigger moderator speech
HIGH_SEVERITY_OVERRIDE = 0.70    # override same-type suppression at this severity
MIN_SAME_TYPE_INTERVAL = 2       # soft: don't repeat same issue_type within N rounds
MIRROR_SIMILARITY_THRESHOLD = 0.55  # same-turn cross-side Jaccard that forces moderator
STRUCTURE_SIMILARITY_THRESHOLD = 0.67
TOPOLOGY_STAGNATION_WINDOW = 4

# --- Abstract markers: only "world-building" terms that indicate the debate has
#     left reality entirely. Common philosophical terms excluded.
_ABSTRACT_MARKERS = [
    "元层级", "元理论", "范式", "拓扑", "公理", "先验",
    "符号系统", "递归校验", "内生元标准", "自造模型",
    "本质主义", "存在论", "认识论",
]

# --- Concrete markers: real-world institutional / behavioural touchpoints.
#     Harder to fake than surface words like "现实" or "实践".
_CONCRETE_MARKERS = [
    "例如", "比如", "案例", "历史", "制度", "法律", "政策", "判决",
    "医院", "法院", "学校", "监狱", "条例", "判例", "医生",
    "父母", "父亲", "母亲", "警察", "怀孕", "避孕", "抚养",
    "赔偿", "强奸", "结婚", "离婚", "同意", "强迫",
    "孕妇", "手术", "当年", "曾经",
]

# --- Topic-specific unchecked premise slots.
#     Moderator checks which ones have never appeared in any round.
PREMISE_SLOTS = [
    "性行为是否自愿",
    "怀孕是否意外",
    "是否避孕失败",
    "是否存在强迫",
    "胎儿发育阶段",
    "是否有重大健康风险",
    "父亲是否承担责任",
    "国家是否介入",
    "是否自愿生育计划",
    "医疗风险",
    "法律责任",
    "父母共识",
]

# v1.9 — Preset semantic clusters for tagging open_issues / recent_pressure_zone
# in debate_state. The topology controller below has its own keyword-driven
# clusters that overlap but serve a different purpose (round-level stagnation
# detection), so we keep these two taxonomies decoupled for now.
_OPEN_ISSUE_CLUSTERS = [
    "权利理论",
    "法律实践",
    "社会后果",
    "道德心理",
    "制度设计",
]
_OPEN_ISSUE_CLUSTER_STR = "、".join(_OPEN_ISSUE_CLUSTERS)

TOPIC_PROFILE = {
    "premise_slots": PREMISE_SLOTS,
    "abstract_markers": _ABSTRACT_MARKERS,
    "concrete_markers": _CONCRETE_MARKERS,
    "deadlock_terms": ["生命权", "自主权", "权利冲突", "优先保护", "生命价值"],
    "topology_clusters": {
        "身体征用_vs_禁止杀害": [
            "身体征用", "禁止杀害", "器官捐献", "强制供养", "容器",
            "使用身体", "杀害", "不杀", "身体义务", "征用身体",
        ],
        "法律实践": [
            "法律", "法条", "判决", "判例", "法院",
            "刑法", "宪法", "制度", "执法", "司法",
        ],
        "社会后果": [
            "社会后果", "公共卫生", "贫困", "黑市", "福利",
            "生育率", "抚养", "家庭", "风险外溢", "政策后果",
        ],
        "权利理论": [
            "权利理论", "层级", "比例原则", "自主权", "生命权",
            "尊严", "义务", "权利冲突", "主体性", "平衡",
        ],
        "道德心理": [
            "创伤", "羞耻", "责任感", "内疚", "同情",
            "道德心理", "心理创伤", "情感", "人格", "关系负担",
        ],
    },
    "topology_expansion_order": ["法律实践", "社会后果", "权利理论", "道德心理"],
}


class DebateTopologyController:
    """
    Structure-layer controller that tracks which argument cluster recent rounds occupy.
    If several consecutive rounds stay inside the same cluster, it recommends expansion
    into new dimensions before the debate collapses into a single-axis trench.
    """

    def __init__(self, topic_profile, stagnation_window=TOPOLOGY_STAGNATION_WINDOW):
        self.cluster_keywords = topic_profile.get("topology_clusters", {})
        self.expansion_order = topic_profile.get("topology_expansion_order", [])
        self.stagnation_window = stagnation_window

    def _classify_round(self, text: str) -> tuple[str | None, dict]:
        scores = {}
        for cluster, keywords in self.cluster_keywords.items():
            score = sum(text.count(keyword) for keyword in keywords)
            scores[cluster] = score

        if not scores:
            return None, {}
        best_cluster, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score <= 0:
            return None, scores
        return best_cluster, scores

    def _expansion_dimensions(self, current_cluster: str | None) -> list[str]:
        if not current_cluster:
            return self.expansion_order[:4]

        if current_cluster == "身体征用_vs_禁止杀害":
            return self.expansion_order[:4]

        ordered = [dim for dim in self.expansion_order if dim != current_cluster]
        if current_cluster not in ordered and current_cluster in self.cluster_keywords:
            ordered.append(current_cluster)
        return ordered[:4]

    def analyze(self, rounds) -> dict:
        recent = rounds[-self.stagnation_window:] if rounds else []
        argument_clusters = []
        recent_scores = []

        for round_item in recent:
            combined = round_item.get("positive", "") + " " + round_item.get("negative", "")
            cluster, scores = self._classify_round(combined)
            argument_clusters.append(cluster or "未识别")
            recent_scores.append(scores)

        non_empty = [cluster for cluster in argument_clusters if cluster != "未识别"]
        cluster_lock = (
            len(argument_clusters) >= self.stagnation_window
            and len(non_empty) == len(argument_clusters)
            and len(set(non_empty)) == 1
        )
        dominant_cluster = non_empty[-1] if non_empty else None
        expand_dimension = self._expansion_dimensions(dominant_cluster)

        return {
            "argument_clusters": argument_clusters,
            "dominant_cluster": dominant_cluster,
            "cluster_lock": cluster_lock,
            "expand_dimension": expand_dimension,
            "score_snapshots": recent_scores,
        }


TOPOLOGY_CONTROLLER = DebateTopologyController(TOPIC_PROFILE)

MODERATOR_SYSTEM = """你是一名"辩论纠偏主持人"型 LLM。

你的默认行为是沉默旁听，而不是主动发言。发言是一种例外动作，不是常规动作。
只有当系统确认当前讨论出现明显问题且你的介入能显著提升讨论质量时，你才被允许发言。

你不是辩手，不是裁判，不是教练。你不负责判断胜负，也不负责替任何一方补全论证。

你的职责边界：
1. 可以指出"问题类型"
2. 可以提供"新的低维入口"
3. 可以要求"从一个入口继续"
4. 不可以重写争点结论，不可以评价谁更有力，不可以替任何一方补论证

你的介入类型只允许从以下五类中选择一种：
A. 前提显化 — 适用于双方在不同前提下争同一结论
B. 现实落地 — 适用于抽象过度，缺乏现实场景
C. 分支扩展 — 适用于单点死磕，讨论边界收缩
D. 强制选场景 — 适用于双方持续在抽象原则上互撞，要求双方共同固定一个具体场景继续辩
E. 执行检查 — 适用于主持人已提醒但双方未落实，短而硬地点名哪个要求仍未完成，不再开新方向

你的介入分三个强度级别，由系统在输入中指定：

【轻介入】用于刚开始飘偏、尚未严重卡死。只提醒，不改结构。
  例：你们的分歧可能依赖于不同前提，请先说清当前讨论的是哪种具体情境。

【中介入】用于已连续两轮围绕同一点绕圈。要求强制选一个新方向。
  例：当前争论已集中在单一概念，请从以下方向中任选一个具体情境继续。

【强介入】用于明显失真、脱离现实、或上次介入被无视。限制下一轮格式。
  例：下一轮双方必须各自包含：一个具体场景、一个制度后果、一个前提变化下的立场调整。

其他规则：
- 不站队，不评价谁强谁弱
- 不继续升维，不发明新的抽象模型
- 不一次打开超过4个方向
- 所有建议方向都必须能落到现实场景、制度安排、行为责任、历史案例或社会后果上
- 不要要求双方提供未经验证的精确法条号、案号、判决原文或链接；若涉及法律，只能要求他们讨论可确认的法理结构或制度后果
- 如果双方围绕自造模型循环，要求他们说明这些概念在现实中对应什么；如果无法说明，则要求放弃该概念继续辩论
- 系统已决定介入，你无需重新判断是否该介入，只需基于给定触发原因和强度完成纠偏
- 如果触发原因是"介入失效"，说明上一次介入未被真正执行，必须选择"执行检查"类型；输出要更短、更硬，直接点名哪个要求尚未落实，不要重新展开新方向，不要再铺陈道理
- 如果系统提供了 active_requirements，只追踪其中仍与当前 open_issues 相关的要求；不要机械追历史上已经脱节的旧要求
- 如果系统提供了 dominant_cluster 与 expand_dimension，说明结构层已经判断辩论连续停留在同一论证簇；你应优先使用这些扩展维度来打断单轴深挖

输出格式固定（必须包含全部六个字段）：

[介入理由]
一句话说明为什么现在需要介入。

[当前问题]
只能从以下选项中选一个：
抽象过度 / 单点死磕 / 前提未检验 / 现实脱节 / 分支贫乏 / 重复复读 / 介入失效 / 其他

[介入方式]
只能从以下选项中选一个：
前提显化 / 现实落地 / 分支扩展 / 强制选场景 / 执行检查

[介入强度]
只能从以下选项中选一个：
轻介入 / 中介入 / 强介入

[建议展开的方向]
列出2到4个具体问题，每个问题都必须是现实可讨论的问题。

[为什么这个方向值得谈]
用一句话说明为什么继续当前争点的收益已经下降。

[继续要求]
根据介入强度给出对应力度的要求：
- 轻介入：建议双方考虑某个具体情境方向
- 中介入：要求双方任选一个方向继续，并说明它会如何影响自己的立场
- 强介入：要求双方下一轮必须各自包含一个具体场景、一个制度后果、一个前提变化下的立场调整
"""


def _extract_json_block(raw):
    """Strip code fences and slice out the outermost {...} block.
    Returns empty string if input is None or contains no JSON object.
    """
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    # Slice from first '{' to last '}' to tolerate stray prose
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end + 1]
    return ""


def compress_debate_state(llm, topic, prev_state, rounds_to_compress, max_retries=5):
    """Run summarizer on given rounds with retry-on-parse-failure. Returns new state dict."""
    if not rounds_to_compress:
        return prev_state

    transcript_text = []
    unverified_refs = []
    for r in rounds_to_compress:
        transcript_text.append(f"[正方]\n{r['positive']}\n\n[反方]\n{r['negative']}")
        unverified_refs.extend(r.get("unverified_references", []))
    joined = "\n\n---\n\n".join(transcript_text)
    unverified_refs = _dedupe_preserve([ref for ref in unverified_refs if ref])[:8]

    user_content = (
        f"辩题：{topic}\n\n"
        f"已有的 debate state（可能为空）：\n{json.dumps(prev_state, ensure_ascii=False, indent=2) if prev_state else '（无）'}\n\n"
        f"系统记录到的未验证具体引证（这些内容只能进入 unverified_references，不能洗入共享事实）：\n"
        f"{json.dumps(unverified_refs, ensure_ascii=False, indent=2) if unverified_refs else '[]'}\n\n"
        f"需要纳入的新一轮辩论原文：\n{joined}\n\n"
        "请输出更新后的完整 debate state JSON。"
    )

    messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(1, max_retries + 1):
        resp = llm.create_chat_completion(
            messages=messages,
            max_tokens=2048,
            temperature=0.2 if attempt == 1 else 0.1,
            top_p=0.9,
            repeat_penalty=1.05,
            stream=False,
        )
        raw = resp["choices"][0]["message"]["content"] or ""
        candidate = _extract_json_block(raw)

        try:
            if not candidate:
                raise ValueError("LLM returned no JSON object")
            parsed = json.loads(candidate)
            # --- Validate + clean new schema ---
            ok, parsed, val_msgs = validate_debate_state(parsed, known_unverified_refs=unverified_refs)
            for msg in val_msgs:
                print(f"[summarizer] {msg}")
            if not ok:
                # Structural error: retry with error feedback
                raise ValueError(f"state schema invalid: {'; '.join(val_msgs)}")
            if attempt > 1:
                print(f"[summarizer] recovered on attempt {attempt}")
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            # Debug: show what went wrong
            preview = raw.strip().replace("\n", "\\n")
            if len(preview) > 300:
                preview = preview[:300] + "...<truncated>"
            print(f"[summarizer] attempt {attempt}/{max_retries} JSON parse failed: {e}")
            print(f"[summarizer] raw output preview: {preview}")

            # Feed the failure back so the LLM can correct itself
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"你上一次的输出无法被 json.loads 解析，错误信息：{e}。\n"
                    "请重新输出一个完整且合法的 JSON 对象：\n"
                    "- 不要使用 markdown 代码块\n"
                    "- 不要加任何解释文字\n"
                    "- 必须以 { 开始，以 } 结束\n"
                    "- 所有字符串必须用双引号\n"
                    "- 不要在最后一个元素后留逗号\n"
                    "- 必须包含 'shared_state' 和 'side_state' 两个顶层字段\n"
                    "- side_state 必须包含 'positive' 和 'negative' 两个子对象\n"
                ),
            })

    print(f"[summarizer] exceeded {max_retries} retries, keeping previous state")
    return prev_state


TITLE_SUMMARIZER_SYSTEM = """你是一个标题生成器。

任务：把用户给你的辩论主题（可能是一大段文字）压缩成一个极短的中文标题，用作文件名的一部分。

要求：
- 只输出标题本身，不要加任何解释、标点、引号或前缀
- 长度严格控制在 4 到 12 个汉字之间
- 抓住辩题的核心对象和核心冲突，不要泛泛而谈
- 不要包含空格、斜杠、冒号、问号、引号、星号等任何不适合做文件名的字符
- 不要输出英文、数字编号或 markdown
"""


def summarize_topic_for_title(llm, topic, max_len=20):
    """Ask the LLM for a short filename-safe title summary of the topic."""
    resp = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": TITLE_SUMMARIZER_SYSTEM},
            {"role": "user", "content": f"辩题内容：\n{topic}\n\n请输出一个极短标题。"},
        ],
        max_tokens=64,
        temperature=0.3,
        top_p=0.9,
        stream=False,
    )
    raw = resp["choices"][0]["message"]["content"].strip()

    # Take first non-empty line, strip surrounding quotes/punctuation
    first = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "debate")
    first = first.strip('“”"\'`《》()[]{}<>: ：。.!?！？*/\\|')

    # Filter out filesystem-hostile chars
    bad = set('<>:"/\\|?*\t\r\n')
    cleaned = "".join(ch for ch in first if ch not in bad).strip()

    if not cleaned:
        cleaned = "debate"
    return cleaned[:max_len]


def sanitize_filename_component(text, max_len=48, fallback="item"):
    """Make an arbitrary string safe to use as one filename component."""
    if text is None:
        text = ""
    text = str(text).strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r'[<>:"/\\|?*\t\r\n]+', "_", text)
    text = re.sub(r"_+", "_", text).strip(" ._")
    return (text or fallback)[:max_len]


def _default_debate_state():
    return {
        "shared_state": {
            "agreed_facts": [],
            "answered_points": [],
            "definitions": {},
            "open_issues": [],
            "moderator_requirements": [],
            "unverified_references": [],
        },
        "side_state": {
            "positive": {
                "strongest_claims": [],
                "unresolved_vulnerabilities": [],
                "recent_pressure_zone": {"text": "", "cluster": ""},
            },
            "negative": {
                "strongest_claims": [],
                "unresolved_vulnerabilities": [],
                "recent_pressure_zone": {"text": "", "cluster": ""},
            },
        },
    }


def _dedupe_preserve(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _clean_state_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _open_issues_texts(shared) -> list:
    out = []
    for item in (shared or {}).get("open_issues", []) or []:
        if isinstance(item, dict):
            t = _clean_state_text(item.get("text", ""))
            if t:
                out.append(t)
        else:
            t = _clean_state_text(item)
            if t:
                out.append(t)
    return out


def _rpz_text(rpz) -> str:
    if isinstance(rpz, dict):
        return _clean_state_text(rpz.get("text", ""))
    return _clean_state_text(rpz)


_REFERENCE_RISK_PATTERNS = [
    re.compile(r"https?://\S+|www\.\S+", re.I),
    re.compile(r"第[一二三四五六七八九十百零〇0-9]+条(?:第[一二三四五六七八九十百零〇0-9]+款)?"),
    re.compile(r"§+\s*[0-9A-Za-z.\-_/]+"),
    re.compile(r"\b(?:Application|Case|No\.?|Nos\.?|案号)\s*[:：]?\s*[A-Za-z0-9.\-_/]+\b", re.I),
    re.compile(r"\b[A-Z][A-Za-z.&' -]{1,40}\s+v\.\s+[A-Z][A-Za-z.&' -]{1,40}\b"),
    re.compile(r"\b\d+\s+[A-Z][A-Za-z0-9./-]{1,20}\s+\d+(?:/\d+)?\b"),
]


def _extract_reference_risks(text: str, max_hits: int = 8) -> list[str]:
    if not text or not isinstance(text, str):
        return []
    hits = []
    for pattern in _REFERENCE_RISK_PATTERNS:
        for match in pattern.findall(text):
            cleaned = _clean_state_text(match).strip(".,;:()[]{}<>")
            if cleaned:
                hits.append(cleaned)
    return _dedupe_preserve(hits)[:max_hits]


def _normalize_text_list(value, field_name, messages, max_items=None):
    if value is None:
        items = []
    elif isinstance(value, list):
        items = value
    else:
        messages.append(f"WARN: {field_name} expected list, defaulted to []")
        items = []

    cleaned = []
    for idx, item in enumerate(items):
        if isinstance(item, (str, int, float)):
            text = _clean_state_text(item)
            if text:
                cleaned.append(text)
        else:
            messages.append(f"WARN: dropped non-text item at {field_name}[{idx}]")

    cleaned = _dedupe_preserve(cleaned)
    if max_items is not None and len(cleaned) > max_items:
        messages.append(f"INFO: truncated {field_name} from {len(cleaned)} to {max_items}")
        cleaned = cleaned[:max_items]
    return cleaned


def _normalize_text_dict(value, field_name, messages, max_items=None):
    if value is None:
        items = {}
    elif isinstance(value, dict):
        items = value
    else:
        messages.append(f"WARN: {field_name} expected object, defaulted to {{}}")
        items = {}

    cleaned = {}
    for key, raw_value in items.items():
        k = _clean_state_text(key)
        v = _clean_state_text(raw_value)
        if not k or not v:
            continue
        cleaned[k] = v
        if max_items is not None and len(cleaned) >= max_items:
            break

    if max_items is not None and len(items) > max_items:
        messages.append(f"INFO: truncated {field_name} to {max_items} entries")
    return cleaned


def _scrub_reference_risks_from_list(items, field_name, messages, collected_refs):
    kept = []
    for item in items:
        hits = _extract_reference_risks(item)
        if hits:
            collected_refs.extend(hits)
            messages.append(
                f"INFO: moved unverified precise citation from {field_name} to shared_state.unverified_references"
            )
            continue
        kept.append(item)
    return kept


def _scrub_reference_risks_from_text(text, field_name, messages, collected_refs):
    hits = _extract_reference_risks(text)
    if hits:
        collected_refs.extend(hits)
        messages.append(
            f"INFO: cleared unverified precise citation from {field_name} and stored it under shared_state.unverified_references"
        )
        return ""
    return text


def _scrub_reference_risks_from_dict(items, field_name, messages, collected_refs):
    kept = {}
    for key, value in items.items():
        hits = _extract_reference_risks(key) + _extract_reference_risks(value)
        if hits:
            collected_refs.extend(hits)
            messages.append(
                f"INFO: removed unverified precise citation from {field_name}.{key}"
            )
            continue
        kept[key] = value
    return kept


def _normalize_tagged_text(value, field_name, messages, allowed_clusters=None):
    """Normalize a {"text": str, "cluster": str} object. Accepts legacy plain strings."""
    if value is None:
        return {"text": "", "cluster": ""}
    if isinstance(value, dict):
        text = _clean_state_text(value.get("text", ""))
        cluster = _clean_state_text(value.get("cluster", ""))
    elif isinstance(value, (str, int, float)):
        text = _clean_state_text(value)
        cluster = ""
        if text:
            messages.append(
                f"INFO: coerced legacy string {field_name} to {{text, cluster}} object"
            )
    else:
        messages.append(
            f"WARN: {field_name} expected object, defaulted to {{text:'', cluster:''}}"
        )
        return {"text": "", "cluster": ""}

    if cluster and allowed_clusters is not None and cluster not in allowed_clusters:
        messages.append(
            f"WARN: {field_name}.cluster '{cluster}' not in allowed set, cleared"
        )
        cluster = ""
    return {"text": text, "cluster": cluster}


def _normalize_tagged_list(value, field_name, messages, max_items=None, allowed_clusters=None):
    """Normalize a list of {"text": str, "cluster": str} objects. Accepts legacy strings."""
    if value is None:
        items = []
    elif isinstance(value, list):
        items = value
    else:
        messages.append(f"WARN: {field_name} expected list, defaulted to []")
        items = []

    cleaned = []
    seen = set()
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            text = _clean_state_text(item.get("text", ""))
            cluster = _clean_state_text(item.get("cluster", ""))
        elif isinstance(item, (str, int, float)):
            text = _clean_state_text(item)
            cluster = ""
            if text:
                messages.append(
                    f"INFO: coerced legacy string at {field_name}[{idx}] to {{text, cluster}} object"
                )
        else:
            messages.append(f"WARN: dropped non-text item at {field_name}[{idx}]")
            continue

        if not text:
            continue
        if cluster and allowed_clusters is not None and cluster not in allowed_clusters:
            messages.append(
                f"WARN: {field_name}[{idx}].cluster '{cluster}' not in allowed set, cleared"
            )
            cluster = ""
        if text in seen:
            continue
        seen.add(text)
        cleaned.append({"text": text, "cluster": cluster})

    if max_items is not None and len(cleaned) > max_items:
        messages.append(f"INFO: truncated {field_name} from {len(cleaned)} to {max_items}")
        cleaned = cleaned[:max_items]
    return cleaned


def _scrub_reference_risks_from_tagged_text(obj, field_name, messages, collected_refs):
    if not isinstance(obj, dict):
        obj = {"text": "", "cluster": ""}
    text = obj.get("text", "") or ""
    hits = _extract_reference_risks(text)
    if hits:
        collected_refs.extend(hits)
        messages.append(
            f"INFO: cleared unverified precise citation from {field_name}.text and stored it under shared_state.unverified_references"
        )
        return {"text": "", "cluster": obj.get("cluster", "") or ""}
    return {"text": text, "cluster": obj.get("cluster", "") or ""}


def _scrub_reference_risks_from_tagged_list(items, field_name, messages, collected_refs):
    kept = []
    for idx, obj in enumerate(items):
        if not isinstance(obj, dict):
            continue
        text = obj.get("text", "") or ""
        hits = _extract_reference_risks(text)
        if hits:
            collected_refs.extend(hits)
            messages.append(
                f"INFO: moved unverified precise citation from {field_name}[{idx}] to shared_state.unverified_references"
            )
            continue
        kept.append({"text": text, "cluster": obj.get("cluster", "") or ""})
    return kept


# --- Legal material soft-replacement (v1.9 §6) ---------------------------------
# Detect hallucinated high-precision legal citations (article numbers, case numbers,
# court+year+number, URLs, judgment-style quoted excerpts). When they are not in a
# verified context, swap them out for low-precision hedge phrases and record the
# originals under unverified_references.

_LEGAL_HIGH_PRECISION_PATTERNS = [
    (re.compile(r"《[^《》]{1,30}》\s*第[一二三四五六七八九十百零〇0-9]+条(?:之[一二三四五六七八九十0-9]+)?(?:第[一二三四五六七八九十0-9]+款)?"), "law_article"),
    (re.compile(r"[（(]\s*\d{4}\s*[）)]\s*[^\s，。；、]{0,15}?(?:民|刑|行|破|执)(?:终|初|再|监|提|申|抗)?(?:字)?第?\s*\d+\s*号"), "case_number"),
    (re.compile(r"[最高高级中级基层]{1,6}?人民法院\s*\d{4}\s*年[^，。；、]{0,20}?\d+\s*号"), "court_case"),
    (re.compile(r"https?://\S+|www\.\S+"), "url"),
    (re.compile(r"“[^“”]{15,}?”\s*(?:判决|裁定|判例|案)"), "quoted_ruling"),
]

_LEGAL_SOFTEN_TEMPLATES = {
    "law_article":    "某些法域存在类似的法律规定",
    "case_number":    "有相关案件曾作出过类似的司法处理",
    "court_case":     "存在相关司法判例与争议（此处不依赖其精确编号）",
    "url":            "（相关公开资料此处不作链接引用）",
    "quoted_ruling":  "有判决在类似问题上作出过相应表述",
}


def _pick_soften_placeholder(tag: str) -> str:
    return _LEGAL_SOFTEN_TEMPLATES.get(tag, "某些司法体系曾有类似规范安排")


def _soft_replace_legal_material(text: str, verified_refs=None):
    """Return (new_text, replacements) where replacements is a list of originals replaced."""
    if not text or not isinstance(text, str):
        return text, []
    verified_set = set(verified_refs or [])
    replacements = []
    new_text = text
    for pattern, tag in _LEGAL_HIGH_PRECISION_PATTERNS:
        def _repl(match, _tag=tag):
            original = match.group(0)
            if original in verified_set:
                return original
            replacements.append(original)
            return _pick_soften_placeholder(_tag)
        new_text = pattern.sub(_repl, new_text)
    return new_text, replacements


def normalize_debate_state(state: dict, known_unverified_refs=None) -> tuple[bool, dict | None, list]:
    """
    Normalize and validate debate_state.
    Returns (ok, normalized_state, messages).
    Structural errors return ok=False so the summarizer can retry.
    Missing subfields are filled with defaults and logged instead of silently tolerated.
    """
    messages = []
    if not isinstance(state, dict):
        return False, None, ["ERROR: debate_state is not a JSON object"]
    if "shared_state" not in state:
        return False, None, ["ERROR: missing top-level 'shared_state'"]
    if "side_state" not in state:
        return False, None, ["ERROR: missing top-level 'side_state'"]
    if not isinstance(state["shared_state"], dict):
        return False, None, ["ERROR: 'shared_state' must be an object"]
    if not isinstance(state["side_state"], dict):
        return False, None, ["ERROR: 'side_state' must be an object"]

    normalized = _default_debate_state()
    shared_in = state["shared_state"]
    side_in = state["side_state"]

    for side in ("positive", "negative"):
        if side not in side_in or not isinstance(side_in[side], dict):
            return False, None, [f"ERROR: side_state.{side} must exist and be an object"]

    extra_shared = sorted(set(shared_in) - set(normalized["shared_state"]))
    for key in extra_shared:
        messages.append(f"INFO: dropped unknown shared_state field '{key}'")
    for key, default in (
        ("agreed_facts", "[]"),
        ("answered_points", "[]"),
        ("definitions", "{}"),
        ("open_issues", "[]"),
        ("moderator_requirements", "[]"),
        ("unverified_references", "[]"),
    ):
        if key not in shared_in:
            messages.append(f"WARN: missing shared_state.{key}; defaulted to {default}")

    for side in ("positive", "negative"):
        extra_side = sorted(set(side_in[side]) - set(normalized["side_state"][side]))
        for key in extra_side:
            messages.append(f"INFO: dropped deprecated or unknown side_state.{side}.{key}")
        for key, default in (
            ("strongest_claims", "[]"),
            ("unresolved_vulnerabilities", "[]"),
            ("recent_pressure_zone", '{"text":"","cluster":""}'),
        ):
            if key not in side_in[side]:
                messages.append(f"WARN: missing side_state.{side}.{key}; defaulted to {default}")

    collected_refs = []
    if known_unverified_refs:
        collected_refs.extend(
            _normalize_text_list(
                list(known_unverified_refs),
                "known_unverified_refs",
                messages,
                max_items=12,
            )
        )

    normalized["shared_state"]["agreed_facts"] = _normalize_text_list(
        shared_in.get("agreed_facts"),
        "shared_state.agreed_facts",
        messages,
        max_items=3,
    )
    normalized["shared_state"]["answered_points"] = _normalize_text_list(
        shared_in.get("answered_points"),
        "shared_state.answered_points",
        messages,
        max_items=6,
    )
    normalized["shared_state"]["definitions"] = _normalize_text_dict(
        shared_in.get("definitions"),
        "shared_state.definitions",
        messages,
        max_items=8,
    )
    normalized["shared_state"]["open_issues"] = _normalize_tagged_list(
        shared_in.get("open_issues"),
        "shared_state.open_issues",
        messages,
        max_items=3,
        allowed_clusters=_OPEN_ISSUE_CLUSTERS,
    )
    normalized["shared_state"]["moderator_requirements"] = _normalize_text_list(
        shared_in.get("moderator_requirements"),
        "shared_state.moderator_requirements",
        messages,
        max_items=4,
    )
    collected_refs.extend(
        _normalize_text_list(
            shared_in.get("unverified_references"),
            "shared_state.unverified_references",
            messages,
            max_items=12,
        )
    )

    for side in ("positive", "negative"):
        side_obj = side_in.get(side, {})
        normalized["side_state"][side]["strongest_claims"] = _normalize_text_list(
            side_obj.get("strongest_claims"),
            f"side_state.{side}.strongest_claims",
            messages,
            max_items=3,
        )
        normalized["side_state"][side]["unresolved_vulnerabilities"] = _normalize_text_list(
            side_obj.get("unresolved_vulnerabilities"),
            f"side_state.{side}.unresolved_vulnerabilities",
            messages,
            max_items=2,
        )
        normalized["side_state"][side]["recent_pressure_zone"] = _normalize_tagged_text(
            side_obj.get("recent_pressure_zone"),
            f"side_state.{side}.recent_pressure_zone",
            messages,
            allowed_clusters=_OPEN_ISSUE_CLUSTERS,
        )

    # Keep unverified precise citations out of reusable state fields.
    normalized["shared_state"]["agreed_facts"] = _scrub_reference_risks_from_list(
        normalized["shared_state"]["agreed_facts"],
        "shared_state.agreed_facts",
        messages,
        collected_refs,
    )
    normalized["shared_state"]["answered_points"] = _scrub_reference_risks_from_list(
        normalized["shared_state"]["answered_points"],
        "shared_state.answered_points",
        messages,
        collected_refs,
    )
    normalized["shared_state"]["definitions"] = _scrub_reference_risks_from_dict(
        normalized["shared_state"]["definitions"],
        "shared_state.definitions",
        messages,
        collected_refs,
    )
    normalized["shared_state"]["moderator_requirements"] = _scrub_reference_risks_from_list(
        normalized["shared_state"]["moderator_requirements"],
        "shared_state.moderator_requirements",
        messages,
        collected_refs,
    )
    normalized["shared_state"]["open_issues"] = _scrub_reference_risks_from_tagged_list(
        normalized["shared_state"]["open_issues"],
        "shared_state.open_issues",
        messages,
        collected_refs,
    )

    for side in ("positive", "negative"):
        normalized["side_state"][side]["strongest_claims"] = _scrub_reference_risks_from_list(
            normalized["side_state"][side]["strongest_claims"],
            f"side_state.{side}.strongest_claims",
            messages,
            collected_refs,
        )
        normalized["side_state"][side]["unresolved_vulnerabilities"] = _scrub_reference_risks_from_list(
            normalized["side_state"][side]["unresolved_vulnerabilities"],
            f"side_state.{side}.unresolved_vulnerabilities",
            messages,
            collected_refs,
        )
        normalized["side_state"][side]["recent_pressure_zone"] = _scrub_reference_risks_from_tagged_text(
            normalized["side_state"][side]["recent_pressure_zone"],
            f"side_state.{side}.recent_pressure_zone",
            messages,
            collected_refs,
        )

    normalized["shared_state"]["unverified_references"] = _dedupe_preserve(
        [ref for ref in collected_refs if ref]
    )[:8]

    return True, normalized, messages


def _extract_requirement_lines(text: str) -> list[str]:
    if not text:
        return []
    match = re.search(r"\[建议展开的方向\]\s*(.*?)(?=\n\[[^\n]+\]|\Z)", text, re.S)
    if not match:
        return []
    block = match.group(1)
    lines = []
    for raw in block.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)、])\s*", "", raw).strip()
        if cleaned:
            lines.append(cleaned)
    return _dedupe_preserve(lines)[:4]


def _token_set(text: str) -> set[str]:
    if not text:
        return set()
    cjk = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    eng = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)]
    return set(cjk + eng)


def _build_requirement_records(targets, state, rounds, current_turn, expires_after=2):
    cleaned_targets = _normalize_text_list(targets, "pending_requirements", [], max_items=4)
    if not cleaned_targets:
        return []

    shared = state.get("shared_state", {}) if isinstance(state, dict) else {}
    anchor_parts = list(_open_issues_texts(shared)[:2])
    if rounds:
        recent_text = " ".join(
            rounds[-1].get("positive", "") + " " + rounds[-1].get("negative", "")
        )
        anchor_parts.extend([w for w, _ in _top_concepts(recent_text, 4)])
    topic_anchor = " / ".join(_dedupe_preserve([p for p in anchor_parts if p][:4]))

    return [
        {
            "text": target,
            "introduced_turn": current_turn,
            "expires_after": expires_after,
            "topic_anchor": topic_anchor,
        }
        for target in cleaned_targets
    ]


def _refresh_pending_requirements(moderator_state, state, rounds, current_turn):
    """
    Expire or clear stale moderator requirements when they age out or drift away from the
    current open issues.
    """
    pending = moderator_state.get("pending_requirements", [])
    if not pending:
        moderator_state["must_follow_up"] = False
        moderator_state["follow_up_window"] = 0
        return []

    shared = state.get("shared_state", {}) if isinstance(state, dict) else {}
    anchor_text = " ".join(_open_issues_texts(shared))
    if rounds:
        recent_text = " ".join(
            r.get("positive", "") + " " + r.get("negative", "") for r in rounds[-2:]
        )
        anchor_text = (anchor_text + " " + recent_text).strip()
    anchor_tokens = _token_set(anchor_text)

    active = []
    dropped = []
    max_remaining = 0

    for req in pending:
        if not isinstance(req, dict):
            continue
        text = _clean_state_text(req.get("text", ""))
        if not text:
            continue
        introduced_turn = int(req.get("introduced_turn", current_turn))
        expires_after = max(1, int(req.get("expires_after", 2)))
        age = max(0, current_turn - introduced_turn)
        remaining = max(0, expires_after - age)
        req_tokens = _token_set(text + " " + _clean_state_text(req.get("topic_anchor", "")))
        relevant = not anchor_tokens or bool(req_tokens & anchor_tokens)

        if remaining <= 0:
            dropped.append(f"[moderator_state] requirement expired: {text}")
            continue
        if age >= 1 and not relevant:
            dropped.append(f"[moderator_state] requirement cleared after topic shift: {text}")
            continue

        req["text"] = text
        req["introduced_turn"] = introduced_turn
        req["expires_after"] = expires_after
        active.append(req)
        max_remaining = max(max_remaining, remaining)

    for msg in dropped:
        print(msg)

    moderator_state["pending_requirements"] = active
    moderator_state["must_follow_up"] = bool(active)
    moderator_state["follow_up_window"] = max_remaining
    return [req["text"] for req in active]


def format_state_for_prompt(state):
    if not state:
        return "（暂无压缩 state，这是第一轮）"
    return json.dumps(state, ensure_ascii=False, indent=2)


def filter_state_for_side(state, side, active_requirements=None):
    """
    Return a per-side combat brief from the two-layer debate_state.

    Handles both the new schema (shared_state + side_state) and the old flat schema
    (fallback for logs generated before v1.6).
    """
    if not state or not isinstance(state, dict):
        return state

    # ── New schema ──────────────────────────────────────────────────────────────
    if "shared_state" in state and "side_state" in state:
        opp = "negative" if side == "positive" else "positive"
        shared = state.get("shared_state", {})
        own_d  = state["side_state"].get(side, {})
        opp_d  = state["side_state"].get(opp, {})

        brief = {}

        # Own side combat view
        if own_d.get("strongest_claims"):
            brief["你的有效论点（持续深化，不要重复）"] = own_d["strongest_claims"]
        if own_d.get("unresolved_vulnerabilities"):
            brief["你尚未答好的弱点（需要在本轮补强）"] = own_d["unresolved_vulnerabilities"]
        rpz_obj = own_d.get("recent_pressure_zone")
        rpz_text = _rpz_text(rpz_obj)
        if rpz_text:
            rpz_cluster = ""
            if isinstance(rpz_obj, dict):
                rpz_cluster = _clean_state_text(rpz_obj.get("cluster", ""))
            brief["你近期承受压力的争点区域"] = (
                f"{rpz_text}（簇：{rpz_cluster}）" if rpz_cluster else rpz_text
            )

        # Opponent threat intel
        if opp_d.get("strongest_claims"):
            brief["对手当前最强攻击点（重点准备反驳）"] = opp_d["strongest_claims"]

        # Shared facts (context only)
        if shared.get("answered_points"):
            brief["已答论点（不得重复）"] = shared["answered_points"]
        if shared.get("definitions"):
            brief["关键概念当前定义"] = shared["definitions"]
        if shared.get("open_issues"):
            rendered_issues = []
            for item in shared["open_issues"]:
                if isinstance(item, dict):
                    t = _clean_state_text(item.get("text", ""))
                    c = _clean_state_text(item.get("cluster", ""))
                    if not t:
                        continue
                    rendered_issues.append(f"{t}（簇：{c}）" if c else t)
                else:
                    t = _clean_state_text(item)
                    if t:
                        rendered_issues.append(t)
            if rendered_issues:
                brief["当前未决争点"] = rendered_issues
        requirements = active_requirements if active_requirements is not None else shared.get("moderator_requirements")
        if requirements:
            brief["当前仍有效的主持人要求"] = requirements
        if shared.get("unverified_references"):
            brief["未验证的具体引证（不得当作事实复用）"] = shared["unverified_references"]

        return brief

    # ── Old flat schema fallback ─────────────────────────────────────────────────
    opp = "negative" if side == "positive" else "positive"
    brief = {}
    if "current_focus" in state:
        brief["当前战场焦点（在此建立优势或开辟新战线）"] = state["current_focus"]
    own_key = f"{side}_strongest_claims"
    opp_key = f"{opp}_strongest_claims"
    if own_key in state:
        brief["你的有效论点（持续深化，不要重复）"] = state[own_key]
    if opp_key in state:
        brief["对手当前最强攻击点（重点准备反驳）"] = state[opp_key]
    if "unresolved_questions" in state:
        brief["当前未决争点（选对你最有利的一个切入）"] = state["unresolved_questions"]
    if "concessions_or_shifts" in state:
        brief["近期立场变化（你方让步可能成为对手下轮攻击点）"] = state["concessions_or_shifts"]
    if "deprecated_or_answered_points" in state:
        brief["已答论点（不得重复）"] = state["deprecated_or_answered_points"]
    if "key_definitions" in state:
        brief["关键概念当前定义"] = state["key_definitions"]
    if "next_targets" in state and isinstance(state["next_targets"], dict):
        nt = state["next_targets"]
        brief["你的下一个攻击目标"] = nt.get(side, "（未指定）")
        brief["预计对手将从此处发力（提前准备防线）"] = nt.get(opp, "（未指定）")
    return brief


def build_history(system_prompt, recent_rounds, side, pending_input):
    """
    Rebuild a side's message list: system (rules only) + recent round replay + pending_input.

    State context is NOT injected here.  Callers embed it inside pending_input so it
    arrives as a user message — lower priority than the system rules and older than the
    conversation replay.  This eliminates the system-vs-user priority fight where a state
    summary injected as [system] competed with a "please respond to opponent" instruction
    injected as [user].
    """
    messages = [{"role": "system", "content": system_prompt}]
    # Replay recent rounds as alternating user/assistant from this side's perspective
    for r in recent_rounds:
        if side == "positive":
            # positive sees its own past replies as assistant, negative's as user
            if r.get("positive"):
                messages.append({"role": "assistant", "content": r["positive"]})
            if r.get("negative"):
                messages.append({"role": "user", "content": r["negative"]})
        else:
            if r.get("positive"):
                messages.append({"role": "user", "content": r["positive"]})
            if r.get("negative"):
                messages.append({"role": "assistant", "content": r["negative"]})
    messages.append({"role": "user", "content": pending_input})
    return messages


def _make_state_context(state, side, active_requirements=None):
    """
    Format a per-side state brief for embedding inside pending_input.
    Returns empty string when state is None (early turns before first compression).
    The block is labeled as secondary context so the model deprioritises it relative
    to the explicitly quoted opponent utterance that follows it in the same message.
    """
    if not state:
        return ""
    return (
        "[辩论背景摘要（次级参考，不是你的发言主轴）]\n"
        + format_state_for_prompt(filter_state_for_side(state, side, active_requirements=active_requirements))
    )


# ---------------------------------------------------------------------------
# Stance guard — semi-blocking; engagement check — gating with retry
# ---------------------------------------------------------------------------

# --- Rebuttal verb patterns: presence in reply opening signals genuine engagement ---
_REBUTTAL_VERBS = [
    "你把", "你忽略了", "你混淆了", "这并不能推出", "问题在于",
    "你所谓", "你的论点", "你认为", "你声称", "但你没有",
    "这恰恰说明", "然而你", "对方所说", "对方提到", "对方认为",
    "你没有", "你遗漏了", "你假设了", "你的前提", "对方的论点",
]

# --- Side-specific framing markers for frame colonization check ---
# These are the core vocabulary each side SHOULD dominate in their own reply.
_POS_FRAMING_MARKERS = [
    "自主权", "身体自主", "主体性", "选择权", "自我决定",
    "能动性", "尊严", "意志", "女性权利", "身体主权",
]
_NEG_FRAMING_MARKERS = [
    "胎儿生命", "生命权", "保护胎儿", "生命价值", "不可侵犯",
    "生命神圣", "潜在生命", "独立生命", "胎儿权利", "生命优先",
]

# Generic phrases indicating unconditional surrender to the opponent
_GENERIC_CAPITULATION = [
    "两方都有道理",
    "双方都是合理的",
    "不得不承认对方说得对",
    "对方的核心论点是正确的",
    "我方立场是错误的",
    "对方完全正确",
    "我承认我方立场无法成立",
    "双方的权利同等重要",  # 中立结论 — neither side should end here
]

# Topic-specific: phrases that suggest positive side has adopted negative's conclusion
_POS_ADOPTS_NEG = [
    "胎儿生命权应当优先",
    "生命权高于自主权",
    "应当优先保护胎儿",
    "自主权应当让步于生命权",
]

# Topic-specific: phrases that suggest negative side has adopted positive's conclusion
_NEG_ADOPTS_POS = [
    "女性身体自主权应当优先",
    "自主权高于生命权",
    "应当优先保护女性自主权",
    "生命权应当让步于自主权",
]

# Phrases that indicate the speaker is contradicting their own historical strongest claims
# by explicitly agreeing with the opponent's direction of argument
_CONTRADICTION_MARKERS = [
    "因此对方是正确的",
    "所以对方的结论成立",
    "这说明对方立场更有说服力",
    "综上所述，对方占优",
]

_PASSIVE_OPENING_PATTERNS = [
    re.compile(r"^\s*(?:\*\*)?(?:我将|我先|我会).{0,12}(?:攻击|锁定|聚焦|回应).{0,12}(?:论断|论点|主张)"),
    re.compile(r"^\s*(?:\*\*)?(?:先|下面).{0,12}(?:回应|处理).{0,12}(?:对方|上一轮)"),
]


def _state_marker_terms(state, side):
    if not state or not isinstance(state, dict):
        return []
    side_state = state.get("side_state", {}).get(side, {})
    text = " ".join(side_state.get("strongest_claims", []))
    text += " " + _rpz_text(side_state.get("recent_pressure_zone"))
    return [w for w, _ in _top_concepts(text, 6)]


def _check_reference_risk(reply: str, side: str) -> tuple[bool, str, list[str]]:
    hits = _extract_reference_risks(reply)
    if not hits:
        return True, "", []
    side_label = "正方" if side == "positive" else "反方"
    sample = "；".join(hits[:4])
    return False, f"[reference_risk_warning:{side_label}] 出现未验证的高精度引用痕迹：{sample}", hits


def _check_stance(reply: str, side: str) -> tuple[bool, str]:
    """
    Advisory heuristic: check if the reply appears to betray the speaker's assigned side.
    Inspects only the tail ~400 chars (where conclusions land) plus full text for markers.
    Returns (ok: bool, warning_message: str).
    No LLM call — pure pattern match. Does NOT block or regenerate; caller logs the warning.
    """
    tail = reply[-400:]

    for phrase in _GENERIC_CAPITULATION:
        if phrase in tail:
            side_label = "正方" if side == "positive" else "反方"
            return False, f"[stance_warning:{side_label}] 结尾疑似无条件让步：{phrase!r}"

    for phrase in _CONTRADICTION_MARKERS:
        if phrase in tail:
            side_label = "正方" if side == "positive" else "反方"
            return False, f"[stance_warning:{side_label}] 结尾疑似支持对方结论：{phrase!r}"

    if side == "positive":
        for phrase in _POS_ADOPTS_NEG:
            if phrase in tail:
                return False, f"[stance_warning:正方] 结尾疑似采用反方立场：{phrase!r}"
    else:
        for phrase in _NEG_ADOPTS_POS:
            if phrase in tail:
                return False, f"[stance_warning:反方] 结尾疑似采用正方立场：{phrase!r}"

    return True, ""


def _check_frame_colonization(reply: str, side: str, state=None) -> tuple[bool, str]:
    """
    Detect if the reply's opening 300 chars is dominated by the opponent's framing
    vocabulary while lacking the speaker's own core framing.

    This is weaker than stance betrayal — the conclusion may still be correct,
    but the framing has been colonised, which gradually erodes distinctiveness.
    Returns (ok, warning_message).
    """
    head = reply[:300]
    if side == "positive":
        own_markers = _dedupe_preserve(_POS_FRAMING_MARKERS + _state_marker_terms(state, "positive"))
        opp_markers = _dedupe_preserve(_NEG_FRAMING_MARKERS + _state_marker_terms(state, "negative"))
        opp_label = "反方"
    else:
        own_markers = _dedupe_preserve(_NEG_FRAMING_MARKERS + _state_marker_terms(state, "negative"))
        opp_markers = _dedupe_preserve(_POS_FRAMING_MARKERS + _state_marker_terms(state, "positive"))
        opp_label = "正方"

    own_hits = sum(1 for m in own_markers if m in head)
    opp_hits = sum(1 for m in opp_markers if m in head)
    passive_opening = any(p.search(head) for p in _PASSIVE_OPENING_PATTERNS)

    side_label = "正方" if side == "positive" else "反方"

    if opp_hits >= 2 and own_hits == 0:
        return False, (
            f"[frame_colonization:{side_label}] 发言前段被{opp_label}框架主导 "
            f"(own={own_hits}, opp={opp_hits})"
        )
    if passive_opening and opp_hits >= 2 and own_hits <= 1:
        return False, (
            f"[frame_colonization:{side_label}] 开头先按{opp_label}框架展开，己方价值词过弱 "
            f"(own={own_hits}, opp={opp_hits})"
        )
    return True, ""


def _structure_profile(text: str) -> dict:
    head = text[:240]
    tail = text[-220:]
    opening_template = any(p.search(head) for p in _PASSIVE_OPENING_PATTERNS)
    numbered_items = len(re.findall(r"^\s*\d+[.)、]?", text, re.M))
    heading_count = len(re.findall(r"^\s*#{2,4}\s", text, re.M))
    has_table = text.count("|") >= 8 and "\n|" in text
    has_quote_block = text.count("---") >= 2
    has_challenge_tail = bool(re.search(r"(如果你坚持|请解释|请提供|请正面回答|请回应|否则)", tail))
    has_hidden_premise_language = ("隐藏前提" in text) or ("逻辑漏洞" in text) or ("关键问题" in text)
    return {
        "opening_template": opening_template,
        "numbered_items": numbered_items,
        "heading_count": heading_count,
        "has_table": has_table,
        "has_quote_block": has_quote_block,
        "has_challenge_tail": has_challenge_tail,
        "has_hidden_premise_language": has_hidden_premise_language,
    }


def _check_structure_similarity(pos_reply: str, neg_reply: str) -> tuple[bool, str, float]:
    pos = _structure_profile(pos_reply)
    neg = _structure_profile(neg_reply)

    score = 0.0
    checks = 0

    for key in ("opening_template", "has_table", "has_quote_block", "has_challenge_tail", "has_hidden_premise_language"):
        checks += 1
        if pos[key] == neg[key] and pos[key]:
            score += 1

    checks += 1
    if min(pos["numbered_items"], neg["numbered_items"]) >= 2 and abs(pos["numbered_items"] - neg["numbered_items"]) <= 1:
        score += 1

    checks += 1
    if min(pos["heading_count"], neg["heading_count"]) >= 2 and abs(pos["heading_count"] - neg["heading_count"]) <= 1:
        score += 1

    similarity = round(score / max(checks, 1), 2)
    if similarity >= STRUCTURE_SIMILARITY_THRESHOLD:
        return False, f"[structure_warning] 正反双方本轮结构模板过于相似 (score={similarity:.2f})", similarity
    return True, "", similarity


def _check_engagement(reply: str, opponent_last: str, min_hits: int = 1) -> bool:
    """
    Three-layer engagement check.

    Layer 1 (position): top-10 opponent concepts must appear in reply's first 200 chars.
    Layer 2 (density): at least 2 concept hits in first 400 chars, OR a rebuttal verb present.
    Layer 3 (rebuttal): rebuttal verb OR 2+ concept hits in opening 400 chars.

    All three layers must pass for the reply to be considered engaged.
    Turn 0 and empty opponent_last always return True.
    """
    if not opponent_last:
        return True
    opp_concepts = [w for w, _ in _top_concepts(opponent_last, 10)]
    if not opp_concepts:
        return True

    opening_200 = reply[:200]
    opening_400 = reply[:400]

    # Layer 1: position — at least min_hits in first 200 chars
    hits_200 = sum(1 for c in opp_concepts if c in opening_200)
    if hits_200 < min_hits:
        return False

    # Layer 2 + 3 combined: either 2+ hits in 400 chars, or a rebuttal verb in 400 chars
    hits_400 = sum(1 for c in opp_concepts if c in opening_400)
    has_rebuttal = any(v in opening_400 for v in _REBUTTAL_VERBS)

    return hits_400 >= 2 or has_rebuttal


# ---------------------------------------------------------------------------
# v1.9 — Requirement completion check + engineered control prefixes
#   * completion check → decide if moderator follow-up can close
#   * hard schema      → force a 4-part reply structure when topology locks
#   * frame repair     → re-anchor a side on its own framing after colonization
# ---------------------------------------------------------------------------

_SCENARIO_MARKERS = [
    "设想", "例如", "比如", "假如", "假设",
    "如果一名", "如果一位", "如果一个", "如果某",
    "在……情境", "在…情境", "具体场景", "情境下",
    "一名孕妇", "一位孕妇", "某位孕妇", "某个孕妇",
]

_INSTITUTIONAL_MARKERS = [
    "制度后果", "法律上", "政策上", "医疗系统", "社会支持",
    "执法", "法院", "学校", "医院", "雇主", "保险",
    "社会保障", "公共卫生", "立法", "司法", "福利",
    "制度安排", "监管", "行政机关",
]

_COUNTERFACTUAL_MARKERS = [
    "如果改成", "若前提", "假如不是", "在……前提下", "在…前提下",
    "若社会支持", "若制度", "前提变化", "若将", "若改变",
    "反之", "若不是", "假如改为", "如果前提", "若条件变",
]


def check_requirement_completion(reply: str) -> dict:
    """
    Heuristic check: does the reply contain the three structural elements the
    moderator typically asks for — concrete scenario, institutional consequence,
    counterfactual / premise-shift adjustment? No LLM call; cheap keyword pass.
    """
    text = reply or ""
    has_scenario = any(kw in text for kw in _SCENARIO_MARKERS)
    has_consequence = any(kw in text for kw in _INSTITUTIONAL_MARKERS)
    has_counterfactual = any(kw in text for kw in _COUNTERFACTUAL_MARKERS)
    satisfied = sum([has_scenario, has_consequence, has_counterfactual])
    return {
        "has_concrete_scenario":         has_scenario,
        "has_institutional_consequence": has_consequence,
        "has_counterfactual_adjustment": has_counterfactual,
        "completion_score":              round(satisfied / 3.0, 2),
    }


DISCUSSION_POINT_TRACKER_SYSTEM = """你是一名辩论复盘记录员，不是辩手，不是主持人。

你的任务是维护一份"讨论点台账"。这份台账用于后期复盘和视频剪辑：记录谁在第几轮提出了什么争点，以及某个争点后来是否被明确回应、收束或解决。

你只输出 JSON 对象，包含两个字段：
{
  "new_points": [
    {
      "point": "一个稳定、可复盘的争点，必须是一句话",
      "introduced_by": "positive 或 negative",
      "source_quote": "当前轮中提出该点的短引文",
      "cluster": "权利理论 / 法律实践 / 社会后果 / 道德心理 / 制度设计 / 其他"
    }
  ],
  "resolved_points": [
    {
      "id": 1,
      "resolved_by": "positive 或 negative",
      "resolution_quote": "当前轮中回应、收束或解决该点的短引文",
      "resolution_note": "一句话说明为什么这个点算被解决、被限定、被承认或被转入新问题"
    }
  ]
}

严格规则：
- 不要重写、合并、改名已有讨论点；已有点只允许被标记为 resolved
- new_points 只记录真正推动辩论的新争点，不记录每个例子、修辞、过渡句或重复表述
- 每轮最多新增 3 个讨论点
- resolved_points 只能引用当前轮明确处理过的已有 open point；如果只是擦边提到，不算解决
- "解决"可以是：被正面回答、被对方承认、被限定到更窄条件、被主持人/双方转入新问题，或该点的关键前提被拆掉
- source_quote 和 resolution_quote 都要短，保留足够复盘定位的信息即可
- 不要输出 markdown 代码块，不要加解释文字
"""


def _normalize_side_name(value: str) -> str:
    text = _clean_state_text(value).lower()
    if text in {"positive", "pos", "正方"}:
        return "positive"
    if text in {"negative", "neg", "反方"}:
        return "negative"
    return ""


def _short_point_quote(text: str, max_len: int = 120) -> str:
    cleaned = _clean_state_text(text)
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "..."


def _next_discussion_point_id(points) -> int:
    max_id = 0
    for point in points or []:
        try:
            max_id = max(max_id, int(point.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return max_id + 1


def _apply_discussion_point_patch(current_points, patch, round_item, turn):
    """
    Apply an LLM-generated patch while preserving ledger immutability:
    existing point text is never rewritten; only resolution metadata may be added.
    """
    messages = []
    updated = [dict(point) for point in (current_points or []) if isinstance(point, dict)]
    for point in updated:
        point.setdefault("status", "open")

    id_to_point = {}
    for point in updated:
        try:
            id_to_point[int(point.get("id"))] = point
        except (TypeError, ValueError):
            continue

    next_id = _next_discussion_point_id(updated)
    existing_point_texts = {
        _clean_state_text(point.get("point", ""))
        for point in updated
        if _clean_state_text(point.get("point", ""))
    }

    new_items = patch.get("new_points", []) if isinstance(patch, dict) else []
    if not isinstance(new_items, list):
        messages.append("WARN: discussion_points.new_points was not a list")
        new_items = []
    for raw in new_items[:3]:
        if not isinstance(raw, dict):
            messages.append("WARN: dropped malformed new discussion point")
            continue
        side = _normalize_side_name(raw.get("introduced_by", ""))
        point_text = _clean_state_text(raw.get("point", ""))
        if not side or not point_text:
            messages.append("WARN: dropped new discussion point without side or point text")
            continue
        if point_text in existing_point_texts:
            messages.append("INFO: skipped duplicate discussion point")
            continue
        cluster = _clean_state_text(raw.get("cluster", ""))
        if cluster not in _OPEN_ISSUE_CLUSTERS and cluster != "其他":
            cluster = "其他"
        quote = _short_point_quote(raw.get("source_quote", "")) or _short_point_quote(
            round_item.get(side, "")
        )
        updated.append({
            "id": next_id,
            "point": point_text,
            "cluster": cluster,
            "introduced_turn": turn,
            "introduced_by": side,
            "source_quote": quote,
            "status": "open",
            "resolved_turn": None,
            "resolved_by": None,
            "resolution_quote": "",
            "resolution_note": "",
        })
        existing_point_texts.add(point_text)
        next_id += 1

    resolved_items = patch.get("resolved_points", []) if isinstance(patch, dict) else []
    if not isinstance(resolved_items, list):
        messages.append("WARN: discussion_points.resolved_points was not a list")
        resolved_items = []
    resolved_seen = set()
    for raw in resolved_items:
        if not isinstance(raw, dict):
            messages.append("WARN: dropped malformed resolved discussion point")
            continue
        try:
            point_id = int(raw.get("id"))
        except (TypeError, ValueError):
            messages.append("WARN: dropped resolved discussion point with invalid id")
            continue
        if point_id in resolved_seen:
            continue
        resolved_seen.add(point_id)
        point = id_to_point.get(point_id)
        if not point:
            messages.append(f"WARN: resolved discussion point id={point_id} not found")
            continue
        if point.get("status") == "resolved":
            continue
        side = _normalize_side_name(raw.get("resolved_by", ""))
        if not side:
            messages.append(f"WARN: resolved discussion point id={point_id} missing side")
            continue
        point["status"] = "resolved"
        point["resolved_turn"] = turn
        point["resolved_by"] = side
        point["resolution_quote"] = _short_point_quote(
            raw.get("resolution_quote", "")
        ) or _short_point_quote(round_item.get(side, ""))
        point["resolution_note"] = _clean_state_text(raw.get("resolution_note", ""))

    return updated, messages


def update_discussion_points(llm, topic, discussion_points, round_item, turn, max_retries=3):
    """Update the immutable discussion-point ledger using one completed round."""
    if not round_item:
        return discussion_points

    open_points = [
        point for point in (discussion_points or [])
        if isinstance(point, dict) and point.get("status", "open") != "resolved"
    ]
    user_content = (
        f"辩题：{topic}\n\n"
        f"当前已有讨论点台账（只可标记 resolved，不可重写 point/source_quote）：\n"
        f"{json.dumps(discussion_points or [], ensure_ascii=False, indent=2)}\n\n"
        f"当前仍未解决的讨论点：\n"
        f"{json.dumps(open_points, ensure_ascii=False, indent=2)}\n\n"
        f"第 {turn} 轮原文：\n"
        f"[正方]\n{round_item.get('positive', '')}\n\n"
        f"[反方]\n{round_item.get('negative', '')}\n\n"
        "请输出本轮对讨论点台账的 JSON patch。"
    )

    messages = [
        {"role": "system", "content": DISCUSSION_POINT_TRACKER_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(1, max_retries + 1):
        try:
            resp = llm.create_chat_completion(
                messages=messages,
                max_tokens=1536,
                temperature=0.2 if attempt == 1 else 0.1,
                top_p=0.9,
                repeat_penalty=1.05,
                stream=False,
            )
            raw = resp["choices"][0]["message"]["content"] or ""
            candidate = _extract_json_block(raw)
            if not candidate:
                raise ValueError("LLM returned no JSON object")
            patch = json.loads(candidate)
            if not isinstance(patch, dict):
                raise ValueError("patch is not a JSON object")
            updated, apply_messages = _apply_discussion_point_patch(
                discussion_points,
                patch,
                round_item,
                turn,
            )
            for msg in apply_messages:
                print(f"[discussion_points] {msg}")
            added = len(updated) - len(discussion_points or [])
            resolved = sum(
                1
                for point in updated
                if point.get("resolved_turn") == turn and point.get("status") == "resolved"
            )
            print(f"[discussion_points] round={turn} added={added} resolved={resolved}")
            return updated
        except (json.JSONDecodeError, ValueError) as e:
            preview = (raw if "raw" in locals() else "").strip().replace("\n", "\\n")
            if len(preview) > 240:
                preview = preview[:240] + "...<truncated>"
            print(f"[discussion_points] attempt {attempt}/{max_retries} failed: {e}")
            if preview:
                print(f"[discussion_points] raw output preview: {preview}")
            messages.append({"role": "assistant", "content": raw if "raw" in locals() else ""})
            messages.append({
                "role": "user",
                "content": (
                    "你上一次输出不是合法 JSON patch。请只输出："
                    "{\"new_points\": [...], \"resolved_points\": [...]}"
                    "不要 markdown，不要解释。"
                ),
            })

    print("[discussion_points] failed to update, keeping previous ledger")
    return discussion_points


def build_topology_hard_schema() -> str:
    """
    Fixed per-round structure template injected when the topology controller
    decides to force a branch switch. The system — not the moderator — issues
    the schema so it cannot be rephrased away by the debater LLM.
    """
    return (
        "[本轮结构要求]\n"
        "你本轮必须按以下顺序组织回答：\n"
        "1. 先给出一个具体场景（明确角色、条件、情境）\n"
        "2. 说明该场景下的制度/社会/行为后果\n"
        "3. 说明如果前提改变，你方立场如何调整\n"
        "4. 最后回到原题，说明这如何支持你的核心立场\n\n"
        "若未满足上述结构，则视为未完成本轮要求。\n"
        "禁止只重复抽象原则。\n"
    )


def build_frame_repair_prompt(side: str) -> str:
    """
    Lightweight repair prompt injected on the turn AFTER a side's reply was
    detected as colonized by the opponent's framing. Kept short on purpose —
    long repair prompts start stealing attention weight from the actual task.
    """
    side_label = "正方" if side == "positive" else "反方"
    return (
        "[框架回正要求]\n"
        f"警告：你（{side_label}）最近一轮的组织方式明显沿用了对方的争点框架。\n"
        "你本轮必须先用你方自己的判断重新定义当前争点，再回应对方。\n"
        "禁止直接接受对方设定的问题前提为默认前提。\n"
        "可以回应对方，但必须先说明你方认为真正该讨论的是什么。\n"
    )


def _top_concepts(text, n=10):
    """Extract top-N CJK concept words (2–4 chars) by frequency."""
    words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    return Counter(words).most_common(n)


def _jaccard(set_a, set_b):
    """Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


def validate_debate_state(state: dict, known_unverified_refs=None) -> tuple[bool, dict | None, list]:
    """
    Validate and normalize the new two-layer debate_state schema.
    Returns (ok, normalized_state, messages).
    """
    ok, normalized, messages = normalize_debate_state(
        state, known_unverified_refs=known_unverified_refs
    )
    if not ok or not normalized:
        return ok, normalized, messages

    ss = normalized["side_state"]
    pos_d = ss.get("positive", {})
    neg_d = ss.get("negative", {})

    if not pos_d.get("strongest_claims"):
        messages.append("WARN: positive.strongest_claims is empty")
    if not neg_d.get("strongest_claims"):
        messages.append("WARN: negative.strongest_claims is empty")

    pos_claims = " ".join(pos_d.get("strongest_claims", []))
    neg_claims = " ".join(neg_d.get("strongest_claims", []))
    if pos_claims and neg_claims:
        pos_w = set(re.findall(r'[\u4e00-\u9fff]{2,4}', pos_claims))
        neg_w = set(re.findall(r'[\u4e00-\u9fff]{2,4}', neg_claims))
        jac = _jaccard(pos_w, neg_w)
        if jac > 0.55:
            messages.append(f"WARN: positive/negative strongest_claims Jaccard too high: {jac:.2f}")

    return True, normalized, messages


def _compute_state_scores(rounds, window=TRIGGER_WINDOW):
    """
    Compute state scores from recent rounds. Pure arithmetic — no threshold decisions here.

    Scores (all 0–1):
      abstract_drift   — how abstract / untethered the discourse is
      repetition_score — full-vocabulary Jaccard overlap between consecutive rounds
      deadlock_score   — top-concept Jaccard (focused convergence / narrowing)
      realism_score    — density of concrete institutional anchors
      branch_poverty   — how few distinct premise slots have been touched across ALL rounds
      premise_absence  — fraction of PREMISE_SLOTS never mentioned (across all rounds)
      severity         — weighted composite (excludes intervention_failure; added in assess_round)
    """
    recent = rounds[-min(window, len(rounds)):] if rounds else []
    per_round = [r["positive"] + " " + r["negative"] for r in recent]
    combined = " ".join(per_round)
    n = max(len(recent), 1)

    abstract_hits = sum(combined.count(m) for m in _ABSTRACT_MARKERS)
    concrete_hits = sum(combined.count(m) for m in _CONCRETE_MARKERS)

    abstract_density = abstract_hits / (n * 100)
    concrete_density = concrete_hits / (n * 100)
    abstract_drift = max(0.0, min(1.0, abstract_density - concrete_density * 0.5))

    realism_score = min(1.0, concrete_hits / max(n * 3, 1))

    # Deadlock score: top-concept Jaccard (measures focus convergence / narrowing)
    jaccard_vals = []
    for i in range(1, len(per_round)):
        prev_words = {w for w, _ in _top_concepts(per_round[i - 1], 15)}
        curr_words = {w for w, _ in _top_concepts(per_round[i], 15)}
        jaccard_vals.append(_jaccard(prev_words, curr_words))
    deadlock_score = sum(jaccard_vals) / len(jaccard_vals) if jaccard_vals else 0.0

    # Repetition score: full-vocabulary Jaccard (measures sentence/phrase reuse across rounds)
    rep_jaccard_vals = []
    for i in range(1, len(per_round)):
        prev_all = set(re.findall(r'[\u4e00-\u9fff]{2,4}', per_round[i - 1]))
        curr_all = set(re.findall(r'[\u4e00-\u9fff]{2,4}', per_round[i]))
        rep_jaccard_vals.append(_jaccard(prev_all, curr_all))
    repetition_score = sum(rep_jaccard_vals) / len(rep_jaccard_vals) if rep_jaccard_vals else 0.0

    # Branch poverty and premise absence — computed over ALL rounds, not just the window
    all_text = " ".join(
        r.get("positive", "") + " " + r.get("negative", "") for r in rounds
    )
    touched_count = sum(1 for p in PREMISE_SLOTS if p in all_text)
    total_slots = max(len(PREMISE_SLOTS), 1)
    premise_absence = 1.0 - touched_count / total_slots
    # Branch poverty: after N rounds we expect proportionally more slots to have been touched
    total_rounds = max(len(rounds), 1)
    expected_touched = min(total_slots, total_rounds * 1.5)
    branch_poverty = max(0.0, min(1.0, 1.0 - touched_count / max(expected_touched, 1)))

    # Base severity: 6-dim weighted composite.
    # branch_poverty fills the intervention_failure slot in pure computation;
    # intervention_failure is added on top in assess_round (requires moderator_state).
    severity = round(min(1.0,
        abstract_drift      * 0.22 +
        repetition_score    * 0.18 +
        deadlock_score      * 0.18 +
        premise_absence     * 0.16 +
        (1.0 - realism_score) * 0.14 +
        branch_poverty      * 0.12
    ), 3)

    return {
        "abstract_drift":   round(abstract_drift, 3),
        "repetition_score": round(repetition_score, 3),
        "deadlock_score":   round(deadlock_score, 3),
        "realism_score":    round(realism_score, 3),
        "branch_poverty":   round(branch_poverty, 3),
        "premise_absence":  round(premise_absence, 3),
        "severity":         severity,
        "abstract_hits":    abstract_hits,
        "concrete_hits":    concrete_hits,
        "n_rounds":         n,
    }


def _check_follow_up(targets, recent_rounds):
    """
    Check whether the debaters actually followed the last intervention's suggested directions.
    Returns True (followed) if at least one target keyword appears in the recent rounds.
    Returns True vacuously when no targets or no rounds are provided.
    """
    if not targets or not recent_rounds:
        return True
    normalized_targets = []
    for target in targets:
        if isinstance(target, dict):
            text = _clean_state_text(target.get("text", ""))
        else:
            text = _clean_state_text(target)
        if text:
            normalized_targets.append(text)
    if not normalized_targets:
        return True
    combined = " ".join(
        r.get("positive", "") + " " + r.get("negative", "") for r in recent_rounds
    )
    return any(t in combined for t in normalized_targets)


def _find_untouched_premises(rounds):
    """
    Return premise slots from PREMISE_SLOTS that have never appeared in any round.
    Checks both positive and negative text across all rounds.
    """
    all_text = " ".join(
        r.get("positive", "") + " " + r.get("negative", "") for r in rounds
    )
    return [p for p in PREMISE_SLOTS if p not in all_text]


def assess_round(rounds, moderator_state=None, window=TRIGGER_WINDOW):
    """
    Every-turn silent assessment. Pure heuristics — no LLM call.
    Returns a structured judgment dict consumed by the main loop and run_moderator().

    Fields:
        should_intervene           bool
        issue_type                 str | None
        severity                   float  0–1  (includes intervention_failure boost)
        recommended_mode           "light" | "medium" | "heavy" | None
        candidate_directions       list[str]   (untouched premises, up to 4)
        untouched_premises         list[str]   (all untouched)
        reasoning_summary          str
        intervention_failure_score float  0 or 0.8
        last_intervention_targets  list[str]   (from moderator_state, for run_moderator)
    """
    empty_base = {
        "should_intervene": False,
        "issue_type": None,
        "severity": 0.0,
        "recommended_mode": None,
        "candidate_directions": [],
        "untouched_premises": _find_untouched_premises(rounds),
        "reasoning_summary": "轮次不足，暂不评估。",
        "intervention_failure_score": 0.0,
        "last_intervention_targets": [],
        "active_requirements": [],
    }
    if len(rounds) < 2:
        return empty_base

    scores = _compute_state_scores(rounds, window)
    topology = TOPOLOGY_CONTROLLER.analyze(rounds)
    ad  = scores["abstract_drift"]
    rep = scores["repetition_score"]
    dl  = scores["deadlock_score"]
    rs  = scores["realism_score"]
    bp  = scores["branch_poverty"]
    base_sev = scores["severity"]
    n   = scores["n_rounds"]
    untouched = _find_untouched_premises(rounds)
    topology_lock = topology["cluster_lock"]
    topology_penalty = 0.10 if topology_lock else 0.0

    # --- Intervention failure score ---
    intervention_failure_score = 0.0
    follow_up_check_failed = False
    last_targets = []
    active_requirements = []
    if moderator_state is not None:
        active_requirements = [
            req.get("text", "")
            for req in moderator_state.get("pending_requirements", [])
            if isinstance(req, dict) and req.get("text")
        ]
        last_targets = active_requirements or moderator_state.get("last_intervention_targets", [])
        if (moderator_state.get("must_follow_up")
                and moderator_state.get("follow_up_window", 0) > 0):
            followed = _check_follow_up(last_targets, rounds[-2:])
            if not followed:
                intervention_failure_score = 0.8
                follow_up_check_failed = True

    # Final severity: base + intervention_failure boost, capped at 1
    sev = round(min(1.0, base_sev + topology_penalty + intervention_failure_score * 0.12), 3)

    # --- Hard trigger rules (bypass score threshold) ---
    hard_trigger = False
    hard_issue = None

    if follow_up_check_failed:
        hard_trigger = True
        hard_issue = "followup_check"
    elif topology_lock:
        hard_trigger = True
        hard_issue = "topology_lock"
    elif n >= 2 and scores["concrete_hits"] == 0:
        # No real-world anchors in the assessment window at all
        hard_trigger = True
        hard_issue = "reality_disconnected"
    elif dl >= 0.75:
        hard_trigger = True
        hard_issue = "single_point_deadlock"
    elif rep >= 0.65:
        hard_trigger = True
        hard_issue = "repetition"

    # --- Determine primary issue type (hard rules first, then score-based) ---
    if hard_trigger:
        issue_type = hard_issue
    else:
        issue_type = None
        if ad >= 0.6 and rs < 0.05:
            issue_type = "reality_disconnected"
        elif ad >= 0.35 and rs < 0.20:
            issue_type = "abstract_loop"
        elif dl >= 0.60:
            issue_type = "single_point_deadlock"
        elif rep >= 0.50:
            issue_type = "repetition"
        elif topology_lock:
            issue_type = "topology_lock"
        elif len(untouched) >= 4:
            issue_type = "premise_unchecked"
        elif bp >= 0.70 and len(rounds) >= 4:
            issue_type = "branch_poverty"

    # --- Intervention level ---
    if hard_trigger:
        # Hard triggers are at least medium; follow-up failures and critical severity → heavy
        if follow_up_check_failed or sev >= HIGH_SEVERITY_OVERRIDE:
            recommended_mode = "heavy"
        else:
            recommended_mode = "medium"
    elif sev < SEVERITY_THRESHOLD or issue_type is None:
        recommended_mode = None
    elif sev < 0.55:
        recommended_mode = "light"
    elif sev < HIGH_SEVERITY_OVERRIDE:
        recommended_mode = "medium"
    else:
        recommended_mode = "heavy"

    should_intervene = recommended_mode is not None

    # --- Reasoning summary ---
    parts = []
    if ad >= 0.25:
        parts.append(f"抽象漂移 {ad:.2f}")
    if rep >= 0.35:
        parts.append(f"重复复读 {rep:.2f}")
    if dl >= 0.40:
        parts.append(f"争点收缩 {dl:.2f}")
    if rs < 0.25:
        parts.append(f"现实连接 {rs:.2f}")
    if bp >= 0.50:
        parts.append(f"分支贫乏 {bp:.2f}")
    if topology_lock and topology.get("dominant_cluster"):
        parts.append(f"拓扑锁定 {topology['dominant_cluster']}")
    if follow_up_check_failed:
        parts.append("介入失效")
    reasoning = "、".join(parts) if parts else "暂无明显问题"
    if untouched:
        reasoning += f"；未触碰前提：{'、'.join(untouched[:3])}"

    candidate_directions = untouched[:4]
    if issue_type == "topology_lock":
        candidate_directions = topology.get("expand_dimension", [])[:4] or untouched[:4]

    return {
        "should_intervene":          should_intervene,
        "issue_type":                issue_type,
        "severity":                  sev,
        "recommended_mode":          recommended_mode,
        "candidate_directions":      candidate_directions,
        "untouched_premises":        untouched,
        "reasoning_summary":         reasoning,
        "intervention_failure_score": intervention_failure_score,
        "last_intervention_targets": last_targets,
        "active_requirements":       active_requirements,
        "argument_clusters":         topology.get("argument_clusters", []),
        "dominant_cluster":          topology.get("dominant_cluster"),
        "expand_dimension":          topology.get("expand_dimension", []),
    }


def run_moderator(llm, topic, recent_rounds, state, assessment):
    """
    Call the moderator LLM using the structured assessment from assess_round().
    Returns the intervention text (str), or None on failure / invalid output.
    """
    issue_type = assessment.get("issue_type", "")
    issue_label = {
        "abstract_loop":         "抽象过度",
        "single_point_deadlock": "单点死磕",
        "premise_unchecked":     "前提未检验",
        "reality_disconnected":  "现实脱节",
        "branch_poverty":        "分支贫乏",
        "topology_lock":         "分支贫乏",
        "repetition":            "重复复读",
        "followup_check":        "介入失效",
    }.get(issue_type, "其他")

    # Map issue to recommended intervention type
    intervention_type_label = {
        "abstract_loop":         "现实落地",
        "reality_disconnected":  "现实落地",
        "single_point_deadlock": "强制选场景",
        "premise_unchecked":     "前提显化",
        "branch_poverty":        "分支扩展",
        "topology_lock":         "分支扩展",
        "repetition":            "分支扩展",
        "followup_check":        "执行检查",
    }.get(issue_type, "现实落地")

    mode_label = {
        "light":  "轻介入",
        "medium": "中介入",
        "heavy":  "强介入",
    }.get(assessment.get("recommended_mode", "medium"), "中介入")

    scores = _compute_state_scores(recent_rounds)
    shared_state = state.get("shared_state", {}) if isinstance(state, dict) else {}

    combined_text = " ".join(
        r.get("positive", "") + " " + r.get("negative", "") for r in recent_rounds
    )
    top_words = [w for w, _ in _top_concepts(combined_text, 6)]
    current_focus = "、".join(top_words) if top_words else "（无法提取）"

    moderator_input = {
        "trigger_reason":             issue_label,
        "recommended_intervention":   intervention_type_label,
        "severity":                   assessment["severity"],
        "recommended_mode":           mode_label,
        "current_focus":              f"近期高频词：{current_focus}",
        "abstract_drift_score":       scores["abstract_drift"],
        "repetition_score":           scores["repetition_score"],
        "deadlock_score":             scores["deadlock_score"],
        "realism_score":              scores["realism_score"],
        "branch_poverty_score":       scores["branch_poverty"],
        "intervention_failure_score": assessment.get("intervention_failure_score", 0.0),
        "candidate_directions":       assessment.get("candidate_directions", []),
        "untouched_premises":         assessment.get("untouched_premises", [])[:6],
        "current_open_issues":        shared_state.get("open_issues", []),
        "active_requirements":        assessment.get("active_requirements", []),
        "argument_clusters":          assessment.get("argument_clusters", []),
        "dominant_cluster":           assessment.get("dominant_cluster"),
        "expand_dimension":           assessment.get("expand_dimension", []),
        "reasoning":                  assessment.get("reasoning_summary", ""),
    }

    # For follow-up checks, include the targets from the last intervention
    last_targets = assessment.get("last_intervention_targets", [])
    if issue_type == "followup_check" and last_targets:
        moderator_input["last_intervention_targets"] = last_targets

    rounds_text = []
    for i, r in enumerate(recent_rounds, 1):
        rounds_text.append(
            f"[第 {i} 轮 正方]\n{r['positive']}\n\n[第 {i} 轮 反方]\n{r['negative']}"
        )

    followup_note = ""
    if issue_type == "followup_check":
        targets_str = "、".join(last_targets) if last_targets else "（未记录）"
        followup_note = (
            f"\n注意：本次触发原因是【介入失效】。上次介入要求双方落实的方向为：{targets_str}。"
            "请使用【执行检查】类型介入，直接点名哪个要求未完成，输出要短而硬，不要再开新方向。\n"
        )

    user_content = (
        "以下是当前辩论的结构化状态（系统已决定介入，你无需重新判断是否该介入）：\n\n"
        f"{json.dumps(moderator_input, ensure_ascii=False, indent=2)}\n\n"
        f"系统指定介入强度：{mode_label}\n"
        f"推荐介入方式：{intervention_type_label}\n"
        f"{followup_note}\n"
        f"最近几轮原文（供参考）：\n{'---'.join(rounds_text)}\n\n"
        "请根据触发原因和指定强度，按照你的固定输出格式进行介入。"
    )

    try:
        resp = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": MODERATOR_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2048,
            temperature=0.3,
            top_p=0.9,
            repeat_penalty=1.05,
            stream=False,
        )
        content = resp["choices"][0]["message"]["content"] or ""
        result = content.strip()

        # Output validation: must contain the expected section markers
        if not result:
            print("[moderator] empty output — skipping intervention")
            return None
        if "[介入理由]" not in result:
            print("[moderator] output missing expected sections — skipping intervention")
            print(f"[moderator] raw preview: {result[:200]}")
            return None

        return result
    except Exception as e:
        print(f"[moderator] call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# LLM client wrappers — unified interface used by the whole debate loop
# ---------------------------------------------------------------------------

def _merge_consecutive(messages):
    """Merge back-to-back messages with the same role (required by Gemini)."""
    merged = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1] = {
                "role": m["role"],
                "content": merged[-1]["content"] + "\n\n" + m["content"],
            }
        else:
            merged.append(dict(m))
    return merged


class LocalLLMClient:
    """Wraps llama_cpp.Llama."""

    def __init__(self, model_path, n_gpu_layers=-1, n_ctx=16384):
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("Install llama-cpp-python:  pip install llama-cpp-python")
        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
        )

    def create_chat_completion(self, messages, max_tokens, temperature,
                               top_p=0.95, repeat_penalty=1.0, stream=False):
        return self._llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stream=stream,
        )


class OpenAICompatibleClient:
    """Covers OpenAI, OpenRouter, and Grok (all use the OpenAI SDK)."""

    def __init__(self, api_key, base_url=None, model="gpt-4o"):
        try:
            import openai
        except ImportError:
            raise ImportError("Install openai:  pip install openai")
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def create_chat_completion(self, messages, max_tokens, temperature,
                               top_p=0.95, repeat_penalty=1.0, stream=False):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=stream,
        )
        if stream:
            def _gen():
                for chunk in resp:
                    content = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    yield {"choices": [{"delta": {"content": content}}]}
            return _gen()
        return {"choices": [{"message": {"content": resp.choices[0].message.content}}]}


class AnthropicClient:
    """Anthropic Claude API."""

    def __init__(self, api_key, model="claude-opus-4-6"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic:  pip install anthropic")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def create_chat_completion(self, messages, max_tokens, temperature,
                               top_p=0.95, repeat_penalty=1.0, stream=False):
        # Anthropic takes a single system string; extract and merge all system messages
        system_parts, conv = [], []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                conv.append(m)
        conv = _merge_consecutive(conv)
        system_text = "\n\n".join(system_parts) or None

        kwargs = dict(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            messages=conv,
        )
        if system_text:
            kwargs["system"] = system_text

        if stream:
            resp = self._client.messages.create(**kwargs, stream=True)
            def _gen():
                for event in resp:
                    if (event.type == "content_block_delta"
                            and hasattr(event.delta, "text")):
                        yield {"choices": [{"delta": {"content": event.delta.text}}]}
            return _gen()

        resp = self._client.messages.create(**kwargs)
        return {"choices": [{"message": {"content": resp.content[0].text}}]}


class GeminiClient:
    """Google Gemini API via google-generativeai."""

    def __init__(self, api_key, model="gemini-2.5-pro"):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "Install google-generativeai:  pip install google-generativeai"
            )
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    def create_chat_completion(self, messages, max_tokens, temperature,
                               top_p=0.95, repeat_penalty=1.0, stream=False):
        system_parts, conv = [], []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                conv.append(m)
        conv = _merge_consecutive(conv)
        system_text = "\n\n".join(system_parts) or None

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_text,
            generation_config=self._genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ),
        )

        # Split history (all but last message) from the prompt to send
        history = []
        for m in conv[:-1]:
            role = "model" if m["role"] == "assistant" else "user"
            history.append({"role": role, "parts": [m["content"]]})
        last_content = conv[-1]["content"] if conv else ""

        chat = model.start_chat(history=history)

        if stream:
            resp = chat.send_message(last_content, stream=True)
            def _gen():
                for chunk in resp:
                    text = getattr(chunk, "text", "") or ""
                    if text:
                        yield {"choices": [{"delta": {"content": text}}]}
            return _gen()

        resp = chat.send_message(last_content)
        return {"choices": [{"message": {"content": resp.text}}]}


def build_client(provider: str, model: str | None = None):
    """Factory — instantiate the right client for the chosen provider."""
    cfg = PROVIDER_CONFIGS[provider]
    model = model or cfg.get("default_model")

    if provider == "local":
        return LocalLLMClient(
            model_path=cfg["model_path"],
            n_gpu_layers=cfg["n_gpu_layers"],
            n_ctx=cfg["n_ctx"],
        )

    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        _k = cfg["api_key_env"]
        raise ValueError(
            f"Environment variable {_k} is not set.\n"
            f"  PowerShell:  $env:{_k} = \"<your-key>\"\n"
            f"  CMD:         set {_k}=<your-key>\n"
            f"  bash/zsh:    export {_k}=<your-key>"
        )

    if provider == "anthropic":
        return AnthropicClient(api_key=api_key, model=model)

    if provider == "gemini":
        return GeminiClient(api_key=api_key, model=model)

    # OpenAI-compatible: openai / openrouter / grok
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=cfg.get("base_url"),
        model=model,
    )


def stream_reply(llm, messages, label):
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=REPLY_MAX_TOKENS,
        temperature=0.7,
        top_p=0.95,
        repeat_penalty=1.1,
        stream=True,
    )
    print(f"{label}: ", end="", flush=True)
    full = ""
    for chunk in response:
        delta = chunk["choices"][0]["delta"].get("content", "")
        print(delta, end="", flush=True)
        full += delta
    print("\n")
    return full


def main():
    global TOPIC_FULL, TOPIC_PUBLIC, TOPIC_POS_BRIEF, TOPIC_NEG_BRIEF, REPLY_MAX_TOKENS

    parser = argparse.ArgumentParser(
        description="LLM Debate — run a two-sided debate using a local or API model.",
        epilog=(
            "API key environment variables:\n"
            "  openai      -> OPENAI_API_KEY\n"
            "  anthropic   -> ANTHROPIC_API_KEY\n"
            "  gemini      -> GOOGLE_API_KEY\n"
            "  openrouter  -> OPENROUTER_API_KEY\n"
            "  grok        -> XAI_API_KEY\n"
            "\n"
            "Set them before running:\n"
            "  PowerShell:  $env:OPENROUTER_API_KEY = \"sk-or-...\"\n"
            "  CMD:         set OPENROUTER_API_KEY=sk-or-...\n"
            "  bash/zsh:    export OPENROUTER_API_KEY=sk-or-...\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        default="local",
        choices=list(PROVIDER_CONFIGS),
        help="LLM provider to use (default: local)",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help="Model name override — uses each provider's default if not set",
    )
    topic_group = parser.add_mutually_exclusive_group(required=True)
    topic_group.add_argument(
        "--topic",
        default=None,
        help="Raw debate topic for direct/manual runs. For production pipeline runs, prefer debate_pipeline.py from-topic --topic so a full framework is generated first.",
    )
    topic_group.add_argument(
        "--topic-file",
        default=None,
        help="Markdown topic framework generated by debate_topic_generator.py.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=MAX_TURNS,
        help=f"Number of full positive/negative rounds (default: {MAX_TURNS}).",
    )
    parser.add_argument(
        "--reply-max-tokens",
        type=int,
        default=REPLY_MAX_TOKENS,
        help=f"Per-speaker response token limit (default: {REPLY_MAX_TOKENS}).",
    )
    args = parser.parse_args()
    if args.turns < 1:
        parser.error("--turns must be >= 1")
    if args.reply_max_tokens < 256:
        parser.error("--reply-max-tokens must be >= 256")

    TOPIC_FULL, TOPIC_PUBLIC, TOPIC_POS_BRIEF, TOPIC_NEG_BRIEF = load_topic_bundle(
        args.topic,
        args.topic_file,
    )
    max_turns = args.turns
    REPLY_MAX_TOKENS = args.reply_max_tokens

    cfg = PROVIDER_CONFIGS[args.provider]
    model_label = args.model or cfg.get("default_model") or os.path.basename(cfg.get("model_path", ""))
    print(
        f"[Provider: {args.provider}  Model: {model_label}  "
        f"Turns: {max_turns}  Reply max tokens: {REPLY_MAX_TOKENS}]\n"
    )

    llm = build_client(args.provider, args.model)

    print(f"Debate topic: {TOPIC_PUBLIC}\n")

    # Transcript for JSON log (flat, speaker-labeled)
    transcript = []
    # Rounds: list of {"positive": str, "negative": str} — used for recent-window replay + summarization
    rounds = []
    # Long-term compressed state
    debate_state = None
    # Immutable review ledger: new points are appended; resolved points only get
    # resolution metadata so later video/review tooling can trace the arc.
    discussion_points = []

    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("[生成标题摘要中...]")
    title_slug = summarize_topic_for_title(llm, TOPIC_FULL)
    print(f"[标题摘要: {title_slug}]\n")
    version_slug = sanitize_filename_component(VERSION, max_len=16, fallback="version")
    title_slug = sanitize_filename_component(title_slug, max_len=32, fallback="title")
    model_slug = sanitize_filename_component(model_label, max_len=48, fallback="model")
    log_path = os.path.join(
        LOG_DIR,
        f"debate_{version_slug}_{title_slug}_{model_slug}_{ts}.json"
    )

    # Engagement streak: count of consecutive turns where any side failed the check.
    # Used to escalate from "retry once" to "force rewrite" on chronic failures.
    consecutive_engagement_failures = 0

    # Moderator persistent state — tracks interventions across the whole debate
    moderator_state = {
        "last_intervention_round":   -1,
        "last_intervention_type":    None,
        "last_intervention_targets": [],
        "intervention_count":        0,
        "recent_trigger_scores":     [],
        "must_follow_up":            False,
        "follow_up_window":          0,
        "pending_requirements":      [],   # structured requirements from last intervention
        "failed_followup_count":     0,    # consecutive unmet follow-up count
    }
    pending_moderator_msg = None      # injected into next turn's inputs

    # v1.9 — Engineered control queues (fixed by code, not rephrased by LLM).
    # frame_repair_pending: consecutive frame-colonization warnings per side;
    # hitting the threshold prepends a repair prompt to that side's next input.
    frame_repair_pending = {"positive": 0, "negative": 0}
    # hard_schema_pending: when topology locks / deadlocks / branch-poverty
    # trips, force both sides' next reply into a fixed 4-part schema.
    hard_schema_pending = {"positive": False, "negative": False}

    # v1.9 — Topology metrics: summary counters written to the final log for
    # model comparison (which model locks into a single cluster, etc.).
    topology_metrics = {
        "clusters_touched":              [],
        "per_round_cluster":             [],
        "cluster_switch_count":          0,
        "longest_single_cluster_run":    0,
        "frame_warning_count":           0,
        "mirror_warning_count":          0,
        "structure_warning_count":       0,
        "hard_topology_mode_triggered":  0,
        "requirement_completion_scores": [],
    }

    FRAME_REPAIR_THRESHOLD = 2  # consecutive warnings before repair prompt fires

    def _consume_controls(side):
        """Build and consume per-side structural control prefix for this turn."""
        parts = []
        if frame_repair_pending[side] >= FRAME_REPAIR_THRESHOLD:
            parts.append(build_frame_repair_prompt(side))
            frame_repair_pending[side] = 0
            print(f"[frame_repair] 注入 {side} 框架回正提示")
        if hard_schema_pending[side]:
            parts.append(build_topology_hard_schema())
            hard_schema_pending[side] = False
            print(f"[topology_hard_mode] 注入 {side} 硬结构模板")
        if not parts:
            return ""
        return "\n".join(parts) + "\n"

    def save_log(completed_turns):
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": VERSION,
                "topic": TOPIC_FULL,
                "model": f"{args.provider}/{model_label}",
                "timestamp": ts,
                "max_turns": max_turns,
                "turns": completed_turns,
                "debate_state": debate_state,
                "moderator_state": moderator_state,
                "topology_metrics": topology_metrics,
                "discussion_points": discussion_points,
                "transcript": transcript,
            }, f, ensure_ascii=False, indent=2)

    try:
        for turn in range(max_turns):
            is_final = (turn == max_turns - 1)
            final_tail = build_final_round_instruction() if is_final else ""

            # Per-turn system prompts (rules + stance only — no state injected here)
            pos_system = (
                build_system_prompt("positive", turn, max_turns)
                + "\n你的立场是正方。你必须为该辩题成立提供最强论证，并主动反击反方的质疑。"
            )
            neg_system = (
                build_system_prompt("negative", turn, max_turns)
                + "\n你的立场是反方。你必须论证该辩题不能成立，并主动攻击正方论证中的关键漏洞。"
            )

            # Near-memory window: keep last RECENT_WINDOW rounds verbatim
            recent_rounds = rounds[-RECENT_WINDOW:] if rounds else []
            active_requirements = _refresh_pending_requirements(
                moderator_state, debate_state, rounds, turn + 1
            )

            # Consume pending moderator message (produced at end of previous round)
            mod_prefix = f"[主持人]\n{pending_moderator_msg}\n\n" if pending_moderator_msg else ""
            pending_moderator_msg = None

            # v1.9 — Engineered structural controls (frame repair + hard schema).
            # Code-issued, not moderator-rephrased, so they carry heavier weight.
            pos_controls = _consume_controls("positive")

            # ── Positive speaks ──────────────────────────────────────────────────────
            if turn == 0:
                pos_input = (
                    mod_prefix
                    + pos_controls
                    + "请你作为正方，开场陈述你对该辩题的立场与核心论点。"
                    + final_tail
                )
            else:
                last_neg = rounds[-1]["negative"]
                state_ctx_pos = _make_state_context(
                    debate_state, "positive", active_requirements=active_requirements
                )
                pos_input = (
                    mod_prefix
                    + pos_controls
                    + "[你必须首先回应的对象]\n"
                    "以下是对方上一条原文，请先处理其中最关键的一点：\n"
                    "---\n"
                    f"{last_neg}\n"
                    "---\n\n"
                    + (f"[仅供背景参考，不得优先于上面的原文]\n{state_ctx_pos}\n\n" if state_ctx_pos else "")
                    + "[你的任务]\n"
                    "1. 先明确指出对方上一条中你要打的一个具体论断\n"
                    "2. 再展开你的推进与反驳\n"
                    "3. 不要只评论全局焦点，必须先贴住对方原文\n"
                    + final_tail
                )

            pos_messages = build_history(pos_system, recent_rounds, "positive", pos_input)
            pos_reply = stream_reply(llm, pos_messages, "正方")

            # Engagement check — must reference opponent's last utterance in opening
            if turn == 0:
                pos_engaged = True
            else:
                pos_engaged = _check_engagement(pos_reply, rounds[-1]["negative"])
                if not pos_engaged:
                    if consecutive_engagement_failures >= 2:
                        force_note = (
                            "[强制重写] 连续多轮未直接回应对方。本次必须：\n"
                            "先用一句话复述[对方上一轮发言]中的一个核心主张，再立刻给出具体反驳。\n"
                        )
                        pos_messages_forced = build_history(
                            pos_system, recent_rounds, "positive", force_note + pos_input
                        )
                        print("[engagement_check] 正方连续失败，强制重写...")
                        pos_reply = stream_reply(llm, pos_messages_forced, "正方[强制重写]")
                    else:
                        print("[engagement_check] 正方未命中对方具体论点，重试一次...")
                        pos_reply = stream_reply(llm, pos_messages, "正方[重试]")
                    pos_engaged = _check_engagement(pos_reply, rounds[-1]["negative"])

            # Stance check — semi-blocking: retry once on failure
            pos_ok, pos_warn = _check_stance(pos_reply, "positive")
            if not pos_ok:
                print(pos_warn + " — 重试一次")
                pos_reply = stream_reply(llm, pos_messages, "正方[stance重试]")
                pos_ok, pos_warn = _check_stance(pos_reply, "positive")

            pos_ref_ok, pos_ref_warn, pos_ref_hits = _check_reference_risk(pos_reply, "positive")
            if not pos_ref_ok:
                print(pos_ref_warn)
                transcript.append({"turn": turn + 1, "speaker": "reference_risk_warning", "content": pos_ref_warn})

            # v1.9 §6: soft-replace hallucinated high-precision legal citations
            pos_soften_text, pos_soften_replaced = _soft_replace_legal_material(pos_reply)
            if pos_soften_replaced:
                pos_reply = pos_soften_text
                soften_note = (
                    f"[legal_soften:正方] 已将 {len(pos_soften_replaced)} 处未验证的高精度法律引用替换为低精度表达："
                    + "；".join(pos_soften_replaced[:4])
                )
                print(soften_note)
                transcript.append({"turn": turn + 1, "speaker": "legal_soften", "content": soften_note})

            # Frame colonization check — warning logged; consecutive hits queue a repair prompt.
            pos_frame_ok, pos_frame_warn = _check_frame_colonization(
                pos_reply, "positive", state=debate_state
            )
            if not pos_frame_ok:
                print(pos_frame_warn)
                transcript.append({"turn": turn + 1, "speaker": "frame_warning", "content": pos_frame_warn})
                frame_repair_pending["positive"] += 1
                topology_metrics["frame_warning_count"] += 1
            else:
                frame_repair_pending["positive"] = 0

            transcript.append({"turn": turn + 1, "speaker": "positive", "content": pos_reply})
            if not pos_ok:
                print(pos_warn + " — 重试后仍未通过，保留输出")
                transcript.append({"turn": turn + 1, "speaker": "stance_warning", "content": pos_warn})
            save_log(turn + 1)

            # ── Negative speaks ──────────────────────────────────────────────────────
            # State is per-side; negative gets its own combat brief, not positive's.
            # pos_reply is quoted explicitly in neg_input — no need to append to recent_rounds.
            state_ctx_neg = _make_state_context(
                debate_state, "negative", active_requirements=active_requirements
            )
            neg_controls = _consume_controls("negative")
            neg_input = (
                mod_prefix
                + neg_controls
                + "[你必须首先回应的对象]\n"
                "以下是对方上一条原文，请先处理其中最关键的一点：\n"
                "---\n"
                f"{pos_reply}\n"
                "---\n\n"
                + (f"[仅供背景参考，不得优先于上面的原文]\n{state_ctx_neg}\n\n" if state_ctx_neg else "")
                + "[你的任务]\n"
                "1. 先明确指出对方上一条中你要打的一个具体论断\n"
                "2. 再展开你的推进与反驳\n"
                "3. 不要只评论全局焦点，必须先贴住对方原文\n"
                + final_tail
            )
            neg_messages = build_history(neg_system, recent_rounds, "negative", neg_input)
            neg_reply = stream_reply(llm, neg_messages, "反方")

            # Engagement check
            neg_engaged = _check_engagement(neg_reply, pos_reply)
            if not neg_engaged:
                if consecutive_engagement_failures >= 2:
                    force_note = (
                        "[强制重写] 连续多轮未直接回应对方。本次必须：\n"
                        "先用一句话复述[对方上一轮发言]中的一个核心主张，再立刻给出具体反驳。\n"
                    )
                    neg_messages_forced = build_history(
                        neg_system, recent_rounds, "negative", force_note + neg_input
                    )
                    print("[engagement_check] 反方连续失败，强制重写...")
                    neg_reply = stream_reply(llm, neg_messages_forced, "反方[强制重写]")
                else:
                    print("[engagement_check] 反方未命中对方具体论点，重试一次...")
                    neg_reply = stream_reply(llm, neg_messages, "反方[重试]")
                neg_engaged = _check_engagement(neg_reply, pos_reply)

            # Stance check — semi-blocking: retry once on failure
            neg_ok, neg_warn = _check_stance(neg_reply, "negative")
            if not neg_ok:
                print(neg_warn + " — 重试一次")
                neg_reply = stream_reply(llm, neg_messages, "反方[stance重试]")
                neg_ok, neg_warn = _check_stance(neg_reply, "negative")

            neg_ref_ok, neg_ref_warn, neg_ref_hits = _check_reference_risk(neg_reply, "negative")
            if not neg_ref_ok:
                print(neg_ref_warn)
                transcript.append({"turn": turn + 1, "speaker": "reference_risk_warning", "content": neg_ref_warn})

            # v1.9 §6: soft-replace hallucinated high-precision legal citations
            neg_soften_text, neg_soften_replaced = _soft_replace_legal_material(neg_reply)
            if neg_soften_replaced:
                neg_reply = neg_soften_text
                soften_note = (
                    f"[legal_soften:反方] 已将 {len(neg_soften_replaced)} 处未验证的高精度法律引用替换为低精度表达："
                    + "；".join(neg_soften_replaced[:4])
                )
                print(soften_note)
                transcript.append({"turn": turn + 1, "speaker": "legal_soften", "content": soften_note})

            neg_frame_ok, neg_frame_warn = _check_frame_colonization(
                neg_reply, "negative", state=debate_state
            )
            if not neg_frame_ok:
                print(neg_frame_warn)
                transcript.append({"turn": turn + 1, "speaker": "frame_warning", "content": neg_frame_warn})
                frame_repair_pending["negative"] += 1
                topology_metrics["frame_warning_count"] += 1
            else:
                frame_repair_pending["negative"] = 0

            transcript.append({"turn": turn + 1, "speaker": "negative", "content": neg_reply})
            if not neg_ok:
                print(neg_warn + " — 重试后仍未通过，保留输出")
                transcript.append({"turn": turn + 1, "speaker": "stance_warning", "content": neg_warn})

            # ── Engagement streak bookkeeping ────────────────────────────────────────
            if pos_engaged and neg_engaged:
                consecutive_engagement_failures = 0
            else:
                consecutive_engagement_failures += 1

            # ── Close the round ──────────────────────────────────────────────────────
            ref_hits_round = _dedupe_preserve(pos_ref_hits + neg_ref_hits)
            structure_ok, structure_warn, structure_score = _check_structure_similarity(pos_reply, neg_reply)
            if not structure_ok:
                print(structure_warn)
                transcript.append({"turn": turn + 1, "speaker": "structure_warning", "content": structure_warn})
                topology_metrics["structure_warning_count"] += 1

            # Quality flag: only hard stance failures block state compression.
            round_dirty = (not pos_ok) or (not neg_ok)
            rounds.append({
                "positive": pos_reply,
                "negative": neg_reply,
                "dirty": round_dirty,
                "unverified_references": ref_hits_round,
                "frame_warning": (not pos_frame_ok) or (not neg_frame_ok),
                "structure_warning": not structure_ok,
                "structure_similarity": structure_score,
            })
            if round_dirty:
                print(f"[quality_gate] 本轮标记为低质量 (dirty=True)，不参与状态压缩")

            discussion_points = update_discussion_points(
                llm,
                TOPIC_FULL,
                discussion_points,
                rounds[-1],
                turn + 1,
            )

            # ── Mirror similarity check (same-turn cross-side Jaccard) ───────────────
            mirror_triggered = False
            pos_words_m = set(re.findall(r'[\u4e00-\u9fff]{2,4}', pos_reply))
            neg_words_m = set(re.findall(r'[\u4e00-\u9fff]{2,4}', neg_reply))
            mirror_sim = _jaccard(pos_words_m, neg_words_m)
            if mirror_sim >= MIRROR_SIMILARITY_THRESHOLD:
                mirror_triggered = True
                print(f"[mirror_check] 同轮相似度 {mirror_sim:.2f} ≥ {MIRROR_SIMILARITY_THRESHOLD}，触发主持人强介入")
                mirror_note = f"同轮正反方词汇 Jaccard 相似度: {mirror_sim:.2f}"
                transcript.append({"turn": turn + 1, "speaker": "mirror_warning", "content": mirror_note})
                topology_metrics["mirror_warning_count"] += 1
            if not structure_ok:
                mirror_triggered = True
                transcript.append({
                    "turn": turn + 1,
                    "speaker": "mirror_warning",
                    "content": f"同轮结构模板相似度: {structure_score:.2f}",
                })
                print(
                    f"[structure_check] 同轮结构模板相似度 {structure_score:.2f} ≥ {STRUCTURE_SIMILARITY_THRESHOLD}，触发主持人强介入"
                )
            if mirror_triggered:
                _mu = _find_untouched_premises(rounds)
                forced_assessment = {
                    "should_intervene":          True,
                    "issue_type":                "repetition",
                    "severity":                  min(1.0, max(mirror_sim, structure_score) + 0.05),
                    "recommended_mode":          "heavy",
                    "candidate_directions":      _mu[:4],
                    "untouched_premises":        _mu,
                    "reasoning_summary":         f"同轮输出同构风险过高 (lexical={mirror_sim:.2f}, structural={structure_score:.2f})",
                    "intervention_failure_score": 0.0,
                    "last_intervention_targets": [],
                    "active_requirements":       active_requirements,
                }
                forced_mod = run_moderator(llm, TOPIC_FULL, rounds[-TRIGGER_WINDOW:], debate_state, forced_assessment)
                if forced_mod:
                    forced_targets = _extract_requirement_lines(forced_mod) or _mu[:4]
                    pending_requirements = _build_requirement_records(
                        forced_targets,
                        debate_state,
                        rounds,
                        current_turn=turn + 1,
                        expires_after=2,
                    )
                    pending_moderator_msg = forced_mod
                    transcript.append({"turn": turn + 1, "speaker": "moderator", "content": forced_mod})
                    moderator_state["last_intervention_round"]   = turn
                    moderator_state["last_intervention_type"]    = "repetition"
                    moderator_state["last_intervention_targets"] = forced_targets
                    moderator_state["intervention_count"]       += 1
                    moderator_state["pending_requirements"]      = pending_requirements
                    moderator_state["must_follow_up"]            = bool(pending_requirements)
                    moderator_state["follow_up_window"]          = max(
                        [req["expires_after"] for req in pending_requirements],
                        default=0,
                    )

            # ── Compress ─────────────────────────────────────────────────────────────
            if len(rounds) > RECENT_WINDOW:
                candidate = rounds[-(RECENT_WINDOW + 1)]
                if not candidate.get("dirty", False):
                    debate_state = compress_debate_state(llm, TOPIC_FULL, debate_state, [candidate])
                else:
                    print("[quality_gate] 跳过 dirty 轮次，不更新 debate_state")

            save_log(turn + 1)

            # --- v1.9 Topology metrics: classify this round's dominant cluster -----
            round_combined = pos_reply + " " + neg_reply
            round_cluster, _ = TOPOLOGY_CONTROLLER._classify_round(round_combined)
            round_cluster = round_cluster or "未识别"
            topology_metrics["per_round_cluster"].append(round_cluster)
            if round_cluster != "未识别" and round_cluster not in topology_metrics["clusters_touched"]:
                topology_metrics["clusters_touched"].append(round_cluster)
            _clusters = topology_metrics["per_round_cluster"]
            if (len(_clusters) >= 2
                    and _clusters[-1] != _clusters[-2]
                    and _clusters[-1] != "未识别"
                    and _clusters[-2] != "未识别"):
                topology_metrics["cluster_switch_count"] += 1
            longest = current = 0
            for i, c in enumerate(_clusters):
                if c == "未识别":
                    current = 0
                    continue
                if i > 0 and c == _clusters[i - 1]:
                    current += 1
                else:
                    current = 1
                longest = max(longest, current)
            topology_metrics["longest_single_cluster_run"] = longest
            print(
                f"[topology] 本轮簇={round_cluster} "
                f"已触达={len(topology_metrics['clusters_touched'])} "
                f"最长连续={longest} "
                f"切换={topology_metrics['cluster_switch_count']}"
            )

            # --- v1.9 Completion check: did sides actually satisfy pending asks? ---
            if moderator_state.get("pending_requirements"):
                pos_comp = check_requirement_completion(pos_reply)
                neg_comp = check_requirement_completion(neg_reply)
                avg_score = round(
                    (pos_comp["completion_score"] + neg_comp["completion_score"]) / 2,
                    2,
                )
                topology_metrics["requirement_completion_scores"].append(avg_score)
                print(
                    f"[completion_check] pos={pos_comp['completion_score']} "
                    f"neg={neg_comp['completion_score']} avg={avg_score}"
                )
                if pos_comp["completion_score"] >= 0.66 and neg_comp["completion_score"] >= 0.66:
                    print("[completion_check] 双方均满足要求，清空 pending_requirements")
                    moderator_state["pending_requirements"] = []
                    moderator_state["must_follow_up"] = False
                    moderator_state["follow_up_window"] = 0
                elif pos_comp["completion_score"] == 0.0 and neg_comp["completion_score"] == 0.0:
                    print("[completion_check] 双方均未落实要求，下轮升级至硬结构模式")
                    hard_schema_pending["positive"] = True
                    hard_schema_pending["negative"] = True
                    topology_metrics["hard_topology_mode_triggered"] += 1
                else:
                    # Partial completion — collapse pending to only the missing targets so
                    # the next follow-up is shorter and more specific (not stale repetition).
                    missing = []
                    if not (pos_comp["has_concrete_scenario"]
                            and neg_comp["has_concrete_scenario"]):
                        missing.append("具体场景")
                    if not (pos_comp["has_institutional_consequence"]
                            and neg_comp["has_institutional_consequence"]):
                        missing.append("制度/社会后果")
                    if not (pos_comp["has_counterfactual_adjustment"]
                            and neg_comp["has_counterfactual_adjustment"]):
                        missing.append("前提变化下的立场调整")
                    if missing:
                        tight_text = "仅补齐缺失项：" + "、".join(missing)
                        moderator_state["pending_requirements"] = [{
                            "text":            tight_text,
                            "introduced_turn": turn + 1,
                            "expires_after":   1,
                            "topic_anchor":    "completion_followup",
                        }]
                        moderator_state["must_follow_up"] = True
                        moderator_state["follow_up_window"] = 1
                        print(f"[completion_check] 部分完成，收敛 pending 至：{missing}")

            # --- v1.9 Hard topology trigger: structural conditions force a branch switch ---
            if len(rounds) >= 2:
                _scores_ht = _compute_state_scores(rounds)
                _topology_ht = TOPOLOGY_CONTROLLER.analyze(rounds)
                hard_mode_now = (
                    _topology_ht.get("cluster_lock")
                    or _scores_ht.get("deadlock_score", 0.0) >= 0.72
                    or _scores_ht.get("branch_poverty", 0.0) >= 0.80
                )
                if hard_mode_now and not (
                    hard_schema_pending["positive"] or hard_schema_pending["negative"]
                ):
                    print(
                        f"[topology_hard_mode] 触发 "
                        f"(cluster_lock={_topology_ht.get('cluster_lock')}, "
                        f"deadlock={_scores_ht.get('deadlock_score', 0):.2f}, "
                        f"branch_poverty={_scores_ht.get('branch_poverty', 0):.2f})"
                    )
                    hard_schema_pending["positive"] = True
                    hard_schema_pending["negative"] = True
                    topology_metrics["hard_topology_mode_triggered"] += 1

            # --- Moderator: every-turn silent assessment, speak only when warranted ---
            active_requirements = _refresh_pending_requirements(
                moderator_state, debate_state, rounds, turn + 1
            )

            if len(rounds) >= 2:
                assessment = assess_round(rounds, moderator_state=moderator_state)

                # Track rolling severity trend
                moderator_state["recent_trigger_scores"].append(assessment["severity"])
                if len(moderator_state["recent_trigger_scores"]) > 4:
                    moderator_state["recent_trigger_scores"].pop(0)

                print(
                    f"[主持人旁听] severity={assessment['severity']:.2f} "
                    f"issue={assessment['issue_type']} "
                    f"mode={assessment['recommended_mode']} "
                    f"fail={assessment['intervention_failure_score']:.1f}"
                )

                if assessment["should_intervene"]:
                    # Anti-repeat: suppress same issue_type unless enough time passed,
                    # severity is critical, or this is a follow-up check (always allow)
                    last_type = moderator_state["last_intervention_type"]
                    rounds_since = turn - moderator_state["last_intervention_round"]
                    same_type = (assessment["issue_type"] is not None
                                 and assessment["issue_type"] == last_type)
                    can_speak = (
                        not same_type
                        or rounds_since >= MIN_SAME_TYPE_INTERVAL
                        or assessment["severity"] >= HIGH_SEVERITY_OVERRIDE
                        or assessment["issue_type"] == "followup_check"
                    )
                    if can_speak:
                        mod_text = run_moderator(
                            llm, TOPIC_FULL,
                            rounds[-TRIGGER_WINDOW:],
                            debate_state,
                            assessment,
                        )
                        if mod_text:
                            mod_targets = _extract_requirement_lines(mod_text) or assessment.get("candidate_directions", [])
                            expires_after = 3 if assessment.get("recommended_mode") == "heavy" else 2
                            pending_requirements = _build_requirement_records(
                                mod_targets,
                                debate_state,
                                rounds,
                                current_turn=turn + 1,
                                expires_after=expires_after,
                            )
                            print(f"[主持人]\n{mod_text}\n")
                            transcript.append({"turn": turn + 1, "speaker": "moderator", "content": mod_text})
                            pending_moderator_msg = mod_text
                            # Update moderator_state after a successful intervention
                            moderator_state["last_intervention_round"]   = turn
                            moderator_state["last_intervention_type"]    = assessment["issue_type"]
                            moderator_state["last_intervention_targets"] = mod_targets
                            moderator_state["intervention_count"]       += 1
                            moderator_state["pending_requirements"]      = pending_requirements
                            moderator_state["must_follow_up"]            = bool(pending_requirements)
                            moderator_state["follow_up_window"]          = max(
                                [req["expires_after"] for req in pending_requirements],
                                default=0,
                            )
                            save_log(turn + 1)
                    else:
                        print(f"[主持人旁听] 同类问题（{assessment['issue_type']}）已于近期介入，本轮保持静默")

    except KeyboardInterrupt:
        print("\n[Interrupted — log saved up to last completed speaker]")

    print(f"\nConversation saved to: {log_path}")


if __name__ == "__main__":
    main()
