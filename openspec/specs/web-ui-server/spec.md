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

The system SHALL run the existing caption pipeline (extract → transcribe → SRT → split) as a background job per uploaded project without blocking the HTTP server.

#### Scenario: Job progress reporting

- **WHEN** a project is processing
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

