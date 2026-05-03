# Debate Repo

This repo contains the debate-to-video pipeline: debate logs, transcript cleanup,
TTS script generation, CosyVoice audio, Whisper timing checks, and Remotion video
rendering.

The current workstation runtime is one Conda environment named `debate`. It
replaces the older cross-environment flow that used separate debate, CosyVoice,
and Remotion environments.

## Current Runtime

- Conda env: `debate`
- Python: `C:\Users\ctz20\anaconda3\envs\debate\python.exe`
- Node/npm: installed inside the same Conda env
- Local overrides: `pipeline.config.local.json` (ignored by Git)
- Model/cache root: repo-local `.cache/`

See [ENVIRONMENT.md](./ENVIRONMENT.md) for the exact package versions, local
config, CUDA llama-cpp notes, and verification commands.

The debate stage can stay relatively formal and analytical. During
`json_to_transcript.py`, free-debate turns are reshaped for the audience: long
written turns are split into shorter spoken exchanges, then same-turn positive
and negative chunks are interleaved into a more live back-and-forth rhythm, with
a host bridge after the opening statements. A second exchange-rewrite pass then
rewrites each short free-debate chunk against the previous opponent chunk, so
the output behaves more like actual clash instead of alternating chopped-up
monologues.

## Quick Start

Start the local dashboard:

```powershell
cd G:\Coding\01_AI-ML\LLM\debate
conda activate debate
python dashboard_app.py
```

Then open `http://127.0.0.1:7861`. The dashboard lets you choose the pipeline
entry point, choose where the run should stop, start/stop a run, watch stage
progress, follow live logs, test voice packs, preview video layouts, and open
generated artifacts. While a job is running, setup controls are locked so the
active run cannot be accidentally changed from another tab.

Generated run artifacts and local voice packs are intentionally ignored by Git.
Keep voice packs under `assets/voices/<pack>/host`, `positive`, and `negative`
on the workstation rather than committing private/licensed samples.

CLI remains available for scripted runs:

```powershell
cd G:\Coding\01_AI-ML\LLM\debate
conda activate debate
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

Run from a generated topic framework:

```powershell
python debate_pipeline.py from-topic --topic-file topics\my_topic.md --turns 3 --provider local --layout dual --port 8099
```

Or give the pipeline a raw topic and let it generate the framework first:

```powershell
python debate_pipeline.py from-topic --topic "当胎儿生命权与女性身体自主权发生冲突时，应优先保护女性身体自主权。" --turns 3 --provider local --layout dual --port 8099
```

Or generate a fresh debate log only:

```powershell
python debate.py --provider local --topic-file topics\my_topic.md --turns 3
```

## API Providers

The same environment also has the API SDKs installed. Set the relevant key and
choose the provider:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
python debate_pipeline.py from-log --log latest --provider openrouter --layout dual --port 8099
```

## Main docs

See [PRODUCTION_PIPELINE.md](./PRODUCTION_PIPELINE.md) for the full pipeline,
configuration, and render workflow.
