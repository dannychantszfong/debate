from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from pipeline_config import (
    REPO_ROOT,
    get_executable_command,
    get_video_config,
)

LOG_DIR = REPO_ROOT / "logs"
TOPICS_DIR = REPO_ROOT / "topics"
TRANSCRIPTS_DIR = REPO_ROOT / "transcripts"
TTS_SCRIPTS_DIR = REPO_ROOT / "tts_scripts"
AUDIO_OUTPUT_DIR = REPO_ROOT / "output" / "audio"
STOP_AFTER_TOPIC = ("topic", "log", "transcript", "tts", "audio", "video")
STOP_AFTER_LOG = ("log", "transcript", "tts", "audio", "video")
STOP_AFTER_TRANSCRIPT = ("tts", "audio", "video")
STOP_AFTER_TTS = ("audio", "video")


def _run_step(label: str, command: list[str], cwd: Path | None = None) -> None:
    workdir = cwd or REPO_ROOT
    print(f"\n[{label}]")
    print(subprocess.list2cmdline(command))
    subprocess.run(command, cwd=workdir, check=True)


def _latest_json(directory: Path) -> Path:
    files = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No JSON files found in {directory}")
    return files[-1]


def _latest_markdown(directory: Path) -> Path:
    files = sorted(directory.glob("*.md"), key=lambda item: item.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No Markdown files found in {directory}")
    return files[-1]


def _resolve_repo_json(value: str | None, directory: Path) -> Path:
    if value in (None, "", "latest"):
        return _latest_json(directory)

    raw = Path(value)
    if raw.is_absolute():
        if raw.exists():
            return raw
        raise FileNotFoundError(f"File does not exist: {raw}")

    repo_candidate = REPO_ROOT / raw
    if repo_candidate.exists():
        return repo_candidate

    if repo_candidate.suffix.lower() != ".json":
        repo_candidate = repo_candidate.with_suffix(".json")
        if repo_candidate.exists():
            return repo_candidate

    candidate = directory / raw
    if candidate.exists():
        return candidate

    if candidate.suffix.lower() != ".json":
        candidate = candidate.with_suffix(".json")
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Could not resolve {value!r} inside {directory}")


def _transcript_path_for(log_path: Path) -> Path:
    return TRANSCRIPTS_DIR / f"debate_transcript_{log_path.stem}.json"


def _tts_script_path_for(transcript_path: Path) -> Path:
    return TTS_SCRIPTS_DIR / f"tts_{transcript_path.stem}.json"


def _timeline_path_for(tts_script_path: Path) -> Path:
    return AUDIO_OUTPUT_DIR / f"{tts_script_path.stem}.json"


def _resolve_optional_user_path(value: str | None) -> str | None:
    if value in (None, ""):
        return None

    raw = Path(value)
    if raw.is_absolute():
        return str(raw)
    return str((REPO_ROOT / raw).resolve())


def _bootstrap(force_video_deps: bool) -> None:
    command = get_executable_command("main_python") + ["pipeline/bootstrap_runtime.py"]
    if force_video_deps:
        command.append("--force-video-deps")
    _run_step("Bootstrap runtime", command)


def _run_clean(log_path: Path) -> None:
    command = get_executable_command("main_python") + [
        "clean_logs.py",
        log_path.name,
        "--dir",
        str(LOG_DIR),
    ]
    _run_step("Clean log", command)


def _run_topic_generator(topic: str) -> Path:
    command = get_executable_command("main_python") + [
        "debate_topic_generator.py",
        "--topic",
        topic,
        "--out-dir",
        str(TOPICS_DIR),
    ]
    _run_step("Generate topic framework", command)
    return _latest_markdown(TOPICS_DIR)


def _run_debate(
    provider: str,
    model: str | None,
    topic_file: str | None,
    turns: int,
    reply_max_tokens: int,
) -> Path:
    command = get_executable_command("main_python") + [
        "debate.py",
        "--provider",
        provider,
        "--turns",
        str(turns),
        "--reply-max-tokens",
        str(reply_max_tokens),
    ]
    if model:
        command += ["--model", model]
    if topic_file:
        command += ["--topic-file", topic_file]
    else:
        raise ValueError("A generated topic framework is required before debate.py runs.")

    _run_step("Generate debate log", command)
    return _latest_json(LOG_DIR)


def _run_json_to_transcript(log_path: Path, provider: str, model: str | None) -> Path:
    out_path = _transcript_path_for(log_path)
    command = get_executable_command("main_python") + [
        "json_to_transcript.py",
        log_path.name,
        "--provider",
        provider,
        "--out-dir",
        str(TRANSCRIPTS_DIR),
    ]
    if model:
        command += ["--model", model]
    _run_step("Humanize transcript", command)
    return out_path


def _run_transcript_to_tts(
    transcript_path: Path,
    provider: str,
    model: str | None,
    density: str,
) -> Path:
    out_path = _tts_script_path_for(transcript_path)
    command = get_executable_command("main_python") + [
        "transcript_to_tts.py",
        transcript_path.name,
        "--provider",
        provider,
        "--density",
        density,
        "--out-dir",
        str(TTS_SCRIPTS_DIR),
    ]
    if model:
        command += ["--model", model]
    _run_step("Insert TTS tags", command)
    return out_path


def _run_tts_audio(tts_script_path: Path, skip_whisper: bool, voice_root: str | None) -> Path:
    out_path = _timeline_path_for(tts_script_path)
    command = get_executable_command("tts_python") + [
        "pipeline/tts/generate_debate_audio.py",
        "--json",
        str(tts_script_path),
        "--out-dir",
        str(AUDIO_OUTPUT_DIR),
    ]
    if skip_whisper:
        command.append("--skip-whisper")
    if voice_root:
        command += ["--voice-root", _resolve_optional_user_path(voice_root)]
    _run_step("Generate debate audio", command)
    return out_path


def _ensure_video_dependencies() -> None:
    video_config = get_video_config()
    app_dir = Path(video_config["app_dir"])
    node_modules = app_dir / "node_modules"
    if node_modules.exists():
        return
    command = get_executable_command("node_package_manager") + ["install"]
    _run_step("Install Remotion deps", command, cwd=app_dir)


def _run_video_render(
    timeline_path: Path,
    layout: str,
    plan: str | None,
    audio: str | None,
    out: str | None,
    max_seconds: str | None,
    concurrency: str | None,
    gl: str | None,
    port: str | None,
    keep_bundle: bool,
    keep_staged_audio: bool,
) -> None:
    video_config = get_video_config()
    app_dir = Path(video_config["app_dir"])
    _ensure_video_dependencies()

    command = get_executable_command("node") + [
        "render-user-debate.cjs",
        "--json",
        str(timeline_path),
        "--layout",
        layout,
    ]
    if plan:
        command += ["--plan", _resolve_optional_user_path(plan)]
    if audio:
        command += ["--audio", _resolve_optional_user_path(audio)]
    if out:
        command += ["--out", _resolve_optional_user_path(out)]
    if max_seconds:
        command += ["--max-seconds", max_seconds]
    if concurrency:
        command += ["--concurrency", concurrency]
    if gl:
        command += ["--gl", gl]
    if port:
        command += ["--port", port]
    if keep_bundle:
        command.append("--keep-bundle")
    if keep_staged_audio:
        command.append("--keep-staged-audio")

    _run_step("Render video", command, cwd=app_dir)


def _add_shared_render_args(parser: argparse.ArgumentParser, default_layout: str) -> None:
    parser.add_argument("--layout", default=default_layout)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--audio", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-seconds", default=None)
    parser.add_argument("--concurrency", default=None)
    parser.add_argument("--gl", default=None)
    parser.add_argument("--port", default=None)
    parser.add_argument("--keep-bundle", action="store_true")
    parser.add_argument("--keep-staged-audio", action="store_true")


