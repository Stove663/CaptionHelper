## ADDED Requirements

### Requirement: TTS provider selection in Web UI

The system SHALL allow users to choose the TTS provider for a project in the Web UI before synthesis runs.

#### Scenario: Default provider is shown

- **WHEN** the user opens a project that has not explicitly chosen a provider
- **THEN** the UI shows `MOSS-TTS` as the default selection

#### Scenario: User selects GLM-TTS

- **WHEN** the user changes the provider to `GLM-TTS`
- **THEN** the selection is saved with the project and used by subsequent synthesis actions

#### Scenario: Selection persists across reloads

- **WHEN** the user refreshes the page or returns later
- **THEN** the previously saved provider selection is restored from project metadata

### Requirement: TTS provider reported by API

The system SHALL expose the active TTS provider in project metadata and synthesis-related API responses.

#### Scenario: Project detail includes provider

- **WHEN** the client calls `GET /api/projects/{id}`
- **THEN** the response includes the selected `tts_provider`

#### Scenario: Synthesis job uses selected provider

- **WHEN** the client starts subtitle synthesis for a project
- **THEN** the server routes the job to the provider stored for that project
