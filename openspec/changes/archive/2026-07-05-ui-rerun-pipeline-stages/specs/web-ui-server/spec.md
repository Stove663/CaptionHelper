## ADDED Requirements

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
