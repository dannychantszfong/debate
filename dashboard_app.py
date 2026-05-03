from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from pipeline_config import REPO_ROOT, get_executable_command, get_video_config


TOPICS_DIR = REPO_ROOT / "topics"
LOG_DIR = REPO_ROOT / "logs"
TRANSCRIPTS_DIR = REPO_ROOT / "transcripts"
TTS_SCRIPTS_DIR = REPO_ROOT / "tts_scripts"
AUDIO_DIR = REPO_ROOT / "output" / "audio"
VIDEO_DIR = REPO_ROOT / "output" / "video"
RUN_RECORDS_DIR = REPO_ROOT / "run_records"
VOICE_ROOT_DIR = REPO_ROOT / "assets" / "voices"
VOICE_PREVIEW_DIR = AUDIO_DIR / "voice_previews"

PROVIDERS = ["local", "openrouter", "openai", "anthropic", "gemini", "grok"]
LAYOUTS = ["dual", "podcast", "mindmap"]
STOP_AFTER_BY_MODE = {
    "from-topic": ["topic", "log", "transcript", "tts", "audio", "video"],
    "from-log": ["log", "transcript", "tts", "audio", "video"],
    "from-transcript": ["tts", "audio", "video"],
    "from-tts": ["audio", "video"],
    "video": ["video"],
    "tts-preview": ["audio"],
}
STAGE_BASE_PROGRESS = {
    "Generate topic framework": 5,
    "Generate debate log": 14,
    "Clean log": 24,
    "Humanize transcript": 34,
    "Insert TTS tags": 46,
    "Generate debate audio": 58,
    "Render video": 78,
}
FINAL_PROGRESS = 100
MAX_MEMORY_LINES = 2500


def _now_label() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")


def _safe_repo_path(rel_path: str) -> Path:
    raw = (REPO_ROOT / rel_path).resolve()
    root = REPO_ROOT.resolve()
    if raw != root and root not in raw.parents:
        raise HTTPException(status_code=400, detail="Path is outside the repo")
    if not raw.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return raw


def _resolve_optional_user_path(value: str | None) -> str | None:
    if value in (None, ""):
        return None

    raw = Path(value)
    if raw.is_absolute():
        return str(raw)
    return str((REPO_ROOT / raw).resolve())


