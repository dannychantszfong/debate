import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATCHA_TTS_ROOT = REPO_ROOT / "third_party" / "Matcha-TTS"
COSYVOICE_ROOT = REPO_ROOT / "third_party" / "CosyVoice"
MODELSCOPE_CACHE_ROOT = REPO_ROOT / ".cache" / "modelscope"

MODELSCOPE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MODELSCOPE_CACHE", str(MODELSCOPE_CACHE_ROOT))

for candidate in (MATCHA_TTS_ROOT, COSYVOICE_ROOT):
    candidate_str = str(candidate)
    if candidate.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import torch
import torchaudio
from cosyvoice.cli.cosyvoice import AutoModel


def load_engine(model_dir: str):
    """Load the TTS model once. Reuse across many calls."""
    model = AutoModel(model_dir=model_dir)
    model._is_v3 = os.path.exists(os.path.join(model_dir, 'cosyvoice3.yaml'))
    return model


def load_voice_pack(pack_dir: str) -> dict:
    """
    Load a voice pack folder. Expects pairs like:
        voices/alice.wav (or .mp3/.flac/.ogg/.m4a)  +  voices/alice.txt
    Returns: {'alice': (audio_path, transcript), ...}
    """
    AUDIO_EXTS = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
    pack = {}
    for audio in Path(pack_dir).iterdir():
        if audio.suffix.lower() not in AUDIO_EXTS:
            continue
        txt = audio.with_suffix('.txt')
        if not txt.exists():
            print(f'[skip] {audio.name}: no matching .txt')
            continue
        pack[audio.stem] = (str(audio), txt.read_text(encoding='utf-8').strip())
    return pack

def text_to_voice(
    engine,
    sample_voice: str,
    sample_text: str,
    text: str,
    out_dir: str,
    out_name: str = 'output.wav',
    pause_ms: int = 250,
    speed: float = 1.0,
    seed: int | None = None,
) -> str:
    """
    Generate a single audio file from `text` using the given voice sample.

    Args:
        engine:       model returned by load_engine()
        sample_voice: path to reference .wav
        sample_text:  exact transcript of sample_voice
        text:         text to synthesize (long text auto-splits into sentences)
        out_dir:      folder to write the output into (created if missing)
        out_name:     filename for the merged output
        pause_ms:     silence inserted between sentences
        speed:        0.5-2.0 (non-streaming only)
        seed:         optional int for reproducibility

    Returns:
        absolute path of the generated .wav
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(out_dir) / out_name

    if seed is not None:
        from cosyvoice.utils.common import set_all_random_seed
        set_all_random_seed(seed)

    # CosyVoice3 expects the assistant preamble
    prompt_text = (
        f'You are a helpful assistant.<|endofprompt|>{sample_text}'
        if getattr(engine, '_is_v3', False) else sample_text
    )

    chunks = []
    silence = torch.zeros(1, int(engine.sample_rate * pause_ms / 1000))

    for out in engine.inference_zero_shot(
            text, prompt_text, sample_voice, stream=False, speed=speed):
        chunks.append(out['tts_speech'])
        chunks.append(silence)

    if chunks:
        chunks.pop()  # drop trailing silence
    full = torch.cat(chunks, dim=1)

    torchaudio.save(str(out_path), full, engine.sample_rate)
    duration = full.shape[1] / engine.sample_rate
    print(f'[ok] {out_path.name}  ({duration:.2f}s)')
    return str(out_path.resolve())
