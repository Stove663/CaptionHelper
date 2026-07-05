## ADDED Requirements

### Requirement: ASR provider on project upload

The system SHALL accept an optional `asr_provider` field when creating a project via video upload, defaulting to `funasr` when omitted.

#### Scenario: Upload with MOSS-Audio selected

- **WHEN** the user uploads a video with `asr_provider` set to `moss-audio`
- **THEN** the created project stores `asr_provider: moss-audio` in `meta.json` and background ASR uses MOSS-Audio

#### Scenario: Upload without provider uses default

- **WHEN** the user uploads a video without specifying `asr_provider`
- **THEN** the project stores `asr_provider: funasr` and background ASR uses FunASR

### Requirement: ASR provider update endpoint

The system SHALL expose `PUT /api/projects/{id}/asr-provider` to update the stored ASR provider for an existing project.

#### Scenario: Update provider while idle

- **WHEN** the client calls `PUT /api/projects/{id}/asr-provider` with a valid value and ASR is not in progress
- **THEN** the server updates `meta.json` and returns the new `asr_provider`

#### Scenario: Update blocked during ASR

- **WHEN** project status is `extracting`, `transcribing`, or `splitting`
- **THEN** `PUT /api/projects/{id}/asr-provider` returns HTTP 409

## MODIFIED Requirements

### Requirement: Background ASR job execution

The system SHALL run the caption pipeline (extract → transcribe → SRT → split) as a background job per uploaded project without blocking the HTTP server, using the project's stored `asr_provider` for the transcription step.

#### Scenario: Background processing status flow

- **WHEN** a video upload completes
- **THEN** the project status progresses through `uploaded`, `extracting`, `transcribing`, `splitting`, and `ready`

#### Scenario: MOSS-Audio background job

- **WHEN** a project has `asr_provider: moss-audio`
- **THEN** the background transcription step invokes the MOSS-Audio backend instead of FunASR
