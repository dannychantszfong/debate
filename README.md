# Debate Studio

Debate Studio is a local, end-to-end debate-to-video production pipeline. It
starts from a raw debate topic or topic framework, generates a structured
debate, reshapes the written debate into a spoken transcript, generates
multi-speaker CosyVoice audio, verifies timing with Whisper, and renders a
Remotion video.

This repository is now standalone. It was originally developed inside a larger
`LLM` workspace with several sibling projects and separate Conda environments.
The current goal of this repo is to keep the whole production chain in one
place, with one local runtime and one dashboard.

## Current Status

This is a workstation-oriented project rather than a plug-and-play hosted
service. It has been tested on a local Windows machine with a CUDA-capable
NVIDIA GPU and a unified Conda environment named `debate`.

The framework is functional:

- topic/topic-framework generation
- local or API-backed debate generation
- debate-log cleanup
- transcript reshaping for spoken delivery
- free-debate splitting, interleaving, and clash rewrite
- TTS script generation with speaking tags
- CosyVoice audio generation
- optional Whisper timing verification
- Remotion video rendering
- local dashboard for staged pipeline runs

There are still rough edges. Progress is currently inferred from logs, the
dashboard stores job state in memory, voice-pack management is local and simple,
and the Remotion layout preview is schematic rather than a full render preview.

## Pipeline

The intended production flow is:

```text
raw topic
  -> topic framework
  -> debate log
  -> cleaned log
  -> audience-facing transcript
  -> TTS script
  -> WAV + timing JSON
  -> MP4 video
```

The main orchestrator is `debate_pipeline.py`. It supports full runs and partial
runs so you can iterate from any stage without regenerating everything.

Important stages:

- `debate_topic_generator.py` creates a structured topic framework.
- `debate.py` generates the formal debate log.
- `clean_logs.py` normalizes generated debate logs.
- `json_to_transcript.py` converts formal debate text into spoken, audience
  oriented turns.
- `transcript_to_tts.py` inserts TTS-friendly speaking tags.
- `pipeline/tts/generate_debate_audio.py` generates multi-speaker audio and
  timing metadata.
- `pipeline/video/remotion/` renders the final video.

## Dashboard

The easiest local entry point is the dashboard:

```powershell
conda activate debate
python dashboard_app.py
```

Open:

```text
http://127.0.0.1:7861
```

The dashboard can:

- choose the pipeline entry point: Topic, Log, Transcript, TTS, or Video
- choose where a run should stop with `Run until`
- start and stop local jobs
- lock setup controls while a job is running
- show stage progress, command output, live logs, and artifacts
- select a local voice pack
- generate a short TTS voice preview from custom text
- preview the broad shape of available video layouts

## CLI Examples

Run from raw topic text:

```powershell
python debate_pipeline.py from-topic `
  --topic "当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。" `
  --turns 3 `
  --provider local `
  --layout dual `
  --port 8099
```

Run from an existing topic framework:

```powershell
python debate_pipeline.py from-topic `
  --topic-file topics\my_topic.md `
  --turns 3 `
  --provider local `
  --layout dual `
  --port 8099
```

Continue from the latest debate log:

```powershell
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

Stop after an intermediate stage:

```powershell
python debate_pipeline.py from-topic --topic-file topics\my_topic.md --turns 3 --provider local --stop-after transcript
python debate_pipeline.py from-tts --tts-script latest --voice-root assets\voices\default --stop-after audio
```

Render video only from an existing timing JSON:

```powershell
python debate_pipeline.py video --timeline latest --layout podcast --port 8099
```

## Runtime Expectations

The canonical local runtime is a single Conda environment named `debate`.

The verified workstation runtime includes:

- Python `3.10`
- CUDA-enabled PyTorch and torchaudio
- CUDA-enabled `llama-cpp-python`
- CosyVoice dependencies
- Whisper
- Node/npm for Remotion
- API SDKs for OpenAI, Anthropic, Gemini, and OpenRouter-compatible providers

See [ENVIRONMENT.md](./ENVIRONMENT.md) for the exact verified local versions,
CUDA llama-cpp notes, and rebuild commands.

## Configuration

Portable defaults live in:

```text
pipeline.config.json
pipeline.config.example.json
pipeline.config.local.example.json
```

Machine-specific overrides belong in:

```text
pipeline.config.local.json
```

`pipeline.config.local.json` is intentionally ignored by Git. Use it for local
Python/Node executable paths, local model paths, and machine-specific overrides.

API-backed providers read keys from environment variables. For example:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
python debate_pipeline.py from-log --log latest --provider openrouter --layout dual --port 8099
```

