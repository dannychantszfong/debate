import json
import os
import sys

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

SPEAKER_LABEL = {
    "positive": "Positive",
    "negative": "Negative",
}


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


def convert(json_path, md_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    topic = data.get("topic", "")
    lines.append(f"# Debate: {topic}")
    lines.append("")
    lines.append(f"- **Model:** {data.get('model', '')}")
    lines.append(f"- **Timestamp:** {data.get('timestamp', '')}")
    lines.append(f"- **Turns:** {data.get('turns', '')}")
    lines.append("")

    debate_state = data.get("debate_state")
    if debate_state:
        lines.append("## Final Debate State")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(debate_state, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    lines.append("## Transcript")
    lines.append("")

    current_turn = None
    for entry in data.get("transcript", []):
        turn = entry.get("turn")
        speaker = SPEAKER_LABEL.get(entry.get("speaker", ""), entry.get("speaker", ""))
        content = entry.get("content", "").strip()

        if turn != current_turn:
            lines.append(f"### Turn {turn}")
            lines.append("")
            current_turn = turn

        lines.append(f"#### {speaker}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    files = list_logs()
    if not files:
        print(f"No JSON logs found in {LOG_DIR}")
        return

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if not target.endswith(".json"):
            target += ".json"
        if target not in files:
            print(f"'{target}' not found in {LOG_DIR}")
            return
        selected = target
    else:
        selected = pick_log(files)

    json_path = os.path.join(LOG_DIR, selected)
    md_path = os.path.join(LOG_DIR, selected.replace(".json", ".md"))
    convert(json_path, md_path)
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
