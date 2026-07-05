# web-ui-server Specification

## Purpose
TBD - created by archiving change add-subtitle-editor-ui. Update Purpose after archive.
## Requirements
### Requirement: Web server launch command

The system SHALL provide a `caption-helper web` command that starts a local HTTP server serving the Web UI and API.

#### Scenario: Default port startup

- **WHEN** the user runs `caption-helper web`
- **THEN** the server listens on `http://127.0.0.1:8080` and serves the upload page

#### Scenario: Custom port and data directory

- **WHEN** the user runs `caption-helper web --port 3000 --data-dir /tmp/caption-data`
- **THEN** the server listens on port 3000 and stores projects under `/tmp/caption-data/projects/`

### Requirement: Video upload via Web UI

The system SHALL accept video file uploads through the browser and create a new processing project for each upload.

#### Scenario: Successful upload

- **WHEN** the user selects or drags a video file (`.mp4`, `.mov`, `.mkv`) onto the upload area
- **THEN** the system creates a project directory, saves the file as `source.<ext>`, and begins ASR processing

#### Scenario: Unsupported file type

- **WHEN** the user uploads a non-video file
- **THEN** the system returns HTTP 400 with an error message describing accepted formats

### Requirement: Background ASR job execution

The system SHALL run the caption pipeline (extract → transcribe → SRT → split) as a background job per uploaded project without blocking the HTTP server, using FunASR for the transcription step.

#### Scenario: Background processing status flow

- **WHEN** a video upload completes
- **THEN** the project status progresses through `uploaded`, `extracting`, `transcribing`, `splitting`, and `ready`

#### Scenario: Job failure

- **WHEN** the pipeline fails (e.g., ffmpeg error, model failure)
- **THEN** the project status is set to `failed` with an error message stored in `meta.json`

### Requirement: Project listing API

The system SHALL expose an API to list all projects and retrieve individual project metadata.

#### Scenario: List projects

- **WHEN** the client calls `GET /api/projects`
- **THEN** the response includes an array of projects with `id`, `filename`, `status`, and `created_at`

#### Scenario: Get project detail

- **WHEN** the client calls `GET /api/projects/{id}`
- **THEN** the response includes full project metadata and current processing status

### Requirement: Video streaming for editor

The system SHALL serve the uploaded source video for in-browser playback during subtitle editing.

#### Scenario: Stream source video

- **WHEN** the client requests `GET /api/projects/{id}/video`
- **THEN** the server streams the project's `source.*` file with appropriate `Content-Type`

### Requirement: Output video download endpoint

The system SHALL expose `GET /api/projects/{id}/output-video` to serve the remuxed `output_video.mp4` file for download.

#### Scenario: Serve output video when ready

- **WHEN** the client requests `GET /api/projects/{id}/output-video` and `output_video.mp4` exists
- **THEN** the server responds with HTTP 200, `Content-Type: video/mp4`, and the file bytes

#### Scenario: Attachment disposition for download

- **WHEN** the client requests `GET /api/projects/{id}/output-video` for download
- **THEN** the response includes `Content-Disposition: attachment` with filename `output_video.mp4`

#### Scenario: Output not ready

- **WHEN** `output_video.mp4` does not exist
- **THEN** the server responds with HTTP 404 and a descriptive error body

### Requirement: Pipeline stage rerun API

The system SHALL expose `POST /api/projects/{id}/rerun/asr`, `POST /api/projects/{id}/rerun/references`, `POST /api/projects/{id}/rerun/synthesis`, and `POST /api/projects/{id}/rerun/remux` to re-execute processing stages on existing projects without a new video upload.

#### Scenario: Rerun endpoints return accepted

- **WHEN** a valid rerun request is received for any of the four endpoints
- **THEN** the server responds with HTTP 202 and a JSON body including `status` set to the initial processing state for that stage

#### Scenario: Rerun synthesis accepts options

- **WHEN** the client calls `POST /api/projects/{id}/rerun/synthesis` with optional `skip_unavailable` and `sync_mode` in the body
- **THEN** the server applies the same validation and options as `POST /api/projects/{id}/synthesize`

### Requirement: ASR rerun artifact cleanup

The system SHALL delete subtitles, audio segments, speaker references, TTS outputs, and remux outputs before enqueueing an ASR rerun, while preserving `source.*` and project metadata.

#### Scenario: Cleanup before ASR rerun

- **WHEN** `POST /api/projects/{id}/rerun/asr` is accepted
- **THEN** files including `subtitles.json`, `segments/*.wav`, `speaker_refs/`, `tts_segments/`, `output_video.mp4`, and related manifests are removed before extraction begins

#### Scenario: Source video preserved

- **WHEN** ASR rerun cleanup runs
- **THEN** the project's `source.*` file remains on disk

### Requirement: Background rerun job execution

The system SHALL execute rerun jobs in the background using the same job runner infrastructure as initial upload processing, without blocking the HTTP server.

#### Scenario: ASR rerun status progression

- **WHEN** an ASR rerun job runs
- **THEN** project status updates through the same stages as initial upload: `extracting` → `transcribing` → `splitting` → `ready`

#### Scenario: Reference bank rerun status

- **WHEN** a reference bank rerun job runs
- **THEN** project status is set to `building_references` during execution and `ready` on success, or `failed` with an error message on failure

### Requirement: Project deletion API

The system SHALL expose `DELETE /api/projects/{id}` to permanently remove a project and all on-disk artifacts.

#### Scenario: Delete returns no content

- **WHEN** the client calls `DELETE /api/projects/{id}` for an existing, non-processing project
- **THEN** the server responds with HTTP 204 and removes the project directory

#### Scenario: Delete unknown project

- **WHEN** the client calls `DELETE /api/projects/{id}` for a non-existent project ID
- **THEN** the server responds with HTTP 404

#### Scenario: Delete busy project

- **WHEN** the client calls `DELETE /api/projects/{id}` while the project has an in-progress job
- **THEN** the server responds with HTTP 409

### Requirement: Project list excludes deleted projects

The system SHALL only include projects whose directories exist on disk in `GET /api/projects` responses.

#### Scenario: List after deletion

- **WHEN** a project is deleted manually or by expiration cleanup
- **THEN** subsequent `GET /api/projects` responses do not include that project

