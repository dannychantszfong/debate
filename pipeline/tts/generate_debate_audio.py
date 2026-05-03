"""
Generate a multi-voice debate audio track from a tagged debate transcript JSON.

This is the self-contained debate-repo version of the CosyVoice debate renderer.
It reads from `tts_scripts/*.json`, uses repo-local voice packs and model paths from
`pipeline.config.json`, and writes a merged WAV plus subtitle-ready timing JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
import torchaudio

from pipeline.tts.tts_lib import load_engine, load_voice_pack
from pipeline_config import get_tts_config

TTS_CONFIG = get_tts_config()
MODEL_DIR = TTS_CONFIG["model_dir"]
SPEAKER_VOICES: dict[str, Path] = {
    speaker: Path(directory) for speaker, directory in TTS_CONFIG["speaker_dirs"].items()
}
OUT_ROOT = Path(TTS_CONFIG["output_dir"])
INTER_TURN_PAUSE_MS = int(TTS_CONFIG["inter_turn_pause_ms"])
INTRA_TURN_PAUSE_MS = int(TTS_CONFIG["intra_turn_pause_ms"])

# ---- Whisper verification ----
VERIFY_WITH_WHISPER = bool(TTS_CONFIG["verify_with_whisper"])
WHISPER_MODEL_NAME = TTS_CONFIG["whisper_model_name"]
WHISPER_MODEL_DIR = Path(TTS_CONFIG["whisper_model_dir"])
WHISPER_LANGUAGE = TTS_CONFIG["whisper_language"]
CER_THRESHOLD = float(TTS_CONFIG["cer_threshold"])
MIN_CHARS_TO_VERIFY = int(TTS_CONFIG["min_chars_to_verify"])
PRIMARY_ATTEMPTS = int(TTS_CONFIG["primary_attempts"])
FALLBACK_ATTEMPTS_PER_VOICE = int(TTS_CONFIG["fallback_attempts_per_voice"])
MAX_FALLBACK_VOICES = int(TTS_CONFIG["max_fallback_voices"])
BASE_SEED = int(TTS_CONFIG["base_seed"])
# -------------------------------

SUPPORTED_TAGS = {
    "[breath]", "[noise]", "[laughter]", "[cough]", "[clucking]", "[accent]",
    "[quick_breath]", "[hissing]", "[sigh]", "[vocalized-noise]",
    "[lipsmack]", "[mn]",
}
TAG_RE = re.compile(r"\[[^\]]+\]")

def clean_text(t: str) -> str:
    def _keep_or_drop(m):
        tag = m.group(0).lower()
        return tag if tag in SUPPORTED_TAGS else ""
    t = TAG_RE.sub(_keep_or_drop, t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def first_voice(pack: dict):
    if not pack:
        raise RuntimeError("empty voice pack")
    key = sorted(pack.keys())[0]
    return key, pack[key]

# ----- CER utilities -----

_STRIP_CHARS = set(
    "。，、；：？！“”‘’「」『』（）《》【】…·～—－ｰ"
    "\".,;:?!()[]{}<>-_*#&%$@/\\=+`~"
    "…—–"
)

def normalize_for_cer(s: str) -> str:
    s = TAG_RE.sub("", s or "")
    s = s.lower()
    out = []
    for c in s:
        if c.isspace() or c in _STRIP_CHARS:
            continue
        out.append(c)
    return "".join(out)

def cer(ref: str, hyp: str) -> float:
    """Character Error Rate on pre-normalized strings."""
    if not ref and not hyp:
        return 0.0
    if not ref:
        return 1.0
    m, n = len(ref), len(hyp)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        ri = ref[i - 1]
        for j in range(1, n + 1):
            if ri == hyp[j - 1]:
                cur[j] = prev[j - 1]
            else:
                cur[j] = 1 + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur
    return prev[n] / m

# ----- Whisper wrapper -----

class WhisperVerifier:
    def __init__(self, model_name: str, model_dir: Path, language: str):
        import whisper as whisper_pkg
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_dir.mkdir(parents=True, exist_ok=True)
        available = set(whisper_pkg.available_models())
        resolved_model_name = model_name
        if resolved_model_name not in available:
            fallback_order = ["small", "medium", "base", "tiny", "large-v3", "large-v2", "large-v1"]
            for fallback in fallback_order:
                if fallback in available:
                    print(
                        f"[whisper] requested model '{model_name}' is unavailable; "
                        f"falling back to '{fallback}'"
                    )
                    resolved_model_name = fallback
                    break
            else:
                raise RuntimeError(
                    f"Model {model_name} not found; available models = {sorted(available)}"
                )
        print(f"[whisper] loading {resolved_model_name} on {device}")
        self.model = whisper_pkg.load_model(
            resolved_model_name,
            device=device,
            download_root=str(model_dir),
        )
        self.device = device
        self.language = language
        self.model_name = resolved_model_name

    def _transcribe_raw(self, wav_path: str) -> dict:
        return self.model.transcribe(
            wav_path,
            language=self.language,
            task="transcribe",
            fp16=(self.device == "cuda"),
            verbose=False,
            condition_on_previous_text=False,
            # No initial_prompt — must not bias the hypothesis.
        )

    def transcribe(self, wav_path: str) -> str:
        return (self._transcribe_raw(wav_path).get("text") or "").strip()

    def transcribe_segments(self, wav_path: str) -> list[dict]:
        """Return [{start, end, text}] in audio-local time."""
        result = self._transcribe_raw(wav_path)
        segs = []
        for s in result.get("segments", []):
            segs.append({
                "start": float(s.get("start", 0.0)),
                "end":   float(s.get("end",   0.0)),
                "text":  (s.get("text") or "").strip(),
            })
        return segs

# ----- sentence synthesis primitive -----

def _synth_one_sentence(engine, sentence: str, prompt_text: str,
                        sample_voice: str, seed: int) -> torch.Tensor:
    """One inference pass for one sentence; returns a mono tensor [1, T]."""
    from cosyvoice.utils.common import set_all_random_seed
    set_all_random_seed(seed)
    # text_frontend=False → don't re-split, don't re-normalize.
    chunks = []
    for out in engine.inference_zero_shot(
            sentence, prompt_text, sample_voice,
            stream=False, speed=1.0, text_frontend=False):
        chunks.append(out['tts_speech'])
    if not chunks:
        return torch.zeros(1, 0)
    return torch.cat(chunks, dim=1)

def _assemble(wavs: list[torch.Tensor], sr: int, pause_ms: int):
    """
    Concatenate per-sentence wavs with silence between (not after the last).
    Returns (full_wav, boundaries) where boundaries[i] = (start_sec, end_sec).
    """
    silence_n = int(sr * pause_ms / 1000)
    pause_s = pause_ms / 1000.0
    silence = torch.zeros(1, silence_n) if silence_n > 0 else None

    chunks = []
    boundaries = []
    cursor = 0.0
    for i, w in enumerate(wavs):
        dur = w.shape[1] / sr
        boundaries.append((cursor, cursor + dur))
        chunks.append(w)
        cursor += dur
        if i < len(wavs) - 1 and silence is not None:
            chunks.append(silence)
            cursor += pause_s
    full = torch.cat(chunks, dim=1) if chunks else torch.zeros(1, 0)
    return full, boundaries

def _align_whisper_to_sentences(whisper_segs: list[dict],
                                 boundaries: list[tuple[float, float]]) -> list[str]:
    """
    For each our-sentence boundary, collect Whisper segments whose midpoint
    falls inside [start, end]. Concatenate their text. Returns per-sentence hyp.
    """
    hyps = [""] * len(boundaries)
    for wseg in whisper_segs:
        mid = 0.5 * (wseg["start"] + wseg["end"])
        for i, (s, e) in enumerate(boundaries):
            if s <= mid <= e:
                hyps[i] = (hyps[i] + wseg["text"]).strip() if hyps[i] else wseg["text"]
                break
    return hyps

# ----- turn synthesis with hybrid verification -----

def _build_prompt_text(engine, sample_text: str) -> str:
    return (f'You are a helpful assistant.<|endofprompt|>{sample_text}'
            if getattr(engine, '_is_v3', False) else sample_text)

def _phase1_generate(engine, voice_samples: list[dict], text: str,
                     base_seed: int) -> dict:
    """
    Phase 1 only — synthesise all sentences with the PRIMARY voice.
    Pure TTS, no Whisper. Returns everything the verify-and-assemble
    step needs, so this step can run on one thread while the next
    turn's Phase 1 runs on another.
    """
    if not voice_samples:
        raise ValueError("voice_samples must be non-empty")
    primary = voice_samples[0]
    fallbacks = voice_samples[1:1 + MAX_FALLBACK_VOICES]

    sentences = list(engine.frontend.text_normalize(text, split=True, text_frontend=True))
    n = len(sentences)
    seeds = [base_seed + i * 1009 for i in range(n)]
    sent_wavs: list[torch.Tensor] = []
    for i, s in enumerate(sentences):
        sent_wavs.append(_synth_one_sentence(
            engine, s, primary["prompt_text"], primary["wav"], seeds[i]))
    return {
        "primary":   primary,
        "fallbacks": fallbacks,
        "sentences": sentences,
        "seeds":     seeds,
        "sent_wavs": sent_wavs,
        "base_seed": base_seed,
    }

def _verify_and_assemble(engine, phase1: dict, part_wav_path: Path,
                         pause_ms: int, verifier: WhisperVerifier | None) -> dict:
    """
    Phases 2 + 3 + 4. Consumes a _phase1_generate result.
      Phase 2: single Whisper pass on the assembled turn, aligned back to sentences.
               Sentences shorter than MIN_CHARS_TO_VERIFY are auto-accepted.
      Phase 3: for failed sentences, retry primary voice up to (PRIMARY_ATTEMPTS-1)
               more times, then rotate through fallback voices.
      Phase 4: reassemble with the winning per-sentence wavs and save the part.
    """
    primary   = phase1["primary"]
    fallbacks = phase1["fallbacks"]
    sentences = phase1["sentences"]
    seeds     = phase1["seeds"]
    sent_wavs = list(phase1["sent_wavs"])   # local copy; we may swap entries
    base_seed = phase1["base_seed"]
    n = len(sentences)
    sr = engine.sample_rate

    # Per-sentence tracking
    cers        = [0.0] * n
    hyps        = [""] * n
    accepted    = [True] * n
    voice_ranks = [0] * n
    voice_uids  = [primary["uid"]] * n
    attempts_log: list[list[dict]] = [[] for _ in range(n)]

    tmp_dir = Path(tempfile.mkdtemp(prefix="ttsverify_"))
    auto_accepted = 0
    try:
        if verifier is not None:
            # ----- Phase 2: turn-level verification -----
            full_wav, bounds = _assemble(sent_wavs, sr, pause_ms)
            probe_path = tmp_dir / "turn_probe.wav"
            torchaudio.save(str(probe_path), full_wav, sr)
            wsegs = verifier.transcribe_segments(str(probe_path))
            hyps  = _align_whisper_to_sentences(wsegs, bounds)

            for i, s in enumerate(sentences):
                ref_norm = normalize_for_cer(s)
                if len(ref_norm) < MIN_CHARS_TO_VERIFY:
                    # too short to produce a meaningful CER — accept unconditionally
                    auto_accepted += 1
                    cers[i] = 0.0
                    accepted[i] = True
                    attempts_log[i].append({
                        "attempt": 0, "seed": seeds[i],
                        "voice_rank": 0, "voice_uid": primary["uid"],
                        "cer": 0.0,
                        "whisper_text": hyps[i],
                        "source": "auto-accept-short",
                    })
                    continue
                cer_val = cer(ref_norm, normalize_for_cer(hyps[i]))
                cers[i] = cer_val
                attempts_log[i].append({
                    "attempt": 0, "seed": seeds[i],
                    "voice_rank": 0, "voice_uid": primary["uid"],
                    "cer": round(cer_val, 4),
                    "whisper_text": hyps[i],
                    "source": "aligned",
                })
                accepted[i] = cer_val <= CER_THRESHOLD

            bad = [i for i, ok in enumerate(accepted) if not ok]
            if auto_accepted:
                print(f"       [skip  ] {auto_accepted}/{n} short sentences auto-accepted")
            if bad:
                print(f"       [verify] {len(bad)}/{n} sentences failed first pass (CER > {CER_THRESHOLD})")

            # ----- Phase 3: per-sentence retries with voice fallback -----
            for i in bad:
                best_cer  = cers[i]
                best_wav  = sent_wavs[i]
                best_hyp  = hyps[i]
                best_rank = 0
                best_uid  = primary["uid"]
                attempt_counter = 0

                stopped = False
                voice_plan = [(0, primary, PRIMARY_ATTEMPTS - 1)]  # -1 because Phase-1 used 1
                for rank, vs in enumerate(fallbacks, start=1):
                    voice_plan.append((rank, vs, FALLBACK_ATTEMPTS_PER_VOICE))

                for rank, v, tries_for_this_voice in voice_plan:
                    if stopped:
                        break
                    for r in range(tries_for_this_voice):
                        attempt_counter += 1
                        new_seed = base_seed + i * 1009 + rank * 10007 + r + 1
                        wav_try = _synth_one_sentence(
                            engine, sentences[i], v["prompt_text"], v["wav"], new_seed)
                        single_path = tmp_dir / f"retry_{i:04d}_v{rank}_{r}.wav"
                        torchaudio.save(str(single_path), wav_try, sr)
                        hyp_try = verifier.transcribe(str(single_path))
                        cer_try = cer(normalize_for_cer(sentences[i]), normalize_for_cer(hyp_try))

                        tag = "primary" if rank == 0 else f"fb#{rank}"
                        attempts_log[i].append({
                            "attempt": attempt_counter,
                            "voice_rank": rank, "voice_uid": v["uid"],
                            "seed": new_seed,
                            "cer": round(cer_try, 4),
                            "whisper_text": hyp_try,
                            "source": "solo",
                        })

                        if cer_try < best_cer:
                            best_cer, best_wav, best_hyp = cer_try, wav_try, hyp_try
                            best_rank, best_uid = rank, v["uid"]

                        if cer_try <= CER_THRESHOLD:
                            print(f"       [ok   ] s{i:03d} {tag} try={r+1} cer={cer_try:.3f}")
                            stopped = True
                            break
                        else:
                            print(f"       [retry] s{i:03d} {tag} try={r+1} cer={cer_try:.3f}")

                sent_wavs[i]   = best_wav
                cers[i]        = best_cer
                hyps[i]        = best_hyp
                accepted[i]    = best_cer <= CER_THRESHOLD
                voice_ranks[i] = best_rank
                voice_uids[i]  = best_uid
                if not accepted[i]:
                    print(f"       [warn ] s{i:03d} gave up, best cer={best_cer:.3f} "
                          f"(voice rank={best_rank}, uid={best_uid})")
    finally:
        try:
            for p in tmp_dir.glob("*"):
                p.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except Exception:
            pass

    # ----- Phase 4: final assembly -----
    final_wav, final_bounds = _assemble(sent_wavs, sr, pause_ms)
    torchaudio.save(str(part_wav_path), final_wav, sr)
    total_dur = final_wav.shape[1] / sr
    print(f"[ok ] {part_wav_path.name}  ({total_dur:.2f}s, {n} sentences)")

    fallback_used = sum(1 for r in voice_ranks if r > 0)
    if fallback_used:
        print(f"       [voice] {fallback_used}/{n} sentences used a fallback voice")

    segments = []
    for i, s in enumerate(sentences):
        seg = {
            "text": s,
            "start": round(final_bounds[i][0], 3),
            "end":   round(final_bounds[i][1], 3),
            "voice_rank": voice_ranks[i],
            "voice_uid":  voice_uids[i],
        }
        if verifier is not None:
            seg.update({
                "cer": round(cers[i], 4),
                "whisper_text": hyps[i],
                "accepted": bool(accepted[i]),
                "attempts": attempts_log[i],
            })
        segments.append(seg)

    return {
        "sample_rate": sr,
        "duration": round(total_dur, 3),
        "pause_ms": pause_ms,
        "verified": verifier is not None,
        "cer_threshold": CER_THRESHOLD if verifier is not None else None,
        "primary_voice_uid": primary["uid"],
        "fallback_voice_uids": [v["uid"] for v in fallbacks],
        "fallback_sentences": fallback_used,
        "auto_accepted_short": auto_accepted,
        "segments": segments,
    }

def synthesize_turn(engine, voice_samples: list[dict], text,
                    part_wav_path: Path, pause_ms: int,
                    verifier: WhisperVerifier | None,
                    base_seed: int) -> dict:
    """Serial path: Phase 1 then Phase 2+3+4 on the same thread."""
    phase1 = _phase1_generate(engine, voice_samples, text, base_seed)
    print(f"       {len(phase1['sentences'])} sentences | "
          f"primary={phase1['primary']['uid']} | fallbacks={len(phase1['fallbacks'])}")
    return _verify_and_assemble(engine, phase1, part_wav_path, pause_ms, verifier)

# ----- main -----

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--json",
        required=True,
        help="Path to a tts_scripts JSON file.",
    )
    parser.add_argument(
        "--model-dir",
        default=MODEL_DIR,
        help=f"CosyVoice model directory (default: {MODEL_DIR})",
    )
    parser.add_argument(
        "--out-dir",
        default=str(OUT_ROOT),
        help=f"Output directory for merged WAV + timing JSON (default: {OUT_ROOT})",
    )
    parser.add_argument(
        "--skip-whisper",
        action="store_true",
        help="Disable Whisper verification and retry logic.",
    )
    parser.add_argument(
        "--voice-root",
        default=None,
        help="Voice pack root containing host/positive/negative subfolders.",
    )
    parser.add_argument("--host-voice-dir", default=None, help="Override host voice directory.")
    parser.add_argument("--positive-voice-dir", default=None, help="Override positive voice directory.")
    parser.add_argument("--negative-voice-dir", default=None, help="Override negative voice directory.")
    return parser.parse_args()


def main():
    start_time = time.time()
    args = parse_args()
    json_path = Path(args.json).expanduser().resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"Missing --json file: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8-sig"))
    turns = data["transcript"]

    model_dir = Path(args.model_dir).expanduser().resolve()
    out_root = Path(args.out_dir).expanduser().resolve()
    out_stem = json_path.stem
    merged_path = out_root / f"{out_stem}.wav"
    merged_meta_path = out_root / f"{out_stem}.json"
    parts_dir = out_root / f"{out_stem}_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[info] loading engine: {model_dir}")
    engine = load_engine(str(model_dir))

    verifier = None
    verify_with_whisper = VERIFY_WITH_WHISPER and not args.skip_whisper
    if verify_with_whisper:
        verifier = WhisperVerifier(WHISPER_MODEL_NAME, WHISPER_MODEL_DIR, WHISPER_LANGUAGE)

    # Resolve every configured speaker's reference voice(s) up front.
    # Samples are ordered: primary first, fallbacks (alphabetically) after.
    speaker_voices: dict[str, Path] = dict(SPEAKER_VOICES)
    if args.voice_root:
        voice_root = Path(args.voice_root).expanduser().resolve()
        speaker_voices.update({
            "host": voice_root / "host",
            "positive": voice_root / "positive",
            "negative": voice_root / "negative",
        })
    for speaker, override in (
        ("host", args.host_voice_dir),
        ("positive", args.positive_voice_dir),
        ("negative", args.negative_voice_dir),
    ):
        if override:
            speaker_voices[speaker] = Path(override).expanduser().resolve()

    voice_by_speaker: dict[str, dict] = {}
    for spk, vdir in speaker_voices.items():
        print(f"[info] {spk} voice dir: {vdir}")
        pack = load_voice_pack(str(vdir))
        if not pack:
            raise RuntimeError(f"empty voice pack for speaker {spk!r}: {vdir}")
        samples = []
        for key in sorted(pack.keys()):
            wav, txt = pack[key]
            samples.append({
                "uid": key,
                "wav": wav,
                "txt": txt,
                "prompt_text": _build_prompt_text(engine, txt),
            })
        voice_by_speaker[spk] = {"dir": vdir, "samples": samples}
        fb_count = min(len(samples) - 1, MAX_FALLBACK_VOICES)
        print(f"[info] {spk} primary={samples[0]['uid']}  (+{fb_count} fallback"
              f"{'s' if fb_count != 1 else ''} available)")

    part_entries = []
    seen_speakers = set()

    for i, turn in enumerate(turns, start=1):
        speaker = turn["speaker"]
        seen_speakers.add(speaker)
        raw = turn.get("content", "")
        text = clean_text(raw)
        if not text:
            print(f"[skip] turn {i}: empty after cleaning")
            continue

        part_name = f"{i:02d}_{speaker}.wav"
        part_path = parts_dir / part_name
        part_meta_path = part_path.with_suffix(".json")

        if part_path.exists() and part_meta_path.exists():
            print(f"[cache] turn {i} ({speaker}) -> {part_path.name}")
            meta = json.loads(part_meta_path.read_text(encoding="utf-8"))
        else:
            if speaker not in voice_by_speaker:
                raise ValueError(
                    f"unknown speaker on turn {i}: {speaker!r}. "
                    "Add it to pipeline.config.json under tts.speaker_dirs."
                )
            v = voice_by_speaker[speaker]
            print(f"[gen ] turn {i}/{len(turns)} ({speaker}), {len(text)} chars, "
                  f"{len(v['samples'])} voice sample(s) in pack")
            turn_seed = BASE_SEED + i * 100003
            meta = synthesize_turn(
                engine=engine,
                voice_samples=v["samples"],
                text=text,
                part_wav_path=part_path,
                pause_ms=INTRA_TURN_PAUSE_MS,
                verifier=verifier,
                base_seed=turn_seed,
            )
            part_meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        part_entries.append((part_path, meta, speaker, i, text))

    unknown = seen_speakers - set(speaker_voices.keys())
    if unknown:
        print(f"[warn] speakers seen in JSON but not configured: {sorted(unknown)}")

    # ---- merge wavs + build final subtitle-ready metadata ----
    print(f"[info] merging {len(part_entries)} parts -> {merged_path.name}")
    sr = engine.sample_rate
    inter_silence = torch.zeros(1, int(sr * INTER_TURN_PAUSE_MS / 1000))
    inter_pause_s = INTER_TURN_PAUSE_MS / 1000.0

    chunks = []
    all_segments = []
    turn_summary = []
    global_cursor = 0.0

    for (part_path, meta, speaker, turn_i, text) in part_entries:
        w, file_sr = torchaudio.load(str(part_path))
        if file_sr != sr:
            w = torchaudio.functional.resample(w, file_sr, sr)
        if w.shape[0] > 1:
            w = w.mean(dim=0, keepdim=True)

        turn_start = global_cursor
        for seg in meta.get("segments", []):
            seg_out = {
                "turn": turn_i,
                "speaker": speaker,
                "text": seg["text"],
                "start": round(turn_start + seg["start"], 3),
                "end":   round(turn_start + seg["end"], 3),
            }
            for k in ("cer", "whisper_text", "accepted", "voice_rank", "voice_uid"):
                if k in seg:
                    seg_out[k] = seg[k]
            all_segments.append(seg_out)

        part_dur = w.shape[1] / sr
        turn_summary.append({
            "turn": turn_i,
            "speaker": speaker,
            "start": round(turn_start, 3),
            "end":   round(turn_start + part_dur, 3),
            "duration": round(part_dur, 3),
            "content": text,
        })

        chunks.append(w)
        global_cursor = turn_start + part_dur
        chunks.append(inter_silence)
        global_cursor += inter_pause_s

    if chunks:
        chunks.pop()
        global_cursor -= inter_pause_s

    full = torch.cat(chunks, dim=1)
    torchaudio.save(str(merged_path), full, sr)
    total_dur = full.shape[1] / sr
    print(f"[done] {merged_path}  ({total_dur:.2f}s)")

    # QA summary
    verified_segs = [s for s in all_segments if "cer" in s]
    qa = None
    if verified_segs:
        cers = [s["cer"] for s in verified_segs]
        rejected = [s for s in verified_segs if s.get("accepted") is False]
        qa = {
            "segments_checked": len(verified_segs),
            "mean_cer": round(sum(cers) / len(cers), 4),
            "max_cer": round(max(cers), 4),
            "rejected_count": len(rejected),
            "cer_threshold": CER_THRESHOLD,
        }
        print(f"[qa  ] mean CER={qa['mean_cer']:.3f}  max CER={qa['max_cer']:.3f}  "
              f"rejected={qa['rejected_count']}/{qa['segments_checked']}")

    voices_meta = {
        spk: {
            "dir": str(v["dir"]),
            "primary_uid":   v["samples"][0]["uid"],
            "fallback_uids": [s["uid"] for s in v["samples"][1:1 + MAX_FALLBACK_VOICES]],
            "total_available": len(v["samples"]),
        }
        for spk, v in voice_by_speaker.items()
    }

    final_meta = {
        "audio": str(merged_path.resolve()),
        "audio_file": merged_path.name,
        "source_json": str(json_path.resolve()),
        "topic": data.get("topic", ""),
        "sample_rate": sr,
        "duration": round(total_dur, 3),
        "voices": voices_meta,
        "inter_turn_pause_ms": INTER_TURN_PAUSE_MS,
        "intra_turn_pause_ms": INTRA_TURN_PAUSE_MS,
        "whisper": {
            "enabled": verify_with_whisper,
            "model": verifier.model_name if verify_with_whisper and verifier else None,
            "primary_attempts": PRIMARY_ATTEMPTS if verify_with_whisper else None,
            "fallback_attempts_per_voice": FALLBACK_ATTEMPTS_PER_VOICE if verify_with_whisper else None,
            "max_fallback_voices": MAX_FALLBACK_VOICES if verify_with_whisper else None,
            "cer_threshold": CER_THRESHOLD if verify_with_whisper else None,
            "strategy": "hybrid + voice-fallback (primary retries -> rotate voice sample)" if verify_with_whisper else None,
        },
        "qa": qa,
        "turns": turn_summary,
        "segments": all_segments,
    }
    merged_meta_path.write_text(
        json.dumps(final_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[done] {merged_meta_path}  ({len(all_segments)} subtitle segments)")

    end_time = time.time()
    print("Used time:", str(end_time - start_time))

if __name__ == "__main__":
    main()