def parse_args():
    video_config = get_video_config()
    default_layout = video_config["default_layout"]

    parser = argparse.ArgumentParser(description="Run the debate production pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Prepare local models and Remotion deps.")
    bootstrap.add_argument("--force-video-deps", action="store_true")

    from_log = subparsers.add_parser("from-log", help="Go from debate log to final video.")
    from_log.add_argument("--log", default="latest")
    from_log.add_argument("--provider", default="local")
    from_log.add_argument("--model", default=None)
    from_log.add_argument("--density", default="medium")
    from_log.add_argument("--stop-after", choices=STOP_AFTER_LOG, default="video")
    from_log.add_argument("--skip-clean", action="store_true")
    from_log.add_argument("--skip-whisper", action="store_true")
    from_log.add_argument("--voice-root", default=None)
    _add_shared_render_args(from_log, default_layout)

    from_topic = subparsers.add_parser("from-topic", help="Go from raw topic/topic framework to final video.")
    topic_source = from_topic.add_mutually_exclusive_group(required=True)
    topic_source.add_argument(
        "--topic",
        default=None,
        help="Raw debate topic text. The pipeline first turns it into a topic framework markdown file.",
    )
    topic_source.add_argument(
        "--topic-file",
        default=None,
        help="Existing topic framework markdown file generated by debate_topic_generator.py.",
    )
    from_topic.add_argument("--turns", type=int, default=10)
    from_topic.add_argument("--reply-max-tokens", type=int, default=10240)
    from_topic.add_argument("--provider", default="local")
    from_topic.add_argument("--model", default=None)
    from_topic.add_argument("--density", default="medium")
    from_topic.add_argument("--stop-after", choices=STOP_AFTER_TOPIC, default="video")
    from_topic.add_argument("--skip-clean", action="store_true")
    from_topic.add_argument("--skip-whisper", action="store_true")
    from_topic.add_argument("--voice-root", default=None)
    _add_shared_render_args(from_topic, default_layout)

    from_transcript = subparsers.add_parser(
        "from-transcript",
        help="Go from transcript JSON to final video.",
    )
    from_transcript.add_argument("--transcript", default="latest")
    from_transcript.add_argument("--provider", default="local")
    from_transcript.add_argument("--model", default=None)
    from_transcript.add_argument("--density", default="medium")
    from_transcript.add_argument("--stop-after", choices=STOP_AFTER_TRANSCRIPT, default="video")
    from_transcript.add_argument("--skip-whisper", action="store_true")
    from_transcript.add_argument("--voice-root", default=None)
    _add_shared_render_args(from_transcript, default_layout)

    from_tts = subparsers.add_parser("from-tts", help="Go from TTS script JSON to final video.")
    from_tts.add_argument("--tts-script", default="latest")
    from_tts.add_argument("--stop-after", choices=STOP_AFTER_TTS, default="video")
    from_tts.add_argument("--skip-whisper", action="store_true")
    from_tts.add_argument("--voice-root", default=None)
    _add_shared_render_args(from_tts, default_layout)

    video = subparsers.add_parser("video", help="Render video only from a timing JSON.")
    video.add_argument("--timeline", default="latest")
    _add_shared_render_args(video, default_layout)

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "bootstrap":
        _bootstrap(force_video_deps=args.force_video_deps)
        return

    if args.command == "from-log":
        log_path = _resolve_repo_json(args.log, LOG_DIR)
        if not args.skip_clean:
            _run_clean(log_path)
        if args.stop_after == "log":
            print(f"\n[pipeline] Final log JSON: {log_path}")
            return
        transcript_path = _run_json_to_transcript(log_path, args.provider, args.model)
        if args.stop_after == "transcript":
            print(f"\n[pipeline] Final transcript JSON: {transcript_path}")
            return
        tts_script_path = _run_transcript_to_tts(
            transcript_path,
            args.provider,
            args.model,
            args.density,
        )
        if args.stop_after == "tts":
            print(f"\n[pipeline] Final TTS script JSON: {tts_script_path}")
            return
        timeline_path = _run_tts_audio(
            tts_script_path,
            skip_whisper=args.skip_whisper,
            voice_root=args.voice_root,
        )
        if args.stop_after == "audio":
            print(f"\n[pipeline] Final timing JSON: {timeline_path}")
            return
    elif args.command == "from-topic":
        topic_file = args.topic_file
        if args.topic:
            topic_file = str(_run_topic_generator(args.topic))
            if args.stop_after == "topic":
                print(f"\n[pipeline] Final topic framework: {topic_file}")
                return
        elif args.stop_after == "topic":
            print(f"\n[pipeline] Selected topic framework: {topic_file}")
            return
        log_path = _run_debate(
            provider=args.provider,
            model=args.model,
            topic_file=topic_file,
            turns=args.turns,
            reply_max_tokens=args.reply_max_tokens,
        )
        if not args.skip_clean:
            _run_clean(log_path)
        if args.stop_after == "log":
            print(f"\n[pipeline] Final log JSON: {log_path}")
            return
        transcript_path = _run_json_to_transcript(log_path, args.provider, args.model)
        if args.stop_after == "transcript":
            print(f"\n[pipeline] Final transcript JSON: {transcript_path}")
            return
        tts_script_path = _run_transcript_to_tts(
            transcript_path,
            args.provider,
            args.model,
            args.density,
        )
        if args.stop_after == "tts":
            print(f"\n[pipeline] Final TTS script JSON: {tts_script_path}")
            return
        timeline_path = _run_tts_audio(
            tts_script_path,
            skip_whisper=args.skip_whisper,
            voice_root=args.voice_root,
        )
        if args.stop_after == "audio":
            print(f"\n[pipeline] Final timing JSON: {timeline_path}")
            return
    elif args.command == "from-transcript":
        transcript_path = _resolve_repo_json(args.transcript, TRANSCRIPTS_DIR)
        tts_script_path = _run_transcript_to_tts(
            transcript_path,
            args.provider,
            args.model,
            args.density,
        )
        if args.stop_after == "tts":
            print(f"\n[pipeline] Final TTS script JSON: {tts_script_path}")
            return
        timeline_path = _run_tts_audio(
            tts_script_path,
            skip_whisper=args.skip_whisper,
            voice_root=args.voice_root,
        )
        if args.stop_after == "audio":
            print(f"\n[pipeline] Final timing JSON: {timeline_path}")
            return
    elif args.command == "from-tts":
        tts_script_path = _resolve_repo_json(args.tts_script, TTS_SCRIPTS_DIR)
        timeline_path = _run_tts_audio(
            tts_script_path,
            skip_whisper=args.skip_whisper,
            voice_root=args.voice_root,
        )
        if args.stop_after == "audio":
            print(f"\n[pipeline] Final timing JSON: {timeline_path}")
            return
    else:
        timeline_path = _resolve_repo_json(args.timeline, AUDIO_OUTPUT_DIR)

    _run_video_render(
        timeline_path=timeline_path,
        layout=args.layout,
        plan=args.plan,
        audio=args.audio,
        out=args.out,
        max_seconds=args.max_seconds,
        concurrency=args.concurrency,
        gl=args.gl,
        port=args.port,
        keep_bundle=args.keep_bundle,
        keep_staged_audio=args.keep_staged_audio,
    )

    print(f"\n[pipeline] Final timing JSON: {timeline_path}")


if __name__ == "__main__":
    main()
