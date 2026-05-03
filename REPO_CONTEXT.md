# REPO_CONTEXT.md — LLM Debate Simulator

> Target reader: another LLM collaborating on this codebase.
> Goal: build an accurate mental model without reading every line.

---

## 1. Global Picture

This repo is a **single-file LLM debate simulation engine** centered on `debate.py` (~1750 lines).
It orchestrates two LLM "debaters" (positive side / negative side) through multiple turns on a fixed
topic, with three autonomous subsystems running in parallel:

```
User invokes main()
    │
    ├─ build_client()          → picks provider (local/openai/anthropic/gemini/openrouter/grok)
    ├─ summarize_topic_for_title()  → generates a short filename slug
    │
    └─ for turn in range(MAX_TURNS):
           ├─ build_system_prompt()    → assembles debater rules + turn-aware strategy hint
           ├─ build_history()          → constructs per-side message list
           ├─ stream_reply()           → calls LLM, streams to stdout
           ├─ _check_engagement()      → Jaccard-based check: did reply cite opponent?
           ├─ _check_stance()          → regex check: did debater surrender its position?
           ├─ compress_debate_state()  → rolling LLM-based summarizer (JSON state object)
           ├─ assess_round()           → pure-heuristic moderator trigger (no LLM call)
           ├─ run_moderator()          → conditional LLM call: formats intervention
           └─ save_log()              → writes JSON to logs/
```

Supporting scripts:
- `debate_topic_generator.py` — standalone tool to pre-generate a debate analysis framework for a topic
- `clean_logs.py` — post-processing: strips LaTeX math artifacts from JSON logs
- `json_to_md.py` / `json_to_txt.py` — converts JSON logs to readable formats

---

## 2. Directory Layout

```
conversation/
├── debate.py                  ← MAIN ENGINE — all debate logic lives here
├── debate_topic_generator.py  ← standalone topic analysis tool (local Llama only)
├── clean_logs.py              ← log post-processor (LaTeX cleanup)
├── json_to_md.py              ← log → Markdown converter
├── json_to_txt.py             ← log → plain text converter
├── debate_topic.txt           ← prompt template reference (not imported by code)
├── comment.txt                ← developer notes (not imported)
├── path.txt                   ← path reference file (not imported)
├── logs/                      ← JSON debate logs, .md/.txt conversions
│   └── debate_v{VER}_{slug}_{ts}.json
└── topics/                    ← framework analyses from debate_topic_generator.py
    └── topic_{slug}_{ts}.md
```

---

## 3. Core Data Structures

### `rounds` (list of dicts, in-memory only)
```python
[{"positive": "<full reply text>", "negative": "<full reply text>"}, ...]
```
Canonical source of truth for heuristic scoring and summarization. Never truncated — grows
to `MAX_TURNS` entries. The last `RECENT_WINDOW` (=2) entries are replayed verbatim in each
LLM message; older ones are summarized into `debate_state`.

### `debate_state` (dict, persisted in log)
LLM-generated rolling summary. Schema enforced by `SUMMARIZER_SYSTEM` prompt:
```json
{
  "current_focus": "...",
  "positive_strongest_claims": [...],
  "negative_strongest_claims": [...],
  "unresolved_questions": [...],
  "concessions_or_shifts": "...",
  "deprecated_or_answered_points": [...],
  "key_definitions": {...},
  "next_targets": {"positive": "...", "negative": "..."}
}
```
**Risk**: This schema is enforced only by prompt instruction, not by code validation.
If the LLM outputs an unexpected shape, `filter_state_for_side()` silently returns a partial
dict with missing keys — callers receive `None` for missing entries without any error.

### `transcript` (list of dicts, persisted in log)
Flat ordered event log including debater turns, moderator speeches, stance warnings, mirror
warnings:
```python
{"turn": int, "speaker": "positive"|"negative"|"moderator"|"stance_warning"|"mirror_warning", "content": str}
```

### `moderator_state` (dict, persisted in log)
Tracks intervention history to prevent same-type repeat-suppression and follow-up enforcement:
```python
{
  "last_intervention_round": int,
  "last_intervention_type": str | None,
  "last_intervention_targets": [str],
  "intervention_count": int,
  "recent_trigger_scores": [float],
  "must_follow_up": bool,
  "follow_up_window": int,   # decremented each turn
}
```

---

## 4. Key Modules (all in `debate.py`)

