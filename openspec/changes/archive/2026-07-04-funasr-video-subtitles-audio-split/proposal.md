## Why

CaptionHelper needs an automated pipeline to turn video recordings into usable subtitle and audio assets. Manual transcription and speaker labeling is slow and error-prone; FunASR's Fun-ASR-Nano model with cam++ speaker diarization provides production-quality Chinese/multilingual ASR with per-sentence timestamps and speaker IDs in a single pass.

## What Changes

- Add a CLI tool that accepts a video file path and produces:
  - An extracted mono 16 kHz WAV audio file
  - An SRT subtitle file with speaker labels and millisecond-accurate timestamps
  - Per-segment audio clips split according to each subtitle entry's time range
- Integrate FunASR (`AutoModel`) with Fun-ASR-Nano-2512, fsmn-vad, and cam++ speaker model
- Use ffmpeg for video-to-audio extraction and audio segment cutting
- Define output directory layout and naming conventions for generated artifacts
- Add project scaffolding: `pyproject.toml`, dependencies, and basic usage documentation

## Capabilities

### New Capabilities

- `video-to-subtitles`: Extract audio from video, run FunASR diarized transcription, and emit SRT with speaker labels and timestamps
- `audio-segment-split`: Split the extracted audio into per-subtitle-segment WAV files aligned to SRT timestamps

### Modified Capabilities

_(none — greenfield project)_

## Impact

- **New dependencies**: `funasr`, `torch`, `soundfile`, `ffmpeg` (system binary)
- **Model downloads**: Fun-ASR-Nano-2512, fsmn-vad, cam++ (first run downloads from ModelScope or HuggingFace)
- **Compute**: GPU recommended (`cuda:0`); CPU fallback supported but slower
- **New code**: Python package under `src/caption_helper/` with CLI entry point
- **Output artifacts**: Per-input video, a sibling output directory containing `.srt`, full `.wav`, and `segments/` folder
