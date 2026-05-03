# Debate Environment

The canonical local runtime is a single Conda environment named `debate`.

This environment is intended to run all three major parts of the project:

- debate and transcript generation
- CosyVoice TTS and Whisper timing verification
- Remotion video rendering

Older notes may mention separate `heretic`, `cosyvoice`, or `remotion`
environments. Treat those as historical context unless a specific debugging
task says otherwise.

## Verified Local Environment

Current verified env:

- Conda env: `debate`
- Env path: `C:\Users\ctz20\anaconda3\envs\debate`
- Python: `3.10.20`
- Node: `22.22.2`
- npm: `10.9.7`
- PyTorch: `2.3.1+cu121`
- torchaudio: `2.3.1+cu121`
- NumPy: `1.26.4`
- `llama-cpp-python`: `0.3.20`
- OpenAI SDK: `2.24.0`
- Anthropic SDK: `0.97.0`
- `google-generativeai`: `0.8.6`
- `openai-whisper`: `20231117`
- Remotion local app: `pipeline/video/remotion`

The llama-cpp-python install has CUDA offload enabled. A working build should
have `ggml-cuda.dll` under:

```text
C:\Users\ctz20\anaconda3\envs\debate\Lib\site-packages\llama_cpp\lib
```

## Local Config

`pipeline.config.local.json` is ignored by Git and should point every stage at
the same environment:

```json
{
  "executables": {
    "main_python": "C:\\Users\\ctz20\\anaconda3\\envs\\debate\\python.exe",
    "tts_python": "C:\\Users\\ctz20\\anaconda3\\envs\\debate\\python.exe",
    "node": "C:\\Users\\ctz20\\anaconda3\\envs\\debate\\node.exe",
    "node_package_manager": "C:\\Users\\ctz20\\anaconda3\\envs\\debate\\npm.cmd"
  }
}
```

Use `pipeline.config.local.example.json` as the committed template.

## Daily Use

Activate the env before running commands:

```powershell
conda activate debate
```

Create a new debate log interactively:

```powershell
python debate.py --provider local
```

Run from the latest debate log through TTS and video:

```powershell
python debate_pipeline.py from-log --log latest --provider local --layout dual --port 8099
```

Resume from later stages:

```powershell
python debate_pipeline.py from-transcript --transcript latest --provider local --layout dual --port 8099
python debate_pipeline.py from-tts --tts-script latest --layout dual --port 8099
python debate_pipeline.py video --timeline latest --layout podcast --port 8099
```

## Verification

Core environment check:

```powershell
python -c "import sys, torch, torchaudio, numpy, llama_cpp; print(sys.version.split()[0]); print(torch.__version__, torchaudio.__version__, torch.cuda.is_available()); print(numpy.__version__); print(llama_cpp.__version__)"
```

CUDA offload check:

```powershell
python -c "from llama_cpp import llama_cpp; print(llama_cpp.llama_supports_gpu_offload())"
```

Entry point checks:

```powershell
python debate.py --help
python transcript_to_tts.py --help
python pipeline\tts\generate_debate_audio.py --help
node pipeline\video\remotion\render-user-debate.cjs --help
```

Remotion composition check:

```powershell
cd pipeline\video\remotion
npm run compositions -- --port=8099
```

The expected composition id is `user-debate-video`.

## Rebuild Notes

The env was created by cloning the previously working CosyVoice env, then
installing debate, API SDK, Node, Remotion, Whisper, and CUDA llama-cpp pieces
into that one env.

High-level rebuild outline:

```powershell
conda create -n debate --clone cosyvoice -y
conda activate debate
python -m pip install openai==2.24.0 anthropic==0.97.0 google-generativeai==0.8.6
python -m pip install openai-whisper==20231117
conda install -c conda-forge nodejs=22 -y
cd pipeline\video\remotion
npm install
```

For `llama-cpp-python==0.3.20`, use a CUDA build. Before building any C/C++
extension on this machine, inspect the environment for compiler pollution:

```powershell
cmd /c "set | findstr /I \"^CC= ^CXX= ^CL= ^_CL_= ^RC= ^CMAKE_\""
```

If any of these are set, clear them in the build shell before invoking CMake or
pip:

```powershell
Remove-Item Env:CC, Env:CXX, Env:CL, Env:_CL_, Env:RC, Env:CMAKE_GENERATOR, Env:CMAKE_GENERATOR_PLATFORM -ErrorAction SilentlyContinue
```

Important llama-cpp build lesson: do not set `CL` to a compiler path. On MSVC,
`CL` is command-line injection for every `cl.exe` invocation, not a compiler
locator. Use CMake compiler variables instead if a compiler path is needed.

## Requirements File

Current policy:

- `requirements.base.txt` is the only project-level Python requirements file.
- It includes the CUDA 12.1 Torch wheel index and pins
  `torch==2.3.1+cu121` plus `torchaudio==2.3.1+cu121`.
- It includes Whisper through `openai-whisper==20231117`.

Removed legacy files:

- `requirements.whisper.txt`
- `requirements.torch-cu121.txt`
- `requirements.torch-cpu.txt`
- `setup_repo.ps1`
- `tools/setup_repo.py`

There is intentionally no CPU fallback requirements file now. This project is
documented around the local CUDA-capable Conda `debate` environment.

## Known Warnings

`pip check` may report inherited metadata conflicts from the cloned CosyVoice
and Matcha-TTS stack. The current env has still been verified to load CosyVoice3,
use CUDA Torch, import llama-cpp with GPU offload, and list the Remotion
composition.

The `google-generativeai` package currently emits an upstream deprecation
warning recommending `google.genai`. That migration is not part of this
environment cleanup.