### 4.1 Provider Layer — `build_client()`, `*Client` classes (lines ~1240–1433)

**Responsibility**: Uniform `create_chat_completion()` interface over 6 providers.

**Classes**:
- `LocalLLMClient` — wraps `llama_cpp.Llama`
- `OpenAICompatibleClient` — wraps `openai.OpenAI`; used for openai, openrouter, grok
- `AnthropicClient` — wraps `anthropic.Anthropic`; extracts system messages manually (Anthropic API requires `system` as a separate kwarg)
- `GeminiClient` — wraps `google.generativeai`; splits history/last message manually; maps `assistant` → `model` role

**Who calls it**: `main()` once; result is passed to all subsystems.

**Risks when modifying**:
- `_merge_consecutive()` exists specifically because Gemini rejects consecutive same-role messages. Removing it breaks Gemini silently (API returns error only at runtime).
- `AnthropicClient` manually separates `system` from `messages`. If a caller injects a second system message into the list (possible through future refactoring), only the first gets used.
- `repeat_penalty` is silently ignored by all API clients (only `LocalLLMClient` actually uses it).

### 4.2 Debate State Compression — `compress_debate_state()` (lines ~540–605)

**Responsibility**: After each turn (when `len(rounds) > RECENT_WINDOW`), the oldest round
outside the verbatim window is compressed into `debate_state` JSON. Prevents context length
explosion for long debates.

**Depends on**: `SUMMARIZER_SYSTEM` prompt, `_extract_json_block()`, the LLM client.

**Retry logic**: Up to 5 retries; on failure, feeds parse error + previous raw output back to
LLM via continued conversation. Falls back to `prev_state` if all retries fail.

**Risks**:
- The retry-conversation approach appends `{"role": "assistant", "content": raw}` followed
  by a correction request. This works for most providers but can accumulate a very long
  message list on repeated failures. No maximum growth limit is enforced.
- `SUMMARIZER_SYSTEM` prompt hard-codes the expected JSON keys. If the LLM omits a key,
  `filter_state_for_side()` will return a partial dict with gaps — no validation or fill.

### 4.3 Per-Side State Injection — `filter_state_for_side()`, `_make_state_context()` (lines ~654–744)

**Responsibility**: Transforms the neutral `debate_state` dict into an asymmetric "combat
brief" for each side. Positive side sees negative's claims as "attack targets"; negative sees
positive's as "attack targets". Prevents both sides from receiving identical framing.

**Called by**: `main()` for each side each turn, result embedded into `pending_input` (not
system prompt — deliberate, see comment at `build_history()` line ~704).

**Risk**: The key names in the brief are hardcoded Chinese strings (e.g., `"你的有效论点（持续深化，不要重复）"`). If `debate_state` structure changes, the mapping silently produces an empty brief.

### 4.4 Automated Moderator — `assess_round()` + `run_moderator()` (lines ~858–1219)

**Responsibility**: Every turn, `assess_round()` computes 6 heuristic scores from recent
rounds (no LLM call). If `severity >= SEVERITY_THRESHOLD` (0.38) and conditions pass, it
calls `run_moderator()` which invokes the LLM using `MODERATOR_SYSTEM`.

**Heuristic scores** (all 0–1, computed in `_compute_state_scores()`):
- `abstract_drift`: abstract marker density minus half the concrete marker density
- `repetition_score`: full-vocabulary Jaccard overlap between consecutive rounds
- `deadlock_score`: top-concept Jaccard (high = discussion narrowing onto one point)
- `realism_score`: density of institutional/behavioural anchors
- `branch_poverty`: fraction of `PREMISE_SLOTS` untouched relative to expected
- `premise_absence`: fraction of `PREMISE_SLOTS` never mentioned across all rounds

**Hard triggers** (bypass severity threshold, line ~1021):
- `follow_up_check_failed`: moderator's prior intervention was ignored
- `concrete_hits == 0`: no real-world anchors in assessment window
- `deadlock_score >= 0.75`
- `repetition_score >= 0.65`

**Mirror check** (after round close, line ~1666): if same-turn Jaccard of pos+neg ≥ 0.55,
forces a heavy moderator intervention immediately.

**Anti-repeat suppression**: same `issue_type` is suppressed within `MIN_SAME_TYPE_INTERVAL`
(=2) turns, unless `severity >= HIGH_SEVERITY_OVERRIDE` (0.70) or it's a follow-up check.

