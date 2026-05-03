from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = REPO_ROOT / "pipeline.config.json"
LOCAL_OVERRIDE_CONFIG_PATH = REPO_ROOT / "pipeline.config.local.json"
EXAMPLE_CONFIG_PATH = REPO_ROOT / "pipeline.config.example.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "executables": {
        "main_python": "python",
        "tts_python": "python",
        "node": "node",
        "node_package_manager": "npm",
    },
    "llm": {
        "local_model_path": ".cache/models/qwen2.5-3b-instruct-q4_k_m.gguf",
        "local_n_gpu_layers": -1,
        "local_n_ctx": 16384,
        "default_model_name": "Qwen2.5-3B-Instruct-Q4_K_M",
    },
    "tts": {
        "model_dir": ".cache/models/Fun-CosyVoice3-0.5B-2512",
        "voice_root": "assets/voices/default",
        "speaker_dirs": {
            "positive": "positive",
            "negative": "negative",
            "host": "host",
        },
        "output_dir": "output/audio",
        "inter_turn_pause_ms": 600,
        "intra_turn_pause_ms": 250,
        "verify_with_whisper": True,
        "whisper_model_name": "small",
        "whisper_model_dir": ".cache/whisper",
        "whisper_language": "Chinese",
        "cer_threshold": 0.25,
        "min_chars_to_verify": 4,
        "primary_attempts": 3,
        "fallback_attempts_per_voice": 1,
        "max_fallback_voices": 3,
        "base_seed": 20250418,
    },
    "video": {
        "app_dir": "pipeline/video/remotion",
        "output_dir": "output/video",
        "default_layout": "dual",
    },
    "bootstrap": {
        "local_llm_model_source": None,
        "cosyvoice_model_source": None,
        "local_llm_download": {
            "provider": "huggingface",
            "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
            "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
            "enabled": True,
        },
        "cosyvoice_download": {
            "provider": "modelscope",
            "repo_id": "FunAudioLLM/Fun-CosyVoice3-0.5B-2512",
            "enabled": True,
        },
    },
}


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_repo_path(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path.resolve())


def normalize_command(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(part) for part in value]
    return [str(value)]


@lru_cache(maxsize=1)
def load_pipeline_config() -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        config = _deep_merge(config, loaded)
    if LOCAL_OVERRIDE_CONFIG_PATH.exists():
        loaded = json.loads(LOCAL_OVERRIDE_CONFIG_PATH.read_text(encoding="utf-8-sig"))
        config = _deep_merge(config, loaded)
    return config


def get_executable_command(name: str) -> list[str]:
    config = load_pipeline_config()
    try:
        value = config["executables"][name]
    except KeyError as exc:
        raise KeyError(f"Unknown executable config key: {name}") from exc
    return normalize_command(value)


def get_local_llm_provider_config(
    *,
    default_model: str | None = None,
    n_ctx: int | None = None,
) -> dict[str, Any]:
    llm_config = load_pipeline_config()["llm"]
    return {
        "model_path": resolve_repo_path(llm_config["local_model_path"]),
        "n_gpu_layers": int(llm_config.get("local_n_gpu_layers", -1)),
        "n_ctx": int(n_ctx or llm_config.get("local_n_ctx", 16384)),
        "default_model": default_model or llm_config.get("default_model_name"),
    }


def get_tts_config() -> dict[str, Any]:
    config = deepcopy(load_pipeline_config()["tts"])
    config["model_dir"] = resolve_repo_path(config["model_dir"])
    config["voice_root"] = resolve_repo_path(config["voice_root"])
    config["output_dir"] = resolve_repo_path(config["output_dir"])
    config["whisper_model_dir"] = resolve_repo_path(config["whisper_model_dir"])
    config["speaker_dirs"] = {
        speaker: resolve_repo_path(str(Path(config["voice_root"]) / folder_name))
        for speaker, folder_name in config.get("speaker_dirs", {}).items()
    }
    return config


def get_video_config() -> dict[str, Any]:
    config = deepcopy(load_pipeline_config()["video"])
    config["app_dir"] = resolve_repo_path(config["app_dir"])
    config["output_dir"] = resolve_repo_path(config["output_dir"])
    return config


def get_bootstrap_config() -> dict[str, Any]:
    config = deepcopy(load_pipeline_config()["bootstrap"])
    config["local_llm_model_source"] = resolve_repo_path(
        config.get("local_llm_model_source")
    )
    config["cosyvoice_model_source"] = resolve_repo_path(
        config.get("cosyvoice_model_source")
    )
    return config
