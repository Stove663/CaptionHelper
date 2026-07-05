## Why

CaptionHelper currently hard-codes FunASR (Fun-ASR-Nano + VAD + cam++ diarization) as the only ASR backend. [MOSS-Audio](https://github.com/OpenMOSS/MOSS-Audio) offers competitive ASR accuracy—especially on dialect, code-mixed, and noisy speech—and strong timestamp ASR, giving users an alternative when FunASR quality or diarization behavior is unsatisfactory. A per-project ASR selector mirrors the existing TTS provider pattern and lets users pick the engine best suited to their source material without changing the rest of the caption workflow.

## What Changes

- Add a per-project ASR provider selection in the Web UI with `FunASR` and `MOSS-Audio`
- Persist the selected provider in project metadata so initial processing and ASR rerun jobs use the same backend
- Route transcription through the chosen provider instead of hard-coding `Transcriber` (FunASR)
- Keep FunASR as the default for backward compatibility with existing projects
- Integrate MOSS-Audio (default model: `MOSS-Audio-4B-Instruct`) with ModelScope/hf-mirror download defaults per `china-mirror-defaults`
- Normalize MOSS-Audio output into the existing `Sentence` schema (`text`, `spk`, `start`, `end`) so downstream SRT, segment split, and reference-bank steps stay unchanged
- Expose ASR provider on project APIs and allow selection at upload time or before ASR rerun

## Capabilities

### New Capabilities

- `asr-provider-selection`: Web UI and API support for choosing the active ASR backend per project
- `moss-audio-asr`: MOSS-Audio-based transcription producing diarized `Sentence` records compatible with the existing pipeline

### Modified Capabilities

- `video-to-subtitles`: ASR requirement broadens from FunASR-only to provider-dispatched transcription; add MOSS-Audio path and provider-aware model hub defaults
- `web-ui-server`: Expose ASR provider in project metadata, upload/create flow, and editor controls
- `pipeline-stage-rerun`: ASR rerun uses the project's stored ASR provider

## Impact

- **Project metadata**: store `asr_provider` (`funasr` | `moss-audio`) in `meta.json`, default `funasr`
- **Transcription layer**: introduce provider dispatch (`Transcriber` protocol or factory) with `MossAudioTranscriber` alongside existing FunASR `Transcriber`
- **Dependencies**: optional `[moss-audio]` extra with MOSS-Audio runtime deps (torch, transformers, ffmpeg); lazy import to avoid breaking FunASR-only installs
- **Web UI**: ASR provider toggle on home upload / editor (parallel to TTS provider UX)
- **API**: `PUT /api/projects/{id}/asr-provider`, `GET` project detail includes `asr_provider`
- **Model downloads**: MOSS-Audio weights from ModelScope by default; HuggingFace/hf-mirror when configured
- **VRAM / preflight**: MOSS-Audio-4B-Instruct needs GPU headroom; document minimum CUDA memory and fail fast with actionable errors