**Risk**: `PREMISE_SLOTS`, `_ABSTRACT_MARKERS`, `_CONCRETE_MARKERS` are hardcoded to a
specific abortion-rights topic (lines ~416–447). These are **not topic-generic**. Changing
the debate topic without updating these lists will produce misleading heuristic scores.

### 4.5 Engagement & Stance Guards — `_check_engagement()`, `_check_stance()` (lines ~820–817)

**Responsibility**:
- `_check_engagement()`: extracts top-10 CJK bigrams/quadrigrams from opponent's last turn,
  checks if ≥1 appear in the first 300 chars of the current reply. Returns bool.
- `_check_stance()`: pattern-matches against hardcoded phrase lists in the tail 400 chars.
  Returns `(ok: bool, warning: str)`. No LLM call.

**Retry logic**: engagement failure → retry once; `consecutive_engagement_failures >= 2` → force-rewrite prompt. Stance failure → retry once; if still fails, saves warning to transcript but keeps reply.

**Risk**: Phrase lists (`_GENERIC_CAPITULATION`, `_POS_ADOPTS_NEG`, `_NEG_ADOPTS_POS`, `_CONTRADICTION_MARKERS`) are hardcoded for the current topic. False negatives (debater surrenders in topic-specific language not in the list) are common.

### 4.6 Prompts — `BASE_PROMPT`, `build_system_prompt()`, `SUMMARIZER_SYSTEM`, `MODERATOR_SYSTEM`, `TITLE_SUMMARIZER_SYSTEM` (lines ~162–618)

**Responsibility**: All prompt logic is inline in `debate.py`.

- `BASE_PROMPT` contains 28 numbered rules for debater behavior (~170 lines). Turn-awareness
  is added by `build_system_prompt()` which appends a round-progress block.
- `SUMMARIZER_SYSTEM` instructs the LLM to output a specific JSON schema.
- `MODERATOR_SYSTEM` instructs a moderation LLM with a fixed 6-field output format.
- `TITLE_SUMMARIZER_SYSTEM` generates short filename slugs.

**Risk**: `TOPIC` is hardcoded as a multiline string constant at the top of `debate.py`
(lines ~9–118). It is **not** read from a file or CLI argument. To change the debate topic,
you must edit the source directly. The hardcoded `TOPIC` already includes a full debate
analysis framework (generated by `debate_topic_generator.py`) embedded directly in the prompt.

---

## 5. Main Call Chain

```
main()
 ├─ build_client(provider)
 ├─ summarize_topic_for_title(llm, TOPIC)          # LLM call, non-streaming
 └─ for turn in [0..MAX_TURNS-1]:
      ├─ build_system_prompt(TOPIC, turn, MAX_TURNS)
      │    └─ returns BASE_PROMPT + round_info block
      │
      ├─ [positive side]
      │   ├─ _make_state_context(debate_state, "positive")
      │   ├─ build_history(pos_system, recent_rounds[-RECENT_WINDOW:], "positive", pos_input)
      │   ├─ stream_reply(llm, pos_messages, "正方")   # streaming LLM call
      │   ├─ _check_engagement(pos_reply, rounds[-1]["negative"])
      │   │    └─ [on fail] stream_reply retry or force-rewrite
      │   └─ _check_stance(pos_reply, "positive")
      │        └─ [on fail] stream_reply retry
      │
      ├─ [negative side] — symmetric to positive
      │
      ├─ rounds.append({positive, negative})
      ├─ [mirror check] _jaccard(pos_words, neg_words) → maybe run_moderator()
      │
      ├─ [compression] if len(rounds) > RECENT_WINDOW:
      │    compress_debate_state(llm, TOPIC, debate_state, [rounds[-(RECENT_WINDOW+1)]])
      │         └─ non-streaming LLM call, up to 5 retries
      │
      ├─ save_log(turn+1)
      │
      └─ [moderator pipeline]
           ├─ assess_round(rounds, moderator_state)   # pure heuristics, no LLM
           └─ if should_intervene:
                run_moderator(llm, TOPIC, rounds[-TRIGGER_WINDOW:], debate_state, assessment)
                     └─ non-streaming LLM call
```

---

## 6. Configuration

All configuration is hardcoded in `debate.py` module-level constants — there is no config file:

