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


def convert(json_path, txt_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    lines.append(f"Topic: {data.get('topic', '')}")
    lines.append(f"Model: {data.get('model', '')}")
    lines.append(f"Timestamp: {data.get('timestamp', '')}")
    lines.append(f"Turns: {data.get('turns', '')}")
    lines.append("=" * 60)
    lines.append("")

    for entry in data.get("transcript", []):
        speaker = SPEAKER_LABEL.get(entry.get("speaker", ""), entry.get("speaker", ""))
        turn = entry.get("turn", "")
        content = entry.get("content", "").strip()
        lines.append(f"[Turn {turn}] {speaker}:")
        lines.append(content)
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
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
    txt_path = os.path.join(LOG_DIR, selected.replace(".json", ".txt"))
    convert(json_path, txt_path)
    print(f"Wrote: {txt_path}")


if __name__ == "__main__":
    main()
