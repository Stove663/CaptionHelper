## Why

The CLI-only workflow from `funasr-video-subtitles-audio-split` is insufficient for reviewing and correcting ASR output. Users need a browser-based interface to upload videos, wait for transcription, and edit subtitles before downstream voice cloning and TTS synthesis. Separating original and edited subtitle versions is essential to identify which segments require re-synthesis.

## What Changes

- Add a local Web UI (FastAPI backend + frontend) launched via `caption-helper web`
- Video upload page with drag-and-drop; server runs the existing ASR pipeline as a background job
- Job status polling (extracting → transcribing → ready)
- Subtitle editor page: video player synced with editable cue list (text, timestamps, speaker)
- Dual subtitle storage per project:
  - `subtitles_original.srt` — immutable ASR output
  - `subtitles_edited.srt` — user-saved edits (initially a copy of original)
- Structured `subtitles.json` manifest tracking per-cue `modified` flag for future TTS/voice-cloning pipeline
- Project-centric workspace: each uploaded video gets a persistent project directory under a configurable data root

## Capabilities

### New Capabilities

- `web-ui-server`: FastAPI app with video upload, background ASR jobs, project listing, and static frontend serving
- `subtitle-editor`: Browser-based subtitle editor with video playback sync and save/export
- `subtitle-versioning`: Separate original vs edited subtitle files and per-segment modification tracking

### Modified Capabilities

_(none — builds on `funasr-video-subtitles-audio-split` pipeline without changing its CLI contract)_

## Impact

- **New dependencies**: `fastapi`, `uvicorn`, `python-multipart`, `aiofiles`; frontend build tooling (Vite + React or lightweight alternative)
- **New code**: `src/caption_helper/web/` (API routes, job runner, project store); `frontend/` SPA
- **Data directory**: `~/.caption-helper/projects/<id>/` (or `--data-dir`) holding video, audio, both SRT files, JSON manifest, segments
- **Compute**: ASR still GPU-heavy; web server runs jobs sequentially or with limited concurrency
- **Depends on**: `funasr-video-subtitles-audio-split` pipeline modules (`pipeline.py`, `srt.py`, etc.)
