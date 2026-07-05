## MODIFIED Requirements

### Requirement: Background ASR job execution

The system SHALL run the caption pipeline (extract → transcribe → SRT → split) as a background job per uploaded project without blocking the HTTP server, using FunASR for the transcription step.

#### Scenario: Background processing status flow

- **WHEN** a video upload completes
- **THEN** the project status progresses through `uploaded`, `extracting`, `transcribing`, `splitting`, and `ready`

#### Scenario: Job failure

- **WHEN** the pipeline fails (e.g., ffmpeg error, model failure)
- **THEN** the project status is set to `failed` with an error message stored in `meta.json`

## REMOVED Requirements

### Requirement: ASR provider on project upload

**Reason**: MOSS-Audio removed; FunASR is the only ASR backend and requires no per-upload provider selection.

**Migration**: Ignore `asr_provider` in upload multipart data; existing projects with `asr_provider: moss-audio` in `meta.json` are treated as FunASR on next load.

### Requirement: ASR provider update endpoint

**Reason**: No ASR backend choice remains; `PUT /api/projects/{id}/asr-provider` is obsolete.

**Migration**: Remove client calls to the endpoint; delete the route from the API.
