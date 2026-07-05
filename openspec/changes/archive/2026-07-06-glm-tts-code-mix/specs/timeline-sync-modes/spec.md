## ADDED Requirements

### Requirement: GLM-TTS provider-aware natural-pace guidance

The system SHALL surface stronger natural-pace recommendations when `tts_provider=glm-tts`, the project uses `sync_mode=fixed-slot`, and the project has at least one modified code-mixed cue.

#### Scenario: Compression-risk API includes GLM guidance

- **WHEN** `GET /api/projects/{id}/compression-risk` is called for a project with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and one or more modified code-mixed cues
- **THEN** the response includes a `provider_guidance` string explaining that GLM-TTS has no duration token hint and fixed-slot mode may compress English pronunciation

#### Scenario: Code-mixed at-risk retains recommend_natural_pace

- **WHEN** a modified cue is code-mixed and compression-at-risk
- **THEN** the compression-risk cue entry includes `recommend_natural_pace: true` regardless of TTS provider

#### Scenario: Editor banner uses GLM-specific text

- **WHEN** the Web UI editor displays a compression banner for a project with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and code-mixed modified cues
- **THEN** the banner text states that GLM-TTS in fixed-slot mode may compress English words and recommends switching to natural-pace

#### Scenario: MOSS-TTS banner unchanged

- **WHEN** `tts_provider=moss-tts` and compression warnings are shown
- **THEN** the existing MOSS-oriented banner text and behavior apply without regression

#### Scenario: No automatic mode switch

- **WHEN** GLM-specific natural-pace guidance is displayed
- **THEN** the system does not change `sync_mode` in `meta.json` without explicit user action

### Requirement: GLM fixed-slot synthesis acknowledgment

The system SHALL allow users to proceed with GLM-TTS fixed-slot synthesis on code-mixed projects after displaying guidance, without forcing a sync mode change.

#### Scenario: Synthesis proceeds after warning

- **WHEN** the user initiates synthesis with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and code-mixed modified cues
- **THEN** the synthesis job MAY proceed after the UI has shown provider guidance (no hard block in v1)