def _list_files(directory: Path, patterns: tuple[str, ...], limit: int = 80) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(directory.glob(pattern))
    files = sorted(set(files), key=lambda item: item.stat().st_mtime, reverse=True)
    out = []
    for item in files[:limit]:
        stat = item.stat()
        out.append({
            "name": item.name,
            "path": _rel(item),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mtime_label": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return out


def _artifact_payload(path: Path) -> dict[str, Any]:
    stat = path.stat()
    rel_path = _rel(path)
    return {
        "name": path.name,
        "path": rel_path,
        "url": f"/files/{rel_path}",
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mtime_label": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _list_voice_packs() -> list[dict[str, Any]]:
    if not VOICE_ROOT_DIR.exists():
        return []
    packs = []
    for pack_dir in sorted(path for path in VOICE_ROOT_DIR.iterdir() if path.is_dir()):
        speakers = {}
        usable = False
        for speaker in ("host", "positive", "negative"):
            voice_dir = pack_dir / speaker
            samples = []
            if voice_dir.exists():
                for audio in sorted(voice_dir.iterdir()):
                    if audio.suffix.lower() not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
                        continue
                    if not audio.with_suffix(".txt").exists():
                        continue
                    samples.append({
                        "name": audio.stem,
                        "path": _rel(audio),
                        "voice_dir": _rel(voice_dir),
                    })
                usable = usable or bool(samples)
            speakers[speaker] = {
                "voice_dir": _rel(voice_dir),
                "samples": samples,
            }
        if usable:
            packs.append({
                "name": pack_dir.name,
                "path": _rel(pack_dir),
                "speakers": speakers,
            })
    return packs


def _command_display(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


class StartJobRequest(BaseModel):
    mode: str
    stop_after: str = "video"
    topic_source: str = "raw"
    topic: str | None = None
    topic_file: str | None = None
    log: str | None = "latest"
    transcript: str | None = "latest"
    tts_script: str | None = "latest"
    timeline: str | None = "latest"
    provider: str = "local"
    model: str | None = None
    turns: int = 3
    reply_max_tokens: int = 10240
    density: str = "medium"
    skip_clean: bool = False
    skip_whisper: bool = False
    voice_root: str | None = None
    preview_voice_dir: str | None = None
    preview_voice_text: str | None = None
    preview_voice_sample: str | None = None
    layout: str = "dual"
    plan: str | None = None
    audio: str | None = None
    out: str | None = None
    max_seconds: str | None = None
    concurrency: str | None = "75%"
    gl: str | None = "angle"
    port: str | None = "8099"
    keep_bundle: bool = False
    keep_staged_audio: bool = False


@dataclass
class Job:
    id: str
    mode: str
    stop_after: str
    command: list[str]
    command_display: str
    log_path: Path
    started_at: float
    status: str = "queued"
    stage: str = "Queued"
    progress: int = 0
    returncode: int | None = None
    ended_at: float | None = None
    process: subprocess.Popen | None = None
    lines: deque[str] = field(default_factory=lambda: deque(maxlen=MAX_MEMORY_LINES))
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append_line(self, line: str) -> None:
        clean = line.rstrip("\r\n")
        with self.lock:
            self.lines.append(clean)
            self._update_from_line(clean)

    def _set_stage(self, stage: str, progress: int) -> None:
        self.stage = stage
        self.progress = max(self.progress, min(progress, 99))

    def _add_artifact_from_text(self, text: str) -> None:
        match = re.search(r"([A-Za-z]:\\[^\"<>|]+|/[^\"<>|]+)", text)
        if not match:
            return
        path = Path(match.group(1).strip())
        if path.exists() and path.is_file():
            try:
                self.artifacts[_rel(path)] = _artifact_payload(path)
            except ValueError:
                pass

    def _update_from_line(self, line: str) -> None:
        stage_match = re.match(r"^\[(Generate topic framework|Generate debate log|Clean log|Humanize transcript|Insert TTS tags|Generate debate audio|Render video)\]", line)
        if stage_match:
            stage = stage_match.group(1)
            self._set_stage(stage, STAGE_BASE_PROGRESS.get(stage, self.progress))
            return

        gen_match = re.match(r"^\[gen \]\s+turn\s+(\d+)(?:/(\d+))?", line)
        if gen_match:
            current = int(gen_match.group(1))
            total = int(gen_match.group(2) or 0)
            self.stage = line.strip("[] ")
            if total:
                self.progress = max(self.progress, min(77, 58 + int((current / total) * 18)))
            else:
                self.progress = max(self.progress, 60)
            return

        if line.startswith("[ok ]"):
            self.stage = line.strip("[] ")
            self.progress = max(self.progress, 62)
            return

        if line.startswith("[qa"):
            self.stage = line.strip()
            self.progress = max(self.progress, 72)
            return

        if line.startswith("[done]"):
            self._add_artifact_from_text(line)
            if self.mode == "tts-preview":
                self.stage = "Done"
                self.progress = max(self.progress, 99)
            else:
                self.progress = max(self.progress, 74)
            return

        render_match = re.search(r"Rendering\s+\[[^\]]+\]\s+(\d+)%\s+phase=([A-Za-z]+)", line)
        if render_match:
            pct = int(render_match.group(1))
            phase = render_match.group(2)
            self.stage = f"Render video / {phase}"
            self.progress = max(self.progress, min(99, 78 + int(pct * 0.20)))
            return

        if line.startswith("Rendered "):
            self.stage = "Rendered"
            self.progress = 99
            self._add_artifact_from_text(line)
            return

        if line.startswith("[pipeline] Final timing JSON:"):
            self.stage = "Pipeline complete"
            self.progress = 100
            self._add_artifact_from_text(line)
            return

        if line.startswith("[pipeline] Final ") or line.startswith("[pipeline] Selected "):
            self.stage = "Pipeline complete"
            self.progress = 100
            self._add_artifact_from_text(line)
            return

        if line.startswith("[info] loading engine:"):
            self._set_stage("TTS preview / loading", 20)
            return

        if "Traceback" in line or "RuntimeError" in line or re.search(r"\bERROR\b", line):
            self.stage = "Error detected"

    def scan_recent_artifacts(self) -> None:
        since = self.started_at - 2
        candidates: list[Path] = []
        for directory, patterns in (
            (TOPICS_DIR, ("*.md",)),
            (LOG_DIR, ("*.json",)),
            (TRANSCRIPTS_DIR, ("*.json",)),
            (TTS_SCRIPTS_DIR, ("*.json",)),
            (AUDIO_DIR, ("*.json", "*.wav")),
            (VIDEO_DIR, ("*.mp4",)),
        ):
            if not directory.exists():
                continue
            for pattern in patterns:
                candidates.extend(path for path in directory.glob(pattern) if path.stat().st_mtime >= since)
        for path in candidates:
            if path.is_file():
                self.artifacts[_rel(path)] = _artifact_payload(path)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            self.scan_recent_artifacts()
            return {
                "id": self.id,
                "mode": self.mode,
                "stop_after": self.stop_after,
                "status": self.status,
                "stage": self.stage,
                "progress": self.progress,
                "returncode": self.returncode,
                "started_at": self.started_at,
                "started_at_label": datetime.fromtimestamp(self.started_at).strftime("%Y-%m-%d %H:%M:%S"),
                "ended_at": self.ended_at,
                "ended_at_label": datetime.fromtimestamp(self.ended_at).strftime("%Y-%m-%d %H:%M:%S") if self.ended_at else "",
                "command": self.command_display,
                "log_path": _rel(self.log_path),
                "log_url": f"/files/{_rel(self.log_path)}",
                "lines": list(self.lines)[-420:],
                "artifacts": sorted(self.artifacts.values(), key=lambda item: item["mtime"], reverse=True),
            }


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def start(self, request: StartJobRequest) -> Job:
        command = build_pipeline_command(request)
        RUN_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex[:8]
        log_path = RUN_RECORDS_DIR / f"dashboard_{_now_label()}_{job_id}.log"
        job = Job(
            id=job_id,
            mode=request.mode,
            stop_after="audio" if request.mode == "tts-preview" else request.stop_after,
            command=command,
            command_display=_command_display(command),
            log_path=log_path,
            started_at=time.time(),
        )
        with self.lock:
            self.jobs[job_id] = job
        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    def _run_job(self, job: Job) -> None:
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        with job.lock:
            job.status = "running"
            job.stage = "Starting"
            job.progress = 1

        with job.log_path.open("w", encoding="utf-8", errors="replace") as log_file:
            log_file.write(f"# Dashboard job {job.id}\n")
            log_file.write(f"# Started: {datetime.fromtimestamp(job.started_at).isoformat(timespec='seconds')}\n")
            log_file.write(f"# Command: {job.command_display}\n\n")
            log_file.flush()

            try:
                process = subprocess.Popen(
                    job.command,
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                    creationflags=creationflags,
                )
            except Exception as exc:
                line = f"[dashboard] Failed to start process: {exc}"
                log_file.write(line + "\n")
                job.append_line(line)
                with job.lock:
                    job.status = "failed"
                    job.returncode = -1
                    job.ended_at = time.time()
                return

            with job.lock:
                job.process = process

            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
                job.append_line(line)

            returncode = process.wait()
            ended_at = time.time()
            with job.lock:
                job.returncode = returncode
                job.ended_at = ended_at
                job.scan_recent_artifacts()
                if job.status == "stopping":
                    job.status = "stopped"
                    job.stage = "Stopped"
                elif returncode == 0:
                    job.status = "completed"
                    job.stage = "Completed"
                    job.progress = FINAL_PROGRESS
                else:
                    job.status = "failed"
                    job.stage = f"Failed ({returncode})"

            log_file.write(f"\n# Finished: {datetime.fromtimestamp(ended_at).isoformat(timespec='seconds')}\n")
            log_file.write(f"# Return code: {returncode}\n")

    def get(self, job_id: str) -> Job:
        try:
            return self.jobs[job_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    def list(self) -> list[dict[str, Any]]:
        with self.lock:
            jobs = sorted(self.jobs.values(), key=lambda item: item.started_at, reverse=True)
        return [job.snapshot() for job in jobs]

    def stop(self, job_id: str) -> Job:
        job = self.get(job_id)
        with job.lock:
            process = job.process
            if not process or process.poll() is not None:
                return job
            job.status = "stopping"
            job.stage = "Stopping"

        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
        return job


def _append_if_value(command: list[str], flag: str, value: str | int | None) -> None:
    if value not in (None, ""):
        command.extend([flag, str(value)])


def _append_render_args(command: list[str], req: StartJobRequest) -> None:
    for flag, value in (
        ("--layout", req.layout),
        ("--plan", req.plan),
        ("--audio", req.audio),
        ("--out", req.out),
        ("--max-seconds", req.max_seconds),
        ("--concurrency", req.concurrency),
        ("--gl", req.gl),
        ("--port", req.port),
    ):
        _append_if_value(command, flag, value)
    if req.keep_bundle:
        command.append("--keep-bundle")
    if req.keep_staged_audio:
        command.append("--keep-staged-audio")


def build_pipeline_command(req: StartJobRequest) -> list[str]:
    if req.mode not in {"from-topic", "from-log", "from-transcript", "from-tts", "video", "tts-preview"}:
        raise HTTPException(status_code=400, detail=f"Unsupported mode: {req.mode}")
    if req.provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")

    if req.mode == "tts-preview":
        if not req.preview_voice_dir:
            raise HTTPException(status_code=400, detail="Voice directory is required")
        if not (req.preview_voice_text or "").strip():
            raise HTTPException(status_code=400, detail="Preview text is required")
        command = get_executable_command("tts_python") + [
            "-u",
            "pipeline/tts/preview_voice.py",
            "--voice-dir",
            _resolve_optional_user_path(req.preview_voice_dir),
            "--text",
            req.preview_voice_text.strip(),
            "--out-dir",
            str(VOICE_PREVIEW_DIR),
            "--out-name",
            f"voice_preview_{_now_label()}.wav",
        ]
        _append_if_value(command, "--sample", req.preview_voice_sample)
        return command

    allowed_stop_after = STOP_AFTER_BY_MODE.get(req.mode, ["video"])
    if req.stop_after not in allowed_stop_after:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported stop_after={req.stop_after!r} for mode={req.mode!r}",
        )

    command = get_executable_command("main_python") + ["-u", "debate_pipeline.py", req.mode]

    if req.mode == "from-topic":
        if req.topic_source == "raw":
            if not (req.topic or "").strip():
                raise HTTPException(status_code=400, detail="Raw topic is required")
            command.extend(["--topic", req.topic.strip()])
        else:
            _append_if_value(command, "--topic-file", req.topic_file)
        _append_if_value(command, "--turns", req.turns)
        _append_if_value(command, "--reply-max-tokens", req.reply_max_tokens)
        _append_if_value(command, "--provider", req.provider)
        _append_if_value(command, "--model", req.model)
        _append_if_value(command, "--density", req.density)
        _append_if_value(command, "--stop-after", req.stop_after)
        if req.skip_clean:
            command.append("--skip-clean")
        if req.skip_whisper:
            command.append("--skip-whisper")
        _append_if_value(command, "--voice-root", req.voice_root)
        _append_render_args(command, req)
        return command

    if req.mode == "from-log":
        _append_if_value(command, "--log", req.log or "latest")
        _append_if_value(command, "--provider", req.provider)
        _append_if_value(command, "--model", req.model)
        _append_if_value(command, "--density", req.density)
        _append_if_value(command, "--stop-after", req.stop_after)
        if req.skip_clean:
            command.append("--skip-clean")
        if req.skip_whisper:
            command.append("--skip-whisper")
        _append_if_value(command, "--voice-root", req.voice_root)
        _append_render_args(command, req)
        return command

    if req.mode == "from-transcript":
        _append_if_value(command, "--transcript", req.transcript or "latest")
        _append_if_value(command, "--provider", req.provider)
        _append_if_value(command, "--model", req.model)
        _append_if_value(command, "--density", req.density)
        _append_if_value(command, "--stop-after", req.stop_after)
        if req.skip_whisper:
            command.append("--skip-whisper")
        _append_if_value(command, "--voice-root", req.voice_root)
        _append_render_args(command, req)
        return command

    if req.mode == "from-tts":
        _append_if_value(command, "--tts-script", req.tts_script or "latest")
        _append_if_value(command, "--stop-after", req.stop_after)
        if req.skip_whisper:
            command.append("--skip-whisper")
        _append_if_value(command, "--voice-root", req.voice_root)
        _append_render_args(command, req)
        return command

    _append_if_value(command, "--timeline", req.timeline or "latest")
    _append_render_args(command, req)
    return command


app = FastAPI(title="Debate Pipeline Dashboard")
manager = JobManager()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return DASHBOARD_HTML


@app.get("/api/options")
def options() -> dict[str, Any]:
    video_config = get_video_config()
    default_layout = video_config.get("default_layout", "dual")
    return {
        "providers": PROVIDERS,
        "layouts": LAYOUTS,
        "stop_after": STOP_AFTER_BY_MODE,
        "voice_packs": _list_voice_packs(),
        "default_layout": default_layout,
        "files": {
            "topics": _list_files(TOPICS_DIR, ("*.md",)),
            "logs": _list_files(LOG_DIR, ("*.json",)),
            "transcripts": _list_files(TRANSCRIPTS_DIR, ("*.json",)),
            "tts_scripts": _list_files(TTS_SCRIPTS_DIR, ("*.json",)),
            "timelines": _list_files(AUDIO_DIR, ("*.json",)),
            "audio": _list_files(AUDIO_DIR, ("*.wav",)),
            "videos": _list_files(VIDEO_DIR, ("*.mp4",)),
        },
    }


@app.get("/api/jobs")
def list_jobs() -> list[dict[str, Any]]:
    return manager.list()


@app.post("/api/jobs")
def start_job(request: StartJobRequest) -> dict[str, Any]:
    job = manager.start(request)
    return job.snapshot()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return manager.get(job_id).snapshot()


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, Any]:
    return manager.stop(job_id).snapshot()


@app.get("/files/{rel_path:path}")
def get_file(rel_path: str) -> FileResponse:
    path = _safe_repo_path(rel_path)
    if path.is_dir():
        raise HTTPException(status_code=400, detail="Directories cannot be served")
    return FileResponse(path)


DASHBOARD_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Debate Pipeline Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fb;
      --surface: #ffffff;
      --surface-2: #eef3f6;
      --text: #18212f;
      --muted: #617083;
      --line: #d7dee8;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --warn: #b45309;
      --danger: #b91c1c;
      --ok: #15803d;
      --shadow: 0 12px 30px rgba(20, 31, 46, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    button, input, select, textarea { font: inherit; letter-spacing: 0; }
    .shell { min-height: 100vh; display: flex; flex-direction: column; }
    header {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      position: sticky;
      top: 0;
      z-index: 2;
      backdrop-filter: blur(10px);
    }
    h1 { margin: 0; font-size: 18px; font-weight: 760; }
    .subtle { color: var(--muted); font-size: 13px; }
    .main {
      flex: 1;
      display: grid;
      grid-template-columns: minmax(360px, 470px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px;
      max-width: 1680px;
      width: 100%;
      margin: 0 auto;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .panel-header {
      min-height: 54px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    .panel-title { font-size: 15px; font-weight: 720; }
    .panel-body { padding: 16px; }
    .grid { display: grid; gap: 12px; }
    .grid.two { grid-template-columns: 1fr 1fr; }
    .grid.three { grid-template-columns: repeat(3, 1fr); }
    .tabs {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 6px;
      padding: 6px;
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .tab {
      min-height: 38px;
      border: 1px solid transparent;
      border-radius: 6px;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .tab.active {
      background: var(--surface);
      color: var(--text);
      border-color: var(--line);
      box-shadow: 0 1px 4px rgba(20, 31, 46, 0.08);
    }
    .tab:disabled { cursor: not-allowed; opacity: 0.55; }
    .section-title {
      margin-top: 2px;
      color: var(--text);
      font-size: 13px;
      font-weight: 780;
    }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; font-weight: 650; }
    input, select, textarea {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      padding: 8px 10px;
      outline: none;
    }
    textarea { min-height: 118px; resize: vertical; line-height: 1.45; }
    input:focus, select:focus, textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12); }
    .toggle-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 38px;
      color: var(--text);
      font-size: 13px;
    }
    .toggle-row input { width: 16px; min-height: 16px; accent-color: var(--accent); }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .btn {
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      color: var(--text);
      padding: 0 14px;
      cursor: pointer;
      font-weight: 700;
    }
    .btn.primary { background: var(--accent); border-color: var(--accent); color: white; }
    .btn.danger { background: white; border-color: #fecaca; color: var(--danger); }
    .btn:disabled { cursor: not-allowed; opacity: 0.55; }
    .status-line { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 0 10px;
      border-radius: 999px;
      background: var(--surface-2);
      color: var(--muted);
      font-size: 12px;
      font-weight: 760;
      border: 1px solid var(--line);
    }
    .pill.ok { color: var(--ok); background: #eefbf2; border-color: #bbf7d0; }
    .pill.warn { color: var(--warn); background: #fff7ed; border-color: #fed7aa; }
    .pill.danger { color: var(--danger); background: #fff1f2; border-color: #fecdd3; }
    .progress {
      height: 12px;
      border-radius: 999px;
      background: #e5eaf1;
      overflow: hidden;
      border: 1px solid var(--line);
    }
    .progress > div {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      transition: width 240ms ease;
    }
    .stage-flow {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
    }
    .stage-step {
      min-height: 54px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
      padding: 8px;
      display: grid;
      align-content: center;
      gap: 3px;
    }
    .stage-step strong { font-size: 12px; }
    .stage-step span { font-size: 11px; color: var(--muted); }
    .stage-step.active { border-color: #7dd3fc; background: #eff6ff; }
    .stage-step.done { border-color: #86efac; background: #f0fdf4; }
    .stage-step.failed { border-color: #fecaca; background: #fff1f2; }
    .command {
      min-height: 44px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8fafc;
      color: #334155;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }
    .log {
      height: min(56vh, 640px);
      min-height: 340px;
      padding: 12px;
      border: 1px solid #1f2937;
      border-radius: 8px;
      background: #111827;
      color: #d1d5db;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      overflow: auto;
      white-space: pre-wrap;
    }
    .artifacts {
      display: grid;
      gap: 8px;
      max-height: 190px;
      overflow: auto;
    }
    .artifact {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      min-height: 40px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfdff;
    }
    .artifact a { color: var(--accent-2); text-decoration: none; font-weight: 650; overflow-wrap: anywhere; }
    .artifact span { color: var(--muted); font-size: 12px; white-space: nowrap; }
    .history {
      display: grid;
      gap: 8px;
      max-height: 210px;
      overflow: auto;
    }
    .history-row {
      display: grid;
      grid-template-columns: 80px 1fr 70px;
      gap: 10px;
      align-items: center;
      min-height: 38px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfdff;
      font-size: 13px;
    }
    .layout-preview {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f172a;
      padding: 10px;
      aspect-ratio: 16 / 9;
      width: 100%;
      display: grid;
      color: #e5e7eb;
      overflow: hidden;
    }
    .layout-preview .frame {
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 6px;
      padding: 10px;
      display: grid;
      gap: 8px;
      min-height: 0;
    }
    .layout-preview .box {
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 6px;
      background: rgba(255,255,255,0.08);
      display: grid;
      place-items: center;
      font-size: 12px;
      font-weight: 720;
      min-height: 0;
    }
    .layout-preview .caption { background: rgba(15,118,110,0.86); }
    .layout-preview .wave { background: repeating-linear-gradient(90deg, rgba(96,165,250,.85) 0 4px, rgba(255,255,255,.1) 4px 12px); }
    .layout-preview .node { border-radius: 999px; }
    audio { width: 100%; height: 36px; }
    .hidden { display: none !important; }
    @media (max-width: 980px) {
      header { height: auto; min-height: 64px; align-items: flex-start; flex-direction: column; padding: 14px 16px; }
      .main { grid-template-columns: 1fr; padding: 12px; }
      .tabs { grid-template-columns: repeat(2, 1fr); }
      .grid.two, .grid.three { grid-template-columns: 1fr; }
      .log { height: 420px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Debate Pipeline Dashboard</h1>
        <div class="subtle">本地编排入口：topic、debate、transcript、TTS、Remotion</div>
      </div>
      <div class="status-line">
        <span id="topStatus" class="pill">Idle</span>
        <span id="topJob" class="pill">No active job</span>
      </div>
    </header>

    <main class="main">
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">Run Setup</div>
          <button id="refreshOptions" class="btn" type="button">Refresh</button>
        </div>
        <div class="panel-body grid">
          <div class="tabs" id="modeTabs">
            <button class="tab active" data-mode="from-topic" type="button">Topic</button>
            <button class="tab" data-mode="from-log" type="button">Log</button>
            <button class="tab" data-mode="from-transcript" type="button">Transcript</button>
            <button class="tab" data-mode="from-tts" type="button">TTS</button>
            <button class="tab" data-mode="video" type="button">Video</button>
          </div>

          <label>Run until
            <select id="stopAfter"></select>
          </label>

          <div id="topicFields" class="grid">
            <div class="section-title">Topic</div>
            <label>Topic source
              <select id="topicSource">
                <option value="raw">Raw topic text</option>
                <option value="file">Existing topic framework</option>
              </select>
            </label>
            <label id="rawTopicField">Raw topic
              <textarea id="topicText" placeholder="输入辩题，例如：当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。"></textarea>
            </label>
            <label id="topicFileField" class="hidden">Topic framework
              <select id="topicFile"></select>
            </label>
          </div>

          <div id="logFields" class="grid hidden">
            <div class="section-title">Log</div>
            <label>Debate log
              <select id="logFile"></select>
            </label>
          </div>

          <div id="transcriptFields" class="grid hidden">
            <div class="section-title">Transcript</div>
            <label>Transcript
              <select id="transcriptFile"></select>
            </label>
          </div>

          <div id="ttsFields" class="grid hidden">
            <div class="section-title">TTS</div>
            <label>TTS script
              <select id="ttsFile"></select>
            </label>
          </div>

          <div id="videoFields" class="grid hidden">
            <div class="section-title">Video</div>
            <label>Timing JSON
              <select id="timelineFile"></select>
            </label>
          </div>

          <div id="llmFields" class="grid two">
            <div class="section-title" style="grid-column: 1 / -1;">LLM</div>
            <label>Provider
              <select id="provider"></select>
            </label>
            <label>Model override
              <input id="model" placeholder="留空使用配置默认模型" />
            </label>
          </div>

          <div id="debateFields" class="grid two">
            <div class="section-title" style="grid-column: 1 / -1;">Debate</div>
            <label>Turns
              <input id="turns" type="number" min="1" value="3" />
            </label>
            <label>Reply max tokens
              <input id="replyMaxTokens" type="number" min="256" value="10240" />
            </label>
          </div>

          <div id="ttsOptionFields" class="grid three">
            <div class="section-title" style="grid-column: 1 / -1;">TTS</div>
            <label>Tag density
              <select id="density">
                <option value="low">low</option>
                <option value="medium" selected>medium</option>
                <option value="high">high</option>
              </select>
            </label>
            <label class="toggle-row"><input id="skipClean" type="checkbox" /> Skip clean</label>
            <label class="toggle-row"><input id="skipWhisper" type="checkbox" /> Skip Whisper</label>
          </div>

          <div id="voiceFields" class="grid">
            <label>Voice pack
              <select id="voicePack"></select>
            </label>
            <div class="grid three">
              <label>Preview speaker
                <select id="previewSpeaker">
                  <option value="host">host</option>
                  <option value="positive">positive</option>
                  <option value="negative">negative</option>
                </select>
              </label>
              <label>Voice sample
                <select id="previewSample"></select>
              </label>
              <label>Preview text
                <input id="previewText" value="大家好，欢迎来到今天的辩论现场。" />
              </label>
            </div>
            <div class="actions">
              <button id="testVoice" class="btn" type="button">Test voice</button>
              <audio id="voiceAudio" controls class="hidden"></audio>
            </div>
          </div>

          <div id="videoConfigFields" class="grid">
            <div class="section-title">Video</div>
            <div class="grid two">
            <label>Layout
              <select id="layout"></select>
            </label>
            <label>Output video path
              <input id="outPath" placeholder="留空使用默认 output/video" />
            </label>
            </div>
            <div id="layoutPreview" class="layout-preview"></div>

          <div class="grid three">
            <label>Concurrency
              <input id="concurrency" value="75%" />
            </label>
            <label>GL
              <input id="gl" value="angle" />
            </label>
            <label>Render port
              <input id="port" value="8099" />
            </label>
          </div>

          <div class="grid three">
            <label>Max seconds
              <input id="maxSeconds" placeholder="可选" />
            </label>
            <label>Plan JSON
              <input id="plan" placeholder="可选" />
            </label>
            <label>Audio override
              <input id="audio" placeholder="可选" />
            </label>
          </div>

          <div class="grid two">
            <label class="toggle-row"><input id="keepBundle" type="checkbox" /> Keep Remotion bundle</label>
            <label class="toggle-row"><input id="keepStagedAudio" type="checkbox" /> Keep staged audio</label>
          </div>
          </div>

          <div class="actions">
            <button id="startJob" class="btn primary" type="button">Start</button>
            <button id="stopJob" class="btn danger" type="button" disabled>Stop</button>
            <span id="formHint" class="subtle">Ready.</span>
          </div>
        </div>
      </section>

      <section class="grid">
        <section class="panel">
          <div class="panel-header">
            <div class="panel-title">Progress</div>
            <div class="status-line">
              <span id="jobStatus" class="pill">Idle</span>
              <span id="jobStage" class="pill">No stage</span>
            </div>
          </div>
          <div class="panel-body grid">
            <div id="stageFlow" class="stage-flow"></div>
            <div class="progress"><div id="progressFill"></div></div>
            <div class="subtle" id="progressText">0%</div>
            <div class="command" id="commandText">No command yet.</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div class="panel-title">Artifacts</div>
            <a id="jobLogLink" class="subtle" href="#" target="_blank" rel="noreferrer">Log</a>
          </div>
          <div class="panel-body">
            <div id="artifacts" class="artifacts"><div class="subtle">No artifacts yet.</div></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div class="panel-title">Live Log</div>
            <button id="copyLog" class="btn" type="button">Copy tail</button>
          </div>
          <div class="panel-body">
            <div id="log" class="log">Waiting for a job...</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div class="panel-title">Recent Jobs</div>
            <button id="refreshJobs" class="btn" type="button">Refresh</button>
          </div>
          <div class="panel-body">
            <div id="history" class="history"><div class="subtle">No jobs in this dashboard session.</div></div>
          </div>
        </section>
      </section>
    </main>
  </div>

  <script>
    const state = { options: null, mode: 'from-topic', activeJobId: null, poll: null, locked: false };
    const $ = (id) => document.getElementById(id);
    const stageLabels = {
      topic: 'Topic',
      log: 'Log',
      transcript: 'Transcript',
      tts: 'TTS Script',
      audio: 'Audio',
      video: 'Video',
    };
    const stageTextNeedles = {
      topic: ['Generate topic framework'],
      log: ['Generate debate log', 'Clean log'],
      transcript: ['Humanize transcript'],
      tts: ['Insert TTS tags'],
      audio: ['Generate debate audio', 'TTS preview'],
      video: ['Render video', 'Rendered'],
    };

    function setHint(text, kind = '') {
      $('formHint').textContent = text;
      $('formHint').style.color = kind === 'error' ? 'var(--danger)' : 'var(--muted)';
    }

    function fillSelect(id, items, emptyLabel = 'latest') {
      const el = $(id);
      el.innerHTML = '';
      const latest = document.createElement('option');
      latest.value = 'latest';
      latest.textContent = emptyLabel;
      el.appendChild(latest);
      for (const item of items || []) {
        const opt = document.createElement('option');
        opt.value = item.path;
        opt.textContent = `${item.name} · ${item.mtime_label}`;
        el.appendChild(opt);
      }
    }

    function fillSimpleSelect(id, items, selected) {
      const el = $(id);
      el.innerHTML = '';
      for (const item of items || []) {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        if (item === selected) opt.selected = true;
        el.appendChild(opt);
      }
    }

    function fillStopAfter() {
      const allowed = (state.options && state.options.stop_after && state.options.stop_after[state.mode]) || ['video'];
      const el = $('stopAfter');
      const old = el.value;
      el.innerHTML = '';
      for (const item of allowed) {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = stageLabels[item] || item;
        el.appendChild(opt);
      }
      el.value = allowed.includes(old) ? old : allowed[allowed.length - 1];
    }

    function fillVoicePacks() {
      const select = $('voicePack');
      select.innerHTML = '';
      const packs = (state.options && state.options.voice_packs) || [];
      for (const pack of packs) {
        const opt = document.createElement('option');
        opt.value = pack.path;
        opt.textContent = pack.name;
        select.appendChild(opt);
      }
      if (!packs.length) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No voice packs found';
        select.appendChild(opt);
      }
      updatePreviewSamples();
    }

    function selectedVoicePack() {
      const packs = (state.options && state.options.voice_packs) || [];
      return packs.find(pack => pack.path === $('voicePack').value) || packs[0] || null;
    }

    function updatePreviewSamples() {
      const pack = selectedVoicePack();
      const speaker = $('previewSpeaker').value;
      const sampleSelect = $('previewSample');
      sampleSelect.innerHTML = '';
      const samples = pack && pack.speakers && pack.speakers[speaker] ? pack.speakers[speaker].samples : [];
      for (const sample of samples) {
        const opt = document.createElement('option');
        opt.value = sample.name;
        opt.textContent = sample.name;
        sampleSelect.appendChild(opt);
      }
      if (!samples.length) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No samples';
        sampleSelect.appendChild(opt);
      }
    }

    async function loadOptions() {
      const res = await fetch('/api/options');
      state.options = await res.json();
      fillSimpleSelect('provider', state.options.providers, 'local');
      fillSimpleSelect('layout', state.options.layouts, state.options.default_layout || 'dual');
      fillSelect('topicFile', state.options.files.topics, 'latest topic framework');
      fillSelect('logFile', state.options.files.logs, 'latest log');
      fillSelect('transcriptFile', state.options.files.transcripts, 'latest transcript');
      fillSelect('ttsFile', state.options.files.tts_scripts, 'latest TTS script');
      fillSelect('timelineFile', state.options.files.timelines, 'latest timing JSON');
      fillStopAfter();
      fillVoicePacks();
      renderLayoutPreview();
      updateVisibility();
    }

    function setMode(mode) {
      if (state.locked) return;
      state.mode = mode;
      for (const btn of document.querySelectorAll('.tab')) btn.classList.toggle('active', btn.dataset.mode === mode);
      fillStopAfter();
      updateVisibility();
    }

    function currentVoiceRoot() {
      const pack = selectedVoicePack();
      return pack ? pack.path : null;
    }

    function currentPreviewVoiceDir() {
      const pack = selectedVoicePack();
      const speaker = $('previewSpeaker').value;
      return pack && pack.speakers && pack.speakers[speaker] ? pack.speakers[speaker].voice_dir : null;
    }

    function selectedStages() {
      const allowed = (state.options && state.options.stop_after && state.options.stop_after[state.mode]) || ['video'];
      const stop = $('stopAfter').value || allowed[allowed.length - 1];
      const idx = allowed.indexOf(stop);
      return allowed.slice(0, idx + 1);
    }

    function includesStage(stage) {
      return selectedStages().includes(stage);
    }

    function renderLayoutPreview() {
      const layout = $('layout').value || 'dual';
      const preview = $('layoutPreview');
      if (layout === 'podcast') {
        preview.innerHTML = `
          <div class="frame" style="grid-template-rows: 1fr auto;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;min-height:0;">
              <div class="box">Positive camera</div>
              <div class="box">Negative camera</div>
            </div>
            <div class="box wave" style="height:36px;">Audio focus</div>
          </div>`;
      } else if (layout === 'mindmap') {
        preview.innerHTML = `
          <div class="frame" style="grid-template-columns:1fr 1.2fr 1fr;align-items:center;">
            <div class="box node" style="height:50px;">Positive</div>
            <div class="box" style="height:90px;">Argument map</div>
            <div class="box node" style="height:50px;">Negative</div>
          </div>`;
      } else {
        preview.innerHTML = `
          <div class="frame" style="grid-template-rows:1fr auto;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;min-height:0;">
              <div class="box">Positive side</div>
              <div class="box">Negative side</div>
            </div>
            <div class="box caption" style="height:42px;">Subtitle band</div>
          </div>`;
      }
    }

    function stagesFor(mode, stopAfter) {
      const allowed = (state.options && state.options.stop_after && state.options.stop_after[mode]) || ['video'];
      const stop = stopAfter || $('stopAfter').value || allowed[allowed.length - 1];
      const idx = allowed.indexOf(stop);
      return allowed.slice(0, idx >= 0 ? idx + 1 : allowed.length);
    }

    function activeStageIndex(job, stages) {
      if (!job) return -1;
      if (job.status === 'completed') return stages.length;
      const text = `${job.stage || ''}\n${(job.lines || []).slice(-8).join('\n')}`;
      for (let i = stages.length - 1; i >= 0; i -= 1) {
        const needles = stageTextNeedles[stages[i]] || [];
        if (needles.some(needle => text.includes(needle))) return i;
      }
      const thresholds = {topic: 5, log: 14, transcript: 34, tts: 46, audio: 58, video: 78};
      let idx = 0;
      for (let i = 0; i < stages.length; i += 1) {
        if ((job.progress || 0) >= (thresholds[stages[i]] || 0)) idx = i;
      }
      return idx;
    }

    function renderStageFlow(job = null) {
      const mode = job ? job.mode : state.mode;
      const stopAfter = job ? job.stop_after : $('stopAfter').value;
      const stages = stagesFor(mode, stopAfter);
      const flow = $('stageFlow');
      flow.style.gridTemplateColumns = `repeat(${Math.max(1, Math.min(stages.length, 6))}, minmax(0, 1fr))`;
      flow.innerHTML = '';
      const activeIdx = activeStageIndex(job, stages);
      const terminalFailed = job && ['failed', 'stopped'].includes(job.status);
      const terminalDone = job && job.status === 'completed';
      stages.forEach((stage, idx) => {
        const step = document.createElement('div');
        let className = 'stage-step';
        if (terminalDone || idx < activeIdx) className += ' done';
        else if (terminalFailed && idx === activeIdx) className += ' failed';
        else if (idx === activeIdx || (!job && idx === 0)) className += ' active';
        step.className = className;
        const detail = terminalDone || idx < activeIdx ? 'Done' : (idx === activeIdx || (!job && idx === 0) ? 'Active' : 'Pending');
        step.innerHTML = `<strong>${stageLabels[stage] || stage}</strong><span>${detail}</span>`;
        flow.appendChild(step);
      });
    }

    function setLocked(locked) {
      state.locked = locked;
      const keepEnabled = new Set(['stopJob', 'copyLog', 'refreshJobs']);
      for (const el of document.querySelectorAll('main button, main input, main select, main textarea')) {
        if (keepEnabled.has(el.id)) continue;
        el.disabled = locked;
      }
      $('stopJob').disabled = !locked;
      if (!locked) {
        $('stopJob').disabled = true;
      }
    }

    function updateVisibility() {
      const needsTranscript = includesStage('transcript');
      const needsTts = includesStage('tts');
      const needsAudio = includesStage('audio');
      const needsVideo = includesStage('video');

      $('topicFields').classList.toggle('hidden', state.mode !== 'from-topic');
      $('logFields').classList.toggle('hidden', state.mode !== 'from-log');
      $('transcriptFields').classList.toggle('hidden', state.mode !== 'from-transcript');
      $('ttsFields').classList.toggle('hidden', state.mode !== 'from-tts');
      $('videoFields').classList.toggle('hidden', state.mode !== 'video');
      $('llmFields').classList.toggle('hidden', !(includesStage('log') || needsTranscript || needsTts) || state.mode === 'from-tts' || state.mode === 'video');
      $('debateFields').classList.toggle('hidden', state.mode !== 'from-topic' || !includesStage('log'));
      $('ttsOptionFields').classList.toggle('hidden', !(needsTts || needsAudio || needsVideo) || state.mode === 'video');
      $('voiceFields').classList.toggle('hidden', !(needsAudio || needsVideo || state.mode === 'from-tts'));
      $('videoConfigFields').classList.toggle('hidden', !needsVideo && state.mode !== 'video');
      $('skipClean').parentElement.classList.toggle('hidden', !((state.mode === 'from-topic' || state.mode === 'from-log') && includesStage('log')));
      $('skipWhisper').parentElement.classList.toggle('hidden', !(needsAudio || needsVideo));
      updateTopicSource();
      renderLayoutPreview();
      renderStageFlow();
    }

    function updateTopicSource() {
      const useRaw = $('topicSource').value === 'raw';
      $('rawTopicField').classList.toggle('hidden', state.mode !== 'from-topic' || !useRaw);
      $('topicFileField').classList.toggle('hidden', state.mode !== 'from-topic' || useRaw);
    }

    function readValue(id) {
      const value = $(id).value.trim();
      return value === '' ? null : value;
    }

    function buildPayload() {
      return {
        mode: state.mode,
        stop_after: $('stopAfter').value,
        topic_source: $('topicSource').value,
        topic: readValue('topicText'),
        topic_file: $('topicFile').value,
        log: $('logFile').value,
        transcript: $('transcriptFile').value,
        tts_script: $('ttsFile').value,
        timeline: $('timelineFile').value,
        provider: $('provider').value,
        model: readValue('model'),
        turns: Number($('turns').value || 3),
        reply_max_tokens: Number($('replyMaxTokens').value || 10240),
        density: $('density').value,
        skip_clean: $('skipClean').checked,
        skip_whisper: $('skipWhisper').checked,
        voice_root: currentVoiceRoot(),
        layout: $('layout').value,
        out: readValue('outPath'),
        max_seconds: readValue('maxSeconds'),
        concurrency: readValue('concurrency'),
        gl: readValue('gl'),
        port: readValue('port'),
        plan: readValue('plan'),
        audio: readValue('audio'),
        keep_bundle: $('keepBundle').checked,
        keep_staged_audio: $('keepStagedAudio').checked,
      };
    }

    function pillClass(status) {
      if (status === 'completed') return 'pill ok';
      if (status === 'failed' || status === 'stopped') return 'pill danger';
      if (status === 'running' || status === 'stopping') return 'pill warn';
      return 'pill';
    }

    function renderJob(job) {
      $('jobStatus').className = pillClass(job.status);
      $('jobStatus').textContent = job.status || 'Idle';
      $('topStatus').className = $('jobStatus').className;
      $('topStatus').textContent = job.status || 'Idle';
      $('jobStage').textContent = job.stage || 'No stage';
      $('topJob').textContent = job.id ? `Job ${job.id}` : 'No active job';
      $('progressFill').style.width = `${job.progress || 0}%`;
      $('progressText').textContent = `${job.progress || 0}% · ${job.stage || ''}`;
      $('commandText').textContent = job.command || 'No command yet.';
      $('log').textContent = (job.lines && job.lines.length) ? job.lines.join('\n') : 'Waiting for output...';
      $('log').scrollTop = $('log').scrollHeight;
      $('jobLogLink').href = job.log_url || '#';
      const isLive = ['queued', 'running', 'stopping'].includes(job.status);
      setLocked(isLive);
      $('stopJob').disabled = !(job.status === 'running' || job.status === 'stopping');
      renderStageFlow(job);

      const artifacts = $('artifacts');
      artifacts.innerHTML = '';
      if (!job.artifacts || !job.artifacts.length) {
        artifacts.innerHTML = '<div class="subtle">No artifacts yet.</div>';
      } else {
        for (const item of job.artifacts) {
          const row = document.createElement('div');
          row.className = 'artifact';
          row.innerHTML = `<a href="${item.url}" target="_blank" rel="noreferrer">${item.path}</a><span>${formatSize(item.size)}</span>`;
          artifacts.appendChild(row);
        }
      }
      if (job.mode === 'tts-preview' && job.status === 'completed') {
        const wav = (job.artifacts || []).find(item => item.path.endsWith('.wav'));
        if (wav) {
          $('voiceAudio').src = wav.url;
          $('voiceAudio').classList.remove('hidden');
        }
      }
    }

    function formatSize(bytes) {
      if (!bytes) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      let value = bytes;
      let idx = 0;
      while (value >= 1024 && idx < units.length - 1) { value /= 1024; idx += 1; }
      return `${value.toFixed(idx ? 1 : 0)} ${units[idx]}`;
    }

    async function pollJob() {
      if (!state.activeJobId) return;
      const res = await fetch(`/api/jobs/${state.activeJobId}`);
      if (!res.ok) {
        clearInterval(state.poll);
        state.poll = null;
        state.activeJobId = null;
        setLocked(false);
        setHint('Active job was not found. Refresh the page if this happened after a server restart.', 'error');
        return;
      }
      const job = await res.json();
      renderJob(job);
      if (!['running', 'queued', 'stopping'].includes(job.status)) {
        clearInterval(state.poll);
        state.poll = null;
        await loadJobs();
        await loadOptions();
        setHint(job.status === 'completed' ? 'Completed.' : `Stopped at ${job.status}.`);
      }
    }

    async function loadJobs() {
      const res = await fetch('/api/jobs');
      const jobs = await res.json();
      const history = $('history');
      history.innerHTML = '';
      if (!jobs.length) {
        history.innerHTML = '<div class="subtle">No jobs in this dashboard session.</div>';
        return;
      }
      for (const job of jobs.slice(0, 12)) {
        const row = document.createElement('div');
        row.className = 'history-row';
        row.innerHTML = `<span class="${pillClass(job.status)}">${job.status}</span><span>${job.mode} → ${stageLabels[job.stop_after] || job.stop_after} · ${job.started_at_label}</span><button class="btn" data-job="${job.id}" type="button">Open</button>`;
        history.appendChild(row);
      }
      for (const btn of history.querySelectorAll('button[data-job]')) {
        btn.addEventListener('click', async () => {
          state.activeJobId = btn.dataset.job;
          const res = await fetch(`/api/jobs/${state.activeJobId}`);
          if (!res.ok) return;
          const job = await res.json();
          renderJob(job);
          if (state.poll) clearInterval(state.poll);
          state.poll = ['running', 'queued', 'stopping'].includes(job.status) ? setInterval(pollJob, 1000) : null;
        });
      }
      if (state.locked) setLocked(true);
    }

    async function startJob() {
      if (state.locked) return;
      setHint('Starting...');
      const payload = buildPayload();
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({detail: res.statusText}));
        setHint(err.detail || 'Failed to start', 'error');
        return;
      }
      const job = await res.json();
      state.activeJobId = job.id;
      renderJob(job);
      setHint('Running.');
      if (state.poll) clearInterval(state.poll);
      state.poll = setInterval(pollJob, 1000);
      await loadJobs();
    }

    async function testVoice() {
      if (state.locked) return;
      const voiceDir = currentPreviewVoiceDir();
      const previewText = readValue('previewText');
      if (!voiceDir) {
        setHint('No usable voice directory selected.', 'error');
        return;
      }
      if (!previewText) {
        setHint('Preview text is required.', 'error');
        return;
      }
      $('voiceAudio').classList.add('hidden');
      $('voiceAudio').removeAttribute('src');
      setHint('Starting voice preview...');
      const payload = {
        mode: 'tts-preview',
        stop_after: 'audio',
        preview_voice_dir: voiceDir,
        preview_voice_text: previewText,
        preview_voice_sample: $('previewSample').value || null,
      };
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({detail: res.statusText}));
        setHint(err.detail || 'Failed to start voice preview', 'error');
        return;
      }
      const job = await res.json();
      state.activeJobId = job.id;
      renderJob(job);
      setHint('Voice preview running.');
      if (state.poll) clearInterval(state.poll);
      state.poll = setInterval(pollJob, 1000);
      await loadJobs();
    }

    async function stopJob() {
      if (!state.activeJobId) return;
      await fetch(`/api/jobs/${state.activeJobId}/stop`, {method: 'POST'});
      await pollJob();
    }

    document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => setMode(btn.dataset.mode)));
    $('topicSource').addEventListener('change', updateTopicSource);
    $('stopAfter').addEventListener('change', updateVisibility);
    $('voicePack').addEventListener('change', () => { updatePreviewSamples(); updateVisibility(); });
    $('previewSpeaker').addEventListener('change', updatePreviewSamples);
    $('layout').addEventListener('change', renderLayoutPreview);
    $('refreshOptions').addEventListener('click', loadOptions);
    $('refreshJobs').addEventListener('click', loadJobs);
    $('startJob').addEventListener('click', startJob);
    $('testVoice').addEventListener('click', testVoice);
    $('stopJob').addEventListener('click', stopJob);
    $('copyLog').addEventListener('click', async () => {
      await navigator.clipboard.writeText($('log').textContent || '');
      setHint('Log tail copied.');
    });

    (async function init() {
      await loadOptions();
      await loadJobs();
      setMode('from-topic');
    })().catch(err => setHint(String(err), 'error'));
  </script>
</body>
</html>
"""


def main() -> None:
    port = int(os.environ.get("DEBATE_DASHBOARD_PORT", "7861"))
    host = os.environ.get("DEBATE_DASHBOARD_HOST", "127.0.0.1")
    print(f"Dashboard: http://{host}:{port}")
    uvicorn.run("dashboard_app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
