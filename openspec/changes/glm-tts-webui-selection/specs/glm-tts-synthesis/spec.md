## ADDED Requirements

### Requirement: GLM-TTS synthesis for modified cues

The system SHALL support GLM-TTS as an alternative synthesis provider for modified subtitle cues.

#### Scenario: GLM-TTS is selected for synthesis

- **WHEN** a project has `tts_provider=glm-tts`
- **THEN** the synthesis job invokes GLM-TTS for each modified cue instead of MOSS-TTS

#### Scenario: GLM-TTS output is stored compatibly

- **WHEN** GLM-TTS generates audio for a cue
- **THEN** the resulting audio is stored in the same project artifact layout expected by downstream merge/remux steps

#### Scenario: GLM-TTS synthesis failure is reported

- **WHEN** GLM-TTS fails for a cue or project
- **THEN** the job records the failure in synthesis status and surfaces a user-visible error message

### Requirement: GLM-TTS provider constraints

The system SHALL document and enforce any GLM-TTS-specific invocation constraints needed for reliable project synthesis.

#### Scenario: Unsupported runtime is detected

- **WHEN** the configured runtime cannot satisfy GLM-TTS requirements
- **THEN** the system blocks synthesis or warns the user before job submission
