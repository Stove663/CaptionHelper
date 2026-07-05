## 1. Backend scaffolding

- [x] 1.1 Add FastAPI, uvicorn, python-multipart, aiofiles to `pyproject.toml`
- [x] 1.2 Create `src/caption_helper/web/` package (`app.py`, `routes/`, `jobs.py`, `store.py`)
- [x] 1.3 Implement `ProjectStore` for project directory CRUD under configurable `data_dir`
- [x] 1.4 Add `caption-helper web` CLI subcommand with `--port`, `--data-dir`, `--host` flags

## 2. Project model and pipeline integration

- [x] 2.1 Define `meta.json` schema (id, filename, status, error, created_at)
- [x] 2.2 Implement background job runner with status updates (`uploaded` → `extracting` → `transcribing` → `splitting` → `ready`)
- [x] 2.3 Wire job runner to existing `pipeline.process()` from `funasr-video-subtitles-audio-split`
- [x] 2.4 On job completion, write `subtitles_original.srt`, initial `subtitles_edited.srt`, and `subtitles.json` from ASR `sentence_info`
- [x] 2.5 Add job queue mutex to process one ASR job at a time

## 3. REST API

- [x] 3.1 `POST /api/projects` — multipart video upload, create project, enqueue job
- [x] 3.2 `GET /api/projects` — list all projects
- [x] 3.3 `GET /api/projects/{id}` — project metadata and status
- [x] 3.4 `GET /api/projects/{id}/subtitles` — return `subtitles.json`
- [x] 3.5 `PUT /api/projects/{id}/subtitles` — validate and save cues, regenerate SRT files
- [x] 3.6 `GET /api/projects/{id}/video` — stream source video with range support
- [x] 3.7 `GET /api/projects/{id}/modified-segments` — return modified cue list with segment paths

## 4. Subtitle versioning logic

- [x] 4.1 Implement `subtitles.json` read/write with `text_original`, `text_edited`, `modified` fields
- [x] 4.2 Implement `compute_modified()` — set `modified` when text, timestamps, or speaker differ from original
- [x] 4.3 Implement `write_srt_from_json()` to generate `subtitles_edited.srt`
- [x] 4.4 Implement `generate_modified_segments_json()` on each save
- [x] 4.5 Add unit tests for modification detection and original immutability

## 5. Frontend scaffolding

- [x] 5.1 Initialize Vite + React + TypeScript project in `frontend/`
- [x] 5.2 Configure API proxy to backend in dev mode
- [x] 5.3 Add build script; mount `frontend/dist` in FastAPI for production
- [x] 5.4 Set up routing: `/` (upload + project list), `/projects/:id/edit` (editor)

## 6. Upload and project list UI

- [x] 6.1 Build drag-and-drop upload component with progress indicator
- [x] 6.2 Build project list table with filename, status badge, created date, edit link
- [x] 6.3 Poll project status every 2s while processing; redirect to editor when `ready`

## 7. Subtitle editor UI

- [x] 7.1 Build split layout: HTML5 video player + scrollable cue list
- [x] 7.2 Implement cue click → video seek to `start_ms`
- [x] 7.3 Implement active cue highlight during video playback (timeupdate listener)
- [x] 7.4 Build inline editable fields: text, speaker, start/end timestamps
- [x] 7.5 Show modified badge and original-text comparison on hover/toggle
- [x] 7.6 Implement Save button calling `PUT /api/projects/{id}/subtitles`

## 8. Verification

- [x] 8.1 End-to-end test: upload video → wait for `ready` → edit cues → save → verify dual SRT files
- [x] 8.2 Verify `subtitles_original.srt` unchanged after multiple saves
- [x] 8.3 Verify `modified_segments.json` lists only edited cues with correct segment paths
- [x] 8.4 Document usage in README (`caption-helper web`, dev mode instructions)