| Constant | Value | Meaning |
|---|---|---|
| `TOPIC` | multiline string | The debate topic + embedded analysis framework |
| `MAX_TURNS` | 10 | Total debate rounds |
| `RECENT_WINDOW` | 2 | Rounds kept verbatim in context |
| `TRIGGER_WINDOW` | 4 | Rounds inspected by moderator heuristics |
| `SEVERITY_THRESHOLD` | 0.38 | Min severity to trigger moderator LLM call |
| `HIGH_SEVERITY_OVERRIDE` | 0.70 | Severity that bypasses anti-repeat suppression |
| `MIN_SAME_TYPE_INTERVAL` | 2 | Turns before same issue_type can trigger again |
| `MIRROR_SIMILARITY_THRESHOLD` | 0.55 | Same-turn Jaccard that forces heavy intervention |
| `VERSION` | `"1.5"` | Embedded in log filenames |
| `MODEL_PATH` | hardcoded Windows path | Local GGUF model path |

**API keys** are read from environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY`. Never hardcoded.

**Provider selection** is via CLI: `--provider {local,openai,anthropic,gemini,openrouter,grok}`.
Model override: `--model <name>`.

---

## 7. Log File Schema

`logs/debate_v{VERSION}_{title_slug}_{timestamp}.json`:
```json
{
  "version": "1.5",
  "topic": "<full TOPIC string>",
  "model": "anthropic/claude-opus-4-6",
  "timestamp": "20260416_210943",
  "turns": 10,
  "debate_state": { ... },
  "moderator_state": { ... },
  "transcript": [
    {"turn": 1, "speaker": "positive", "content": "..."},
    {"turn": 1, "speaker": "negative", "content": "..."},
    ...
  ]
}
```
The `transcript` is the flat event log; `debate_state` is the rolling compression snapshot
from the last completed turn.

---

## 8. High-Risk Areas

### 8.1 `TOPIC` constant is the entire debate topic + framework (lines 9–118)
Changing the topic requires editing source code. The embedded analysis framework inside `TOPIC`
was generated by `debate_topic_generator.py` and pasted in manually. This is not documented —
a collaborator might think `TOPIC` is just a short title string.

### 8.2 `PREMISE_SLOTS`, `_ABSTRACT_MARKERS`, `_CONCRETE_MARKERS` are topic-specific (lines ~416–447)
These lists are tuned for the abortion-rights debate topic. Running any other topic through the
same engine will produce systematically wrong heuristic scores because these lists won't match.
The scoring functions `_compute_state_scores()` and `assess_round()` don't validate this.

### 8.3 `compress_debate_state()` retry loop appends to message history without bound (lines ~562–603)
Each retry appends two new messages. With `max_retries=5`, the message list can grow to 12+
messages in the retry conversation. For models with tight context limits this can cause silent
truncation on the server side.

### 8.4 `debate_state` schema is unvalidated after JSON parse (lines ~571–581)
After `json.loads(candidate)`, the parsed dict is returned as-is. Downstream callers
(`filter_state_for_side()`, `_make_state_context()`) use `.get()` with fallbacks, so missing
keys don't raise errors — but the debate proceeds with incomplete state context, silently
degrading quality.

### 8.5 `GeminiClient.create_chat_completion()` recreates `GenerativeModel` on every call (lines ~1367–1397)
A new model instance is instantiated per call including during high-frequency turns. This is
inefficient and may cause rate-limiting edge cases; however, the `google-generativeai` SDK
doesn't expose a session-level object that cleanly separates configuration from inference.

---

## 9. Historical Compatibility / Technical Debt

### 9.1 `debate_topic.txt` is a dead reference file
`debate_topic.txt` contains a prompt template that matches the structure of `debate_topic_generator.py`'s `SYSTEM_PROMPT`. It is not imported anywhere in the codebase. It appears to be a reference document from an earlier version when the template was external.

### 9.2 `debate_topic_generator.py` uses only `LocalLLMClient` (hardcoded `llama_cpp`)
Unlike `debate.py`, which has a full provider abstraction, `debate_topic_generator.py` is
hardcoded to `llama_cpp`. It has no `--provider` flag. If migrating to API-only environments,
this script will fail at import time.

### 9.3 Version prefix in log filenames only changed manually
`VERSION = "1.5"` is a module constant. There's no version bump script. Log files from
versions 1.3 and 1.5 coexist in `logs/` — the converter scripts (`json_to_md.py`,
`json_to_txt.py`) read log fields but don't validate `version`.

### 9.4 `comment.txt` and `path.txt`
Neither is imported. `comment.txt` appears to contain developer notes. `path.txt` contains a
file path string. Both are stale artifacts with no functional role.

### 9.5 The `TOPIC` constant contains a pre-generated analysis framework (v1.5 onward)
Earlier log files (e.g., `debate_v1.3_*`) were run with a shorter topic string. The v1.5
`TOPIC` includes a 100+ line framework embedded inside the system prompt, significantly
expanding the context used per-turn. This is an intentional quality improvement but makes the
prompt ~3× longer for debaters than in v1.3.

---

## 10. Do Not Lightly Refactor

### 10.1 `build_history()` intentionally puts state context in `pending_input`, not system (lines ~704–729)
The comment at line ~704 explains why: injecting state as a `[system]` message creates a
priority fight with the debater's rules also in `[system]`. The current design puts state
inside `pending_input` as a `[user]` message labeled as secondary reference. Changing this
placement breaks the intended attention ordering.

### 10.2 `_merge_consecutive()` is required for Gemini, must stay in message pipeline (lines ~1226–1237)
`GeminiClient.create_chat_completion()` calls `_merge_consecutive()` on the conversation
before converting to Gemini's format. If you restructure the message building to produce
fewer consecutive same-role messages, this is fine — but if you remove `_merge_consecutive()`,
all Gemini calls will fail with an API error.

### 10.3 Engagement check compares against `rounds[-1]["negative"]` vs `pos_reply` asymmetrically
Positive side checks against the previous round's negative reply (before this turn starts).
Negative side checks against `pos_reply` from the current turn (just produced). This asymmetry
is intentional: negative always responds to the freshest positive statement. Treating them
symmetrically would create a stale-reference bug for the negative side.

### 10.4 `save_log()` is called **twice per turn** — after positive speaks and after negative speaks
This ensures partial progress is persisted if the run crashes mid-turn. The first save has
`transcript` with only positive's entry; the second has both. Any refactor that moves `save_log()`
to once-per-turn risks losing the positive-side transcript entry on crash.

---

## 11. Files to Read First (Priority Order)

1. **`debate.py` lines 1–160** — `TOPIC`, `MAX_TURNS`, `PROVIDER_CONFIGS`, `BASE_PROMPT`.
   Establishes all fixed parameters and debater behavior rules.

2. **`debate.py` lines 338–410** — `build_system_prompt()`, `SUMMARIZER_SYSTEM`, `MODERATOR_SYSTEM`.
   The three LLM personas (debater, summarizer, moderator) and how they differ.

3. **`debate.py` lines 1455–1760** — `main()` loop. The actual turn-by-turn orchestration.

4. **`debate.py` lines 858–940** — `_compute_state_scores()`, moderator heuristics.
   Where the automated quality assessment lives — the most algorithmically complex section.

5. **`debate.py` lines 1240–1434** — `*Client` classes, `build_client()`.
   Provider abstraction layer — needed for adding new providers or debugging API errors.

6. **`debate_topic_generator.py`** — standalone topic analysis tool; entirely independent of
   the main engine. Short file, read in full.

7. **`clean_logs.py`** — post-processing utility. The `RULES` list (lines ~105–177) and
   `_clean_inline_math()` (lines ~21–97) are the working core.

---

## 12. Uncertain / Needs Further Verification

- **[推测]** The `debate_topic.txt` file may have been the original template for
  `debate_topic_generator.py`'s system prompt before it was inlined. The content matches
  structurally. Whether it was ever imported by a prior version is not confirmed by git
  history inspection.

- **[推测]** `comment.txt` and `path.txt` appear to be scratch files from development,
  not documentation. Recommend confirming before deleting.

- **[未确认]** Whether `PREMISE_SLOTS` was ever updated between v1.3 and v1.5, or whether
  it was created only for the current topic. Recommend reading git log for these constants.

- **[未确认]** The `follow_up_window` countdown (`moderator_state["follow_up_window"] -= 1`
  at line ~1709) is decremented even on turns where the moderator didn't speak. This means
  the window can expire before the debaters have had a meaningful chance to respond. Whether
  this is intentional design or a timing bug requires intent confirmation from the author.

- **Suggested read**: `logs/debate_v1.5_胎儿生命权与女性自主权优先性之争_20260416_203032.json` —
  examine `moderator_state.intervention_count` and the `transcript` speaker sequence to
  understand how frequently the moderator actually fires in a complete run.
