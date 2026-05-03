from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.tts.tts_lib import load_engine, load_voice_pack, text_to_voice
from pipeline_config import get_tts_config


TTS_CONFIG = get_tts_config()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a short CosyVoice preview from one voice directory.")
    parser.add_argument("--voice-dir", required=True, help="Directory containing voice sample audio + .txt transcript.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--out-dir", default="output/audio/voice_previews", help="Output directory.")
    parser.add_argument("--out-name", default=None, help="Output wav filename.")
    parser.add_argument("--model-dir", default=TTS_CONFIG["model_dir"], help="CosyVoice model directory.")
    parser.add_argument("--sample", default=None, help="Specific voice sample stem to use.")
    parser.add_argument("--seed", type=int, default=20260503)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    voice_dir = Path(args.voice_dir).expanduser().resolve()
    if not voice_dir.exists():
        raise FileNotFoundError(f"Voice directory does not exist: {voice_dir}")

    pack = load_voice_pack(str(voice_dir))
    if not pack:
        raise RuntimeError(f"Voice directory has no usable audio/txt pairs: {voice_dir}")

    sample_key = args.sample or sorted(pack.keys())[0]
    if sample_key not in pack:
        raise KeyError(f"Voice sample {sample_key!r} not found in {voice_dir}; available={sorted(pack)}")
    sample_voice, sample_text = pack[sample_key]

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_name = args.out_name or f"voice_preview_{voice_dir.parent.name}_{voice_dir.name}_{sample_key}.wav"
    print(f"[info] loading engine: {args.model_dir}")
    print(f"[info] voice dir: {voice_dir}")
    print(f"[info] sample: {sample_key}")
    engine = load_engine(str(Path(args.model_dir).expanduser().resolve()))
    out_path = text_to_voice(
        engine,
        sample_voice=sample_voice,
        sample_text=sample_text,
        text=args.text,
        out_dir=str(out_dir),
        out_name=out_name,
        seed=args.seed,
    )
    print(f"[done] {out_path}")


if __name__ == "__main__":
    main()
