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
  -v
```

| Flag | Description |
|------|-------------|
| `--output-dir` | Custom output directory |
| `--device` | Torch device (`cuda:0`, `cpu`, …) |
| `--language` | Fun-ASR-Nano language hint (default: `中文`) |
| `--hub` | `hf` for HuggingFace model download; omit for ModelScope |
| `--max-segment-s` | VAD max segment length in seconds |

## Development

```bash
uv sync --group dev
uv run pytest
```

## Pipeline

1. **Extract** — ffmpeg: video → mono 16 kHz WAV
2. **Transcribe** — Fun-ASR-Nano + VAD + cam++ speaker diarization
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

TTS synthesis requires extra dependencies and a **CUDA GPU**.

```bash
uv sync --extra tts
```

On Debian 12 with NVIDIA T4 (recommended production target):

```bash
sudo apt-get install -y ffmpeg
# Install NVIDIA driver per https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/
uv pip install --torch-backend cu128 -e ".[tts]"
```

First synthesis downloads [MOSS-TTS-Local-Transformer](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Local-Transformer) (1.7B). Default preset fits T4 16 GB (~5–7 GB peak VRAM).

| Flag | Description |
|------|-------------|
| `--tts-model` | `local-1.7b` (default) or `local-v1.5-4b` |
| `--tts-device` | Torch device for TTS (`cuda:0`, …) |
| `--tokens-per-second` | Duration→token mapping (default: `25`) |

```bash
uv run caption-helper web --port 8080 --tts-model local-1.7b --tts-device cuda:0
```

**Model guide (T4 16 GB)**

| Preset | Model | VRAM | Notes |
|--------|-------|------|-------|
| `local-1.7b` | MOSS-TTS-Local-Transformer | ~8 GB min | Recommended default |
| `local-v1.5-4b` | MOSS-TTS-Local-Transformer-v1.5 | ~12 GB min | Optional upgrade; 48 kHz stereo |

Zh-en code-mixed cues (e.g. `"请使用 Docker 部署"`) are synthesized without a fixed language tag so English words are pronounced naturally.

ffmpeg trims/pads synthesized audio to match each cue's time slot. Preflight checks GPU VRAM at startup and before synthesis.

**Troubleshooting**

| Symptom | Fix |
|---------|-----|
| CUDA not found | Install NVIDIA driver; verify `nvidia-smi` |
| OOM during synthesis | Use `--tts-model local-1.7b`; avoid 8B models on 16 GB GPUs |
| 8B model blocked | Preflight rejects MOSS-TTS-v1.5 on ≤16 GB VRAM — use `local-1.7b` |

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
