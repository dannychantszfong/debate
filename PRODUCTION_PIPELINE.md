# Debate Production Pipeline

This repo is structured so the debate-to-video chain can run from this repo
alone: debate logs, transcript cleanup, TTS script generation, CosyVoice audio,
Whisper timing verification, and Remotion video rendering.

There are no runtime code dependencies on sibling folders like `G:\Coding\01_AI-ML\TTS` or `G:\Coding\10_Creative\remotion`.

## Runtime Contract

What this repo now guarantees:

- all pipeline code lives inside this repo
- the active workstation runtime is one Conda env named `debate`
- downloaded model weights live under repo-local `.cache/`
- rendered outputs live under repo-local `output/`
- Remotion lives under repo-local `pipeline/video/remotion/`
- local machine paths live in ignored `pipeline.config.local.json`

What a fresh machine still needs before setup/rebuild can run:

- Git
- Conda
- Python `3.10` compatibility for CosyVoice and llama-cpp-python
- CUDA-capable NVIDIA stack if local GPU inference/TTS is required
- Windows PowerShell

What GitHub will not contain:

- large model weights such as GGUF and CosyVoice checkpoints
- `node_modules`
- generated topics, logs, transcripts, TTS scripts, run records, timing JSON,
  audio, and video outputs
- local voice packs under `assets/voices/`, because they may contain
  private/licensed voice samples
- rendered outputs

Those are intentionally local and can be recreated by the environment/bootstrap
steps when needed.

## Quick Start

On this workstation:

```powershell
cd G:\Coding\01_AI-ML\LLM\debate
conda activate debate
python dashboard_app.py
```

Open `http://127.0.0.1:7861` for the local dashboard. It wraps the same pipeline
commands below, but gives a visual entry point for selecting sources, starting
or stopping a run, watching progress, tailing logs, and opening artifacts.

Dashboard behavior:

- Choose an entry tab, then use `Run until` to run only the needed stage range
  (`topic`, `log`, `transcript`, `tts`, `audio`, or `video`).
- Setup controls lock while a job is running, so another tab cannot accidentally
  start or mutate the active run.
- The progress panel shows the selected stage flow, current stage, live log,
  command, and produced artifacts.
- TTS config includes voice-pack selection and a short voice-preview generator.
  Voice packs are discovered under `assets/voices/<pack>/host`,
  `assets/voices/<pack>/positive`, and `assets/voices/<pack>/negative`.
- Video config includes a layout selector with an immediate 16:9 layout preview.

For scripted runs:

```powershell
cd G:\Coding\01_AI-ML\LLM\debate
conda activate debate
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

If you need to create a new debate log from a topic first, run:

```powershell
python debate_pipeline.py from-topic --topic-file topics\my_topic.md --turns 3 --provider local --layout dual --port 8099
```

If you only have the raw debate topic text, `from-topic --topic` first runs
`debate_topic_generator.py`, writes a topic framework under `topics/`, and then
passes that generated markdown file into `debate.py`:

```powershell
python debate_pipeline.py from-topic --topic "当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。" --turns 3 --provider local --layout dual --port 8099
```

For debate-log generation only:

```powershell
python debate.py --provider local --topic-file topics\my_topic.md --turns 3
```

Then continue from the latest generated log if you did not use `from-topic`:

```powershell
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

## API Providers

Set the provider key in the same activated environment, then choose the provider
at runtime:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
python debate_pipeline.py from-log --log latest --provider openrouter --layout dual --port 8099
```

Supported debate providers are listed by `python debate.py --help`.

## What The Unified Env Contains

Python:

- local debate scripts
- transcript humanization tools
- TTS pipeline dependencies
- CosyVoice runtime dependencies
- `llama-cpp-python` for local GGUF inference
- OpenAI, Anthropic, Gemini, and OpenRouter compatible API clients
- Whisper for TTS timing verification

Node:

- the standalone Remotion renderer under `pipeline/video/remotion`

Models:

- default local debate LLM:
  - `Qwen/Qwen2.5-3B-Instruct-GGUF`
  - file: `qwen2.5-3b-instruct-q4_k_m.gguf`
- default TTS model:
  - `FunAudioLLM/Fun-CosyVoice3-0.5B-2512`

## Main commands

From the latest debate log:

```powershell
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

