from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline_config import (
    get_bootstrap_config,
    get_executable_command,
    get_local_llm_provider_config,
    get_tts_config,
    get_video_config,
)

HUGGINGFACE_CACHE_ROOT = REPO_ROOT / ".cache" / "huggingface"
MODELSCOPE_CACHE_ROOT = REPO_ROOT / ".cache" / "modelscope"
TRANSFORMERS_CACHE_ROOT = HUGGINGFACE_CACHE_ROOT / "transformers"


def _prepare_repo_cache_env() -> dict[str, str]:
    HUGGINGFACE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    MODELSCOPE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    TRANSFORMERS_CACHE_ROOT.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("HF_HOME", str(HUGGINGFACE_CACHE_ROOT))
    env.setdefault("HUGGINGFACE_HUB_CACHE", str(HUGGINGFACE_CACHE_ROOT / "hub"))
    env.setdefault("TRANSFORMERS_CACHE", str(TRANSFORMERS_CACHE_ROOT))
    env.setdefault("MODELSCOPE_CACHE", str(MODELSCOPE_CACHE_ROOT))
    return env


BOOTSTRAP_ENV = _prepare_repo_cache_env()
os.environ.update(BOOTSTRAP_ENV)


def _link_or_copy_file(source: Path, target: Path, prefer_hardlink: bool) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return "exists"

    if prefer_hardlink:
        try:
            os.link(source, target)
            return "hardlink"
        except OSError:
            pass

    shutil.copy2(source, target)
    return "copy"


def _populate_tree(source: Path, target: Path, prefer_hardlink: bool) -> tuple[int, int]:
    linked = 0
    copied = 0
    target.mkdir(parents=True, exist_ok=True)

    for entry in source.rglob("*"):
        relative = entry.relative_to(source)
        destination = target / relative
        if entry.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        method = _link_or_copy_file(entry, destination, prefer_hardlink)
        if method == "hardlink":
            linked += 1
        elif method == "copy":
            copied += 1

    return linked, copied


def _ensure_file(label: str, source: str | None, target: Path, prefer_hardlink: bool) -> None:
    if target.exists():
        print(f"[bootstrap] {label}: already present -> {target}")
        return
    if not source:
        print(f"[bootstrap] {label}: no source configured, skipped")
        return

    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"{label} source does not exist: {source_path}")

    method = _link_or_copy_file(source_path, target, prefer_hardlink)
    print(f"[bootstrap] {label}: {method} -> {target}")


def _ensure_tree(label: str, source: str | None, target: Path, prefer_hardlink: bool) -> None:
    if not source:
        print(f"[bootstrap] {label}: no source configured, skipped")
        return

    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"{label} source does not exist: {source_path}")

    linked, copied = _populate_tree(source_path, target, prefer_hardlink)
    print(
        f"[bootstrap] {label}: target={target} hardlinked={linked} copied={copied}"
    )


def _download_huggingface_file(
    *,
    repo_id: str,
    filename: str,
    target: Path,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"[bootstrap] local LLM model: already present -> {target}")
        return

    try:
        from huggingface_hub import hf_hub_download

        download_path = Path(
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(target.parent),
            )
        )
    except ModuleNotFoundError:
        command = get_executable_command("main_python") + [
            "-c",
            (
                "from huggingface_hub import hf_hub_download; import sys; "
                "print(hf_hub_download(repo_id=sys.argv[1], filename=sys.argv[2], local_dir=sys.argv[3]))"
            ),
            repo_id,
            filename,
            str(target.parent),
        ]
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            env=BOOTSTRAP_ENV,
            text=True,
        )
        download_path = Path(completed.stdout.strip().splitlines()[-1])

    if download_path.resolve() != target.resolve():
        shutil.copy2(download_path, target)
    print(f"[bootstrap] local LLM model: downloaded -> {target}")


