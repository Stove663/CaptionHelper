## MODIFIED Requirements

### Requirement: Rerun ASR pipeline on existing project

The system SHALL allow re-running the full ASR pipeline (extract → transcribe → split → initialize subtitles → build speaker reference bank) for a project that already has a stored `source.*` video, without requiring a new upload. Transcription SHALL use FunASR.

#### Scenario: Successful ASR rerun

- **WHEN** the client calls `POST /api/projects/{id}/rerun/asr` and `source.*` exists
- **THEN** the server returns HTTP 202, clears downstream artifacts (subtitles, segments, references, TTS, remux outputs), enqueues background ASR processing with FunASR, and project status progresses through `extracting`, `transcribing`, `splitting`, to `ready`

#### Scenario: ASR rerun from failed project

- **WHEN** a project's status is `failed` and the client calls `POST /api/projects/{id}/rerun/asr`
- **THEN** the server clears the error, enqueues FunASR ASR processing, and status leaves `failed`

#### Scenario: ASR rerun blocked while processing

- **WHEN** project status is `extracting`, `transcribing`, or `splitting`
- **THEN** `POST /api/projects/{id}/rerun/asr` returns HTTP 409

#### Scenario: Missing source video

- **WHEN** no `source.*` file exists for the project
- **THEN** `POST /api/projects/{id}/rerun/asr` returns HTTP 400