Stop after an intermediate stage when you are iterating:

```powershell
python debate_pipeline.py from-topic --topic-file topics\my_topic.md --turns 3 --provider local --stop-after transcript
python debate_pipeline.py from-tts --tts-script latest --voice-root assets\voices\default --stop-after audio
```

Transcript shaping:

- `json_to_transcript.py` keeps opening and closing speeches as larger
  structured statements.
- Free-debate turns are split by default into multiple shorter transcript
  entries, so one long written turn can become several spoken back-and-forth
  turns.
- Split free-debate chunks from the same original turn are interleaved by
  default, so positive/negative chunks alternate instead of playing as one
  speaker block followed by the other.
- Interleaved free-debate chunks are then rewritten against the previous
  opponent chunk by default. This second pass is what turns formal alternation
  into actual clash: each short turn should pick up a keyword, premise, or
  question from the previous speaker before advancing its own point.
- A short host bridge is inserted before the first free-debate exchange.
- To keep the old one-entry-per-written-turn behavior, run
  `json_to_transcript.py ... --no-split-free-debate`.
- To keep split chunks but disable positive/negative interleaving, run
  `json_to_transcript.py ... --no-interleave-free-debate`.
- To keep split/interleaved chunks but skip the second-pass clash rewrite, run
  `json_to_transcript.py ... --no-rewrite-free-debate-exchanges`.

From an existing transcript:

```powershell
python debate_pipeline.py from-transcript --transcript latest --provider local --layout dual --port 8099
```

From an existing TTS script:

```powershell
python debate_pipeline.py from-tts --tts-script latest --layout dual --port 8099
```

Video only from an existing timing JSON:

```powershell
python debate_pipeline.py video --timeline latest --layout podcast --port 8099
```

## Layouts

Available layouts:

- `dual`
- `podcast`
- `mindmap`

Example:

```powershell
python debate_pipeline.py from-tts --tts-script latest --layout mindmap --port 8099
```

## Useful render flags

These pass through to the Remotion renderer:

- `--plan <video-plan.json>`
- `--audio <audio.wav>`
- `--out <video.mp4>`
- `--max-seconds 120`
- `--concurrency 75%`
- `--gl angle`
- `--port 8090`
- `--keep-bundle`
- `--keep-staged-audio`

Example:

```powershell
python debate_pipeline.py video --timeline latest --layout dual --concurrency 75% --gl angle --port 8099
```

## Config files

`pipeline.config.json`

- portable repo defaults
- safe to commit

`pipeline.config.example.json`

- committed example of the portable defaults
- useful if you want to compare your local overrides against the baseline

`pipeline.config.local.json`

- machine-local overrides, usually copied from
  `pipeline.config.local.example.json` and adjusted by hand
- ignored by Git
- expected place for:
  - local Python path overrides
  - custom Node package manager path
  - custom model source paths
- current local version should point Python, Node, and npm at the Conda `debate`
  env

## Files and directories

- `debate.py`, `clean_logs.py`, `json_to_transcript.py`, `transcript_to_tts.py`
  - main debate and transcript stages
- `pipeline/tts/`
  - self-contained debate audio generation
- `pipeline/video/remotion/`
  - standalone Remotion renderer
- `third_party/CosyVoice/`
  - vendored CosyVoice runtime code
- `third_party/Matcha-TTS/`
  - vendored Matcha-TTS dependency
- `assets/voices/<pack>/`
  - local-only voice packs for `positive`, `negative`, and `host`
- `.cache/`
  - downloaded or bootstrapped models
- `output/audio/`
  - merged WAV and timing JSON
- `output/video/`
  - rendered MP4 outputs

## Notes

- The local install targets Python `3.10` because that is the safest packaged
  path for CosyVoice and `llama-cpp-python`.
- The Conda `debate` env is the preferred active development path.
- Bootstrap directs Hugging Face and ModelScope caches into repo-local `.cache/`
  instead of defaulting to user-profile cache locations.
- The old `.venv` bootstrap helper and split Torch requirements files have been
  removed. Keep future environment work centered on `ENVIRONMENT.md` and the
  Conda `debate` env.

For exact environment setup and verification, see [ENVIRONMENT.md](./ENVIRONMENT.md).
