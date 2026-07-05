## Context

CaptionHelper's first change delivers a CLI pipeline: video → ASR → SRT + audio segments. Users must now review and correct subtitles in a browser before a future voice-cloning/TTS stage. The editor must preserve the original ASR output while tracking which cues were edited so downstream tooling knows which segments need re-synthesis.

This change adds a local-first Web UI; no authentication or multi-tenant hosting is required.

## Goals / Non-Goals

**Goals:**

- Upload video via browser; trigger existing `pipeline.process()` in a background thread
- Show processing progress until subtitles are ready
- Editor: list cues with inline text edit, speaker label, start/end timestamps; video seeks on cue click
- Save edits to `subtitles_edited.srt` without overwriting `subtitles_original.srt`
- Maintain `subtitles.json` with per-cue `modified: true/false` derived from text diff vs original
- Export list of modified segment indices for future TTS pipeline (`modified_segments.json`)
- Single-user local app: `caption-helper web --port 8080`

**Non-Goals:**

- User authentication or cloud deployment
- Real-time collaborative editing
- In-browser video editing or hard-subtitle burning
- Voice cloning or TTS synthesis (future change; only track modified segments here)
- Mobile-optimized layout (desktop-first is acceptable for v1)

## Decisions

### 1. Backend: FastAPI + background thread pool

**Choice:** FastAPI with `asyncio` + `run_in_executor` for blocking ASR/ffmpeg work.

**Rationale:** Reuses Python pipeline; async upload handling; simple local deployment with uvicorn.

**Alternatives considered:**
- Celery + Redis: Overkill for single-user local app.
- Gradio: Faster to prototype but limited subtitle editor UX.

### 2. Frontend: Vite + React + TypeScript

**Choice:** SPA in `frontend/` with two routes: `/` (upload/projects list) and `/projects/:id/edit` (editor).

**Rationale:** Rich interactive editor (video sync, inline edit) needs component model; Vite is fast to develop.

**Alternatives considered:**
- HTMX + Jinja: Simpler but awkward for video-synced cue editing.

### 3. Project data layout

```
<data_dir>/projects/<uuid>/
├── meta.json              # id, filename, status, created_at
├── source.mp4             # uploaded video (or original extension)
├── audio.wav
├── subtitles_original.srt # ASR output, never overwritten
├── subtitles_edited.srt   # user saves; starts as copy of original
├── subtitles.json         # structured cues + modified flags
├── modified_segments.json # export: indices of cues needing TTS
└── segments/
    └── ...
```

**Rationale:** Clear separation of original vs edited; JSON enables diff tracking without parsing SRT.

### 4. Subtitle data model (JSON)

```json
{
  "cues": [
    {
      "index": 1,
      "spk": 0,
      "start_ms": 880,
      "end_ms": 5195,
      "text_original": "欢迎大家来体验",
      "text_edited": "欢迎大家来体验",
      "modified": false
    }
  ]
}
```

On save, `modified` is set when `text_edited != text_original` (or timestamps/speaker changed). `subtitles_edited.srt` is regenerated from JSON.

**Rationale:** Explicit diff per cue is exactly what TTS/voice-cloning pipeline needs.

### 5. API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/projects` | Upload video, start job |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Project meta + status |
| GET | `/api/projects/{id}/subtitles` | Return `subtitles.json` |
| PUT | `/api/projects/{id}/subtitles` | Save edited cues |
| GET | `/api/projects/{id}/video` | Stream source video |
| GET | `/api/projects/{id}/modified-segments` | Return indices + segment paths for TTS |

### 6. Editor UX

- Left/right or top/bottom split: HTML5 `<video>` + scrollable cue table
- Click cue → seek video to `start_ms`
- Editable fields: text (primary), speaker ID, start/end (advanced, optional collapse)
- "Save" button → PUT subtitles; visual badge on modified cues
- Read-only view of original text on hover or toggle for comparison

### 7. Job status machine

`uploaded` → `extracting` → `transcribing` → `splitting` → `ready` | `failed`

Frontend polls `GET /api/projects/{id}` every 2s while not `ready`/`failed`.

### 8. Static file serving

FastAPI mounts Vite build output at `/` in production; dev mode documents `npm run dev` with proxy to `:8080`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Long ASR jobs block UI patience | Progress status + polling; show stage name |
| Large video uploads timeout | Increase uvicorn limits; chunked upload deferred to v2 |
| Concurrent uploads OOM GPU | Process one ASR job at a time (job queue mutex) |
| Timestamp edits desync segments | v1: text-only edits; timestamp edit regenerates segment on save (optional v1.1) |
| SRT round-trip data loss | JSON is source of truth; SRT is export format |

## Migration Plan

1. Implement after `funasr-video-subtitles-audio-split` is applied
2. `caption-helper web` becomes primary UX; CLI remains for scripting
3. Existing CLI output dirs can be imported manually (future: import endpoint)

## Open Questions

- Should edited timestamp changes re-cut segment WAVs on save? _Deferred: v1 text-only edits; segments keyed by original timestamps._
- Max upload size default? _Default 2 GB with configurable `--max-upload-mb`._
