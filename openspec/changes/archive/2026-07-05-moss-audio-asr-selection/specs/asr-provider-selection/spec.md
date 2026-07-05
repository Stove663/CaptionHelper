## ADDED Requirements

### Requirement: ASR provider selection in Web UI

The system SHALL allow users to choose the ASR provider for a project in the Web UI before ASR processing runs.

#### Scenario: Default provider is shown

- **WHEN** the user opens the upload form or a project that has not explicitly chosen an ASR provider
- **THEN** the UI shows `FunASR` as the default selection

#### Scenario: User selects MOSS-Audio

- **WHEN** the user changes the ASR provider to `MOSS-Audio`
- **THEN** the selection is saved with the project and used by subsequent ASR actions

#### Scenario: Selection persists across reloads

- **WHEN** the user refreshes the page or returns later
- **THEN** the previously saved ASR provider selection is restored from project metadata

#### Scenario: Provider toggle disabled during ASR

- **WHEN** project status is `extracting`, `transcribing`, or `splitting`
- **THEN** the ASR provider toggle is disabled until processing completes

### Requirement: ASR provider reported by API

The system SHALL expose the active ASR provider in project metadata and ASR-related API responses.

#### Scenario: Project detail includes provider

- **WHEN** the client calls `GET /api/projects/{id}`
- **THEN** the response includes the selected `asr_provider`

#### Scenario: ASR job uses selected provider

- **WHEN** the client uploads a video or triggers ASR rerun for a project
- **THEN** the server routes transcription to the provider stored for that project

#### Scenario: Update ASR provider via API

- **WHEN** the client calls `PUT /api/projects/{id}/asr-provider` with `asr_provider` set to `funasr` or `moss-audio`
- **THEN** the server persists the value in `meta.json` and returns the updated project metadata

#### Scenario: Invalid ASR provider rejected

- **WHEN** the client sends an `asr_provider` value other than `funasr` or `moss-audio`
- **THEN** the server returns HTTP 422 with a validation error

### Requirement: CLI ASR provider flag

The system SHALL accept an `--asr-provider` option on `caption-helper process` with values `funasr` or `moss-audio`, defaulting to `funasr`.

#### Scenario: CLI uses FunASR by default

- **WHEN** the user runs `caption-helper process meeting.mp4` without `--asr-provider`
- **THEN** transcription uses FunASR

#### Scenario: CLI selects MOSS-Audio

- **WHEN** the user runs `caption-helper process meeting.mp4 --asr-provider moss-audio`
- **THEN** transcription uses MOSS-Audio