def _download_modelscope_snapshot(*, repo_id: str, target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        print(f"[bootstrap] CosyVoice model directory: already present -> {target}")
        return

    target.mkdir(parents=True, exist_ok=True)
    try:
        from modelscope import snapshot_download

        snapshot_download(
            repo_id,
            cache_dir=str(MODELSCOPE_CACHE_ROOT),
            local_dir=str(target),
        )
    except ModuleNotFoundError:
        command = get_executable_command("tts_python") + [
            "-c",
            (
                "from modelscope import snapshot_download; import sys; "
                "snapshot_download(sys.argv[1], cache_dir=sys.argv[2], local_dir=sys.argv[3])"
            ),
            repo_id,
            str(MODELSCOPE_CACHE_ROOT),
            str(target),
        ]
        subprocess.run(command, check=True, env=BOOTSTRAP_ENV)
    print(f"[bootstrap] CosyVoice model directory: downloaded -> {target}")


def _ensure_local_llm_model(
    bootstrap_config: dict,
    local_llm_config: dict,
    prefer_hardlink: bool,
    allow_downloads: bool,
) -> None:
    target = Path(local_llm_config["model_path"])

    if bootstrap_config.get("local_llm_model_source"):
        _ensure_file(
            "local LLM model",
            bootstrap_config.get("local_llm_model_source"),
            target,
            prefer_hardlink=prefer_hardlink,
        )
        return

    download = bootstrap_config.get("local_llm_download") or {}
    if allow_downloads and download.get("enabled"):
        provider = download.get("provider", "huggingface")
        if provider != "huggingface":
            raise ValueError(f"Unsupported local LLM download provider: {provider}")
        _download_huggingface_file(
            repo_id=download["repo_id"],
            filename=download["filename"],
            target=target,
        )
        return

    print("[bootstrap] local LLM model: no source or download configured, skipped")


def _ensure_cosyvoice_model(
    bootstrap_config: dict,
    tts_config: dict,
    prefer_hardlink: bool,
    allow_downloads: bool,
) -> None:
    target = Path(tts_config["model_dir"])

    if bootstrap_config.get("cosyvoice_model_source"):
        _ensure_tree(
            "CosyVoice model directory",
            bootstrap_config.get("cosyvoice_model_source"),
            target,
            prefer_hardlink=prefer_hardlink,
        )
        return

    download = bootstrap_config.get("cosyvoice_download") or {}
    if allow_downloads and download.get("enabled"):
        provider = download.get("provider", "modelscope")
        if provider != "modelscope":
            raise ValueError(f"Unsupported CosyVoice download provider: {provider}")
        _download_modelscope_snapshot(repo_id=download["repo_id"], target=target)
        return

    print("[bootstrap] CosyVoice model directory: no source or download configured, skipped")


def _install_video_dependencies(force: bool) -> None:
    video_config = get_video_config()
    app_dir = Path(video_config["app_dir"])
    node_modules = app_dir / "node_modules"

    if node_modules.exists() and not force:
        print(f"[bootstrap] video deps: already installed -> {node_modules}")
        return

    command = get_executable_command("node_package_manager") + ["install"]
    print(f"[bootstrap] video deps: {subprocess.list2cmdline(command)}")
    subprocess.run(command, cwd=app_dir, check=True, env=BOOTSTRAP_ENV)


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare repo-local runtime assets.")
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Skip linking/copying repo-local model assets.",
    )
    parser.add_argument(
        "--skip-video-deps",
        action="store_true",
        help="Skip installing Remotion node dependencies.",
    )
    parser.add_argument(
        "--force-video-deps",
        action="store_true",
        help="Run bun install even if node_modules already exists.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy model files instead of creating hardlinks when possible.",
    )
    parser.add_argument(
        "--skip-downloads",
        action="store_true",
        help="Do not download public models when repo-local targets are missing.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    prefer_hardlink = not args.copy

    if not args.skip_models:
        bootstrap_config = get_bootstrap_config()
        local_llm_config = get_local_llm_provider_config()
        tts_config = get_tts_config()
        allow_downloads = not args.skip_downloads

        _ensure_local_llm_model(
            bootstrap_config,
            local_llm_config,
            prefer_hardlink=prefer_hardlink,
            allow_downloads=allow_downloads,
        )
        _ensure_cosyvoice_model(
            bootstrap_config,
            tts_config,
            prefer_hardlink=prefer_hardlink,
            allow_downloads=allow_downloads,
        )

    if not args.skip_video_deps:
        _install_video_dependencies(force=args.force_video_deps)


if __name__ == "__main__":
    main()