## Local Assets Not Included

This repo intentionally does not include generated artifacts or private local
assets.

Ignored local outputs include:

- `.cache/`
- `output/`
- `logs/`
- `topics/`
- `transcripts/`
- `tts_scripts/`
- `run_records/`
- `pipeline.config.local.json`
- local model/checkpoint files such as `.gguf`, `.safetensors`, `.pt`, `.onnx`
- generated audio/video such as `.wav`, `.mp3`, `.mp4`
- local voice packs under `assets/voices/`

Voice packs should be placed locally in this shape:

```text
assets/voices/<pack>/host/
assets/voices/<pack>/positive/
assets/voices/<pack>/negative/
```

Each voice directory should contain audio samples and matching `.txt`
transcripts. They are ignored because they may contain private or licensed
voice material.

## Transcript Design

The debate generation stage can remain relatively formal and analytical. The
audience-facing transformation happens later in `json_to_transcript.py`.

For free-debate sections, the transcript stage can:

- keep opening and closing statements as larger structured turns
- split long written turns into shorter spoken exchanges
- interleave positive and negative chunks into a back-and-forth rhythm
- add a host bridge before free debate begins
- rewrite each free-debate chunk against the previous opponent chunk so the
  exchange feels more like clash than alternating monologues

Useful compatibility flags:

```powershell
python json_to_transcript.py ... --no-split-free-debate
python json_to_transcript.py ... --no-interleave-free-debate
python json_to_transcript.py ... --no-rewrite-free-debate-exchanges
```

## Video Layouts

The Remotion renderer currently supports:

- `dual`
- `podcast`
- `mindmap`

Render flags pass through from `debate_pipeline.py`, including:

- `--plan`
- `--audio`
- `--out`
- `--max-seconds`
- `--concurrency`
- `--gl`
- `--port`
- `--keep-bundle`
- `--keep-staged-audio`

The Remotion project lives under:

```text
pipeline/video/remotion/
```

Check the composition with:

```powershell
cd pipeline\video\remotion
npm run compositions
```

Expected composition id:

```text
user-debate-video
```

## Repository Layout

```text
.
├── dashboard_app.py
├── debate_pipeline.py
├── debate.py
├── debate_topic_generator.py
├── clean_logs.py
├── json_to_transcript.py
├── transcript_to_tts.py
├── pipeline/
│   ├── tts/
│   └── video/remotion/
├── third_party/
│   ├── CosyVoice/
│   └── Matcha-TTS/
├── ENVIRONMENT.md
├── PRODUCTION_PIPELINE.md
└── REPO_CONTEXT.md
```

## Docs

- [PRODUCTION_PIPELINE.md](./PRODUCTION_PIPELINE.md) explains the full pipeline
  and operational workflow.
- [ENVIRONMENT.md](./ENVIRONMENT.md) documents the verified local Conda
  environment and rebuild notes.
- [REPO_CONTEXT.md](./REPO_CONTEXT.md) contains deeper repo context and design
  notes.

## Practical Notes

- This repo is currently optimized for a Windows + Conda + CUDA workstation.
- Model weights and generated outputs are local by design.
- The dashboard is a local control panel, not a multi-user service.
- The project is useful as a production pipeline, but it still benefits from
  careful staged testing when models, voices, or layouts change.
