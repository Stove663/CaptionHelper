# CaptionHelper

Turn lecture and meeting videos into diarized subtitles (SRT) and per-sentence audio segments using [FunASR](https://modelscope.github.io/FunASR/zh/tutorial.html) (Fun-ASR-Nano + fsmn-vad + cam++).

## Prerequisites

- **Python** 3.11+
- **[uv](https://docs.astral.sh/uv/)** package manager
- **ffmpeg** on `PATH`

```bash
# macOS
brew install ffmpeg

# Debian 12 / Ubuntu
sudo apt-get install -y ffmpeg
```

Optional: **NVIDIA GPU + CUDA** for faster ASR (CPU fallback supported).

## Install

```bash
cd CaptionHelper
uv sync
```

`pyproject.toml` defaults to the [Tsinghua PyPI mirror](https://pypi.tuna.tsinghua.edu.cn/simple) for faster installs in mainland China. The frontend uses [npmmirror](https://npmmirror.com/) via `frontend/.npmrc`.

## Mirrors & overseas users

CaptionHelper defaults to China-hosted mirrors for network fetches:

| Layer | Default | Config location |
|-------|---------|-----------------|
| Python packages | Tsinghua PyPI | `[[tool.uv.index]]` in `pyproject.toml` |
| npm packages | npmmirror | `frontend/.npmrc` |
| HuggingFace models | hf-mirror.com | `HF_ENDPOINT` set at CLI/web startup |
| FunASR models | ModelScope | omit `--hub` (default) |

Runtime HuggingFace mirroring is applied automatically when `HF_ENDPOINT` is unset. See `.env.example` for override variables.

**Opt out (overseas users):**

- Python: remove or comment out `[[tool.uv.index]]` in `pyproject.toml`, or run `UV_INDEX_URL=https://pypi.org/simple uv sync`
- npm: delete `frontend/.npmrc` or run `npm config set registry https://registry.npmjs.org`
- HuggingFace: `export HF_ENDPOINT=https://huggingface.co` before running
- ASR: pass `--hub hf` to download FunASR models from HuggingFace instead of ModelScope

## Usage

Process a video into `audio.wav`, `subtitles.srt`, and `segments/`:

```bash
uv run caption-helper process meeting.mp4
```

Output directory (default): `meeting_output/`

```
meeting_output/
├── audio.wav          # mono 16 kHz extracted audio
├── subtitles.srt      # diarized subtitles with speaker labels
└── segments/
    ├── 0001_spk0_880-5195.wav
    └── ...
```

### Options

```bash
uv run caption-helper process meeting.mp4 \
  --output-dir /tmp/out \
  --device cuda:0 \
  --language 中文 \
  --hub hf \
  --max-segment-s 30 \
  --asr-provider funasr \
  -v
```

| Flag | Description |
|------|-------------|
| `--output-dir` | Custom output directory |
| `--device` | Torch device (`cuda:0`, `cpu`, …) |
| `--language` | Fun-ASR-Nano language hint (default: `中文`) |
| `--hub` | Model hub: omit for **ModelScope** (default, China-accessible); `hf` for HuggingFace |
| `--max-segment-s` | VAD max segment length in seconds |

## Development

```bash
uv sync --group dev
uv run pytest
```

## Pipeline

1. **Extract** — ffmpeg: video → mono 16 kHz WAV
2. **Transcribe** — FunASR
3. **SRT** — per-sentence cues with `[说话人 N]` prefix
4. **Split** — ffmpeg: per-cue WAV clips aligned to timestamps

First run downloads FunASR models (may take several minutes).

## Web UI

Start the local web server (API + built frontend):

```bash
# Build frontend once
cd frontend && npm install && npm run build && cd ..

# Start server
uv run caption-helper web --port 8080
```

Open http://127.0.0.1:8080 — upload a video, wait for processing, edit subtitle text, then synthesize modified segments with MOSS-TTS.

### Full workflow

1. Upload a lecture/meeting video and wait for ASR (`ready`)
2. Edit subtitle **text only** (timestamps and speaker are read-only)
3. Save changes — modified cues are tracked in `modified_segments.json`
4. Click **合成已修改片段** — MOSS-TTS clones each speaker's voice from the original `segments/` clip
5. Preview original vs TTS audio per modified cue in the editor
6. Open **预览输出** — build `output_video.mp4` with remixed audio and edited subtitles

Project layout after synthesis and remux:

```
<project>/
├── segments/              # original ASR clips (TTS voice reference)
├── tts_segments/          # MOSS-TTS output for modified cues only
├── synthesis_manifest.json
├── output_audio.wav       # full track with TTS/original clips at cue timestamps
├── output_video.mp4       # source video + output audio + edited subtitles
├── remux_manifest.json
└── subtitles.json
```

### Preview and remux

After editing (and optionally synthesizing modified cues), generate the final output:

```bash
uv run caption-helper remux ~/.caption-helper/projects/<uuid>/
```

Or use the web UI **预览输出** page: click **生成输出视频**, toggle **原视频** / **输出视频**, and download `output_video.mp4` or `output_audio.wav`.

Remux rules:

- Modified cues use `tts_segments/` when available; unmodified cues use original `segments/`
- Edited subtitles (`subtitles_edited.srt`) are embedded as a mov_text track
- Video stream is copied (`-c:v copy`) in **fixed-slot** mode; audio is re-encoded to AAC 192k
- If output audio is shorter than the video, it is padded to match video duration

### Timeline sync modes

CaptionHelper targets **lecture/meeting speech** where edits are usually one or two words per cue.

| Mode | TTS | Timestamps | Video |
|------|-----|------------|-------|
| **fixed-slot** (default) | Compressed to original cue slot | Unchanged (ASR times) | Stream copy |
| **natural-pace** | Natural speech rate | Rippled forward after extensions | Per-segment speed adjust |

**fixed-slot** works well for minor swaps that still fit the original time slot (e.g. swapping one Chinese term).

**natural-pace** is better when edited text is longer (e.g. Chinese → English). TTS runs without duration forcing; later cues shift forward; video slows/speeds per segment to stay in sync.

The editor shows a **compression risk** banner when fixed-slot would over-compress (estimated speech > 130% of slot). Switch to natural-pace before synthesis.

After natural-pace synthesis, `timeline.json` and `subtitles_ripple.srt` are generated. Remux uses rippled timestamps and speed-adjusted video.

```bash
# Project meta stores sync_mode; or pass via Web UI toggle before synthesis
```

API: `PUT /api/projects/{id}/sync-mode`, `GET /api/projects/{id}/compression-risk`, `GET /api/projects/{id}/timeline`, `GET /api/projects/{id}/remux-warnings`.

API endpoints: `POST /api/projects/{id}/remux`, `GET /api/projects/{id}/remux-status`, `GET /api/projects/{id}/output-video`, `GET /api/projects/{id}/output-audio`.

### MOSS-TTS setup (optional)

TTS synthesis requires extra dependencies and a **CUDA GPU** (≥12 GB VRAM recommended for the default 4B model).

```bash
uv sync --extra tts
```

On Debian 12 with dual NVIDIA T4 (recommended production target):

```bash
sudo apt-get install -y ffmpeg
# Install NVIDIA driver per https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/
uv pip install --torch-backend cu128 -e ".[tts]"
```

First synthesis downloads [MOSS-TTS-Local-Transformer-v1.5](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5) (4B). Weights are fetched via the HuggingFace mirror (`HF_ENDPOINT=https://hf-mirror.com`) unless you override it. Default preset fits T4 16 GB (~10–12 GB peak VRAM).

| Flag | Description |
|------|-------------|
| `--tts-model` | `local-v1.5-4b` (default) or `local-1.7b` |
| `--tts-device` | Torch device for TTS (`cuda:0`, `cuda:1`, …) |
| `--tokens-per-second` | Duration→token mapping (default: 12.5 for 4B, 25 for 1.7B) |

**Dual-T4 deployment** (ASR and TTS on separate GPUs):

```bash
uv run caption-helper web --port 8080 \
  --device cuda:0 \
  --tts-device cuda:1 \
  --tts-model local-v1.5-4b
```

**Model guide (T4 16 GB)**

| Preset | Model | VRAM | Notes |
|--------|-------|------|-------|
| `local-v1.5-4b` | MOSS-TTS-Local-Transformer-v1.5 | ~12 GB min | **Recommended default**; 48 kHz → 16 kHz mono in pipeline |
| `local-1.7b` | MOSS-TTS-Local-Transformer | ~8 GB min | Fallback for smaller GPUs or OOM |

Zh-en code-mixed cues (e.g. `"请使用 Docker 部署"`) are synthesized without a fixed language tag so English words are pronounced naturally. The editor warns when code-mixed edits are likely to sound rushed in fixed-slot mode — switch to **自然语速** for better English pronunciation.

ffmpeg trims/pads synthesized audio to match each cue's time slot. Preflight checks the configured TTS GPU VRAM at startup and before synthesis.

**Troubleshooting**

| Symptom | Fix |
|---------|-----|
| CUDA not found | Install NVIDIA driver; verify `nvidia-smi` |
| OOM during synthesis | Use dedicated `--tts-device cuda:1`; or fall back to `--tts-model local-1.7b` |
| 8B model blocked | Preflight rejects MOSS-TTS-v1.5 on ≤16 GB VRAM — use `local-v1.5-4b` |
| Mixed zh-en sounds rushed | Switch project to natural-pace mode before synthesis |

### GLM-TTS setup (optional alternative)

The Web UI lets you choose **MOSS-TTS** (default) or **GLM-TTS** per project before synthesis. GLM-TTS uses [zai-org/GLM-TTS](https://github.com/zai-org/GLM-TTS) zero-shot voice cloning with a separate install:

```bash
git clone https://github.com/zai-org/GLM-TTS.git
cd GLM-TTS
pip install -r requirements.txt
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download zai-org/GLM-TTS --local-dir ckpt
export GLM_TTS_HOME="$(pwd)"
```

(`HF_ENDPOINT` is set automatically when running CaptionHelper; set it explicitly for standalone `huggingface-cli` downloads.)

CaptionHelper also needs `torchaudio` (`uv sync --extra glm-tts`). In the editor toolbar, switch to **GLM-TTS** before clicking **合成已修改片段**. The active provider is stored in `meta.json` as `tts_provider` and recorded in `synthesis_manifest.json`.

Preflight blocks GLM-TTS synthesis when `GLM_TTS_HOME` is unset, checkpoints are missing, or VRAM is below ~8 GB.

**Zh-en code-mixed subtitles (GLM-TTS):**

- CaptionHelper enables GLM **Phoneme-in** automatically for code-mixed cues (`glm_phoneme_mode: auto` in `meta.json`; values `auto` | `on` | `off`).
- Mixed text is preprocessed (CJK↔Latin spacing) before GLM `text_normalize`.
- Phoneme-in improves Chinese polyphone handling in mixed sentences; **English words stay as graphemes** in GLM's `g2p_infer` — natural English pronunciation still depends on the model and reference audio.
- **Fixed-slot + GLM-TTS:** GLM has no MOSS-style `tokens` duration hint; fixed-slot uses post-hoc trim/pad and can compress English syllables. The editor shows a **GLM-specific warning** when code-mixed modified cues exist; switch to **natural-pace** before synthesis when possible.
- `synthesis_manifest.json` records `phoneme_enabled`, `text_prep_applied`, and `glm_phoneme_mode` per cue.

**Phoneme-in call chain (upstream GLM-TTS):** `load_models(use_phoneme)` → `TextFrontEnd` + `generate_long` → per chunk: `text_normalize` → optional `g2p_infer` → LLM → Flow. Pin a GLM-TTS git tag in production for reproducibility.

### Reference audio fallback

When a modified cue's own segment is too short (<1.5 s) or low quality, CaptionHelper automatically picks a fallback reference (same speaker only):

1. Cue's own `segments/` clip (if adequate)
2. `speaker_refs/spk{N}.wav` — best segment per speaker, built after ASR
3. Longest same-speaker segment
4. Concatenated adjacent same-speaker segments (up to 10 s)

Rebuild reference bank for existing projects:

```bash
uv run caption-helper build-refs ~/.caption-helper/projects/<uuid>/
```

The editor shows reference quality badges before synthesis. Cues with no adequate reference are blocked unless you choose **合成可用片段** (skip unavailable cues).

### Development mode

Run backend and frontend separately with hot reload:

```bash
# Terminal 1
uv run caption-helper web --port 8080

# Terminal 2
cd frontend && npm install && npm run dev
```

Frontend dev server: http://127.0.0.1:5173 (proxies `/api` to `:8080`).

Project data is stored under `~/.caption-helper/projects/` by default (`--data-dir` to override).
