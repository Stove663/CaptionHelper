## MODIFIED Requirements

### Requirement: Structured subtitle manifest with modification tracking

The system SHALL maintain `subtitles.json` as the canonical structured representation of all cues, including per-cue `text_original`, `text_edited`, and `modified` boolean fields. The `modified` flag MUST be set to `true` only when `text_edited` differs from `text_original`. Timestamps and speaker ID are immutable after ASR and MUST NOT affect the `modified` flag.

#### Scenario: Unmodified cue after ASR

- **WHEN** ASR produces a cue with text "欢迎大家"
- **THEN** `subtitles.json` records `text_original` and `text_edited` both as "欢迎大家" and `modified` as `false`

#### Scenario: Modified cue after text edit

- **WHEN** the user changes cue text from "欢迎大家" to "欢迎各位朋友"
- **THEN** `subtitles.json` records `text_edited` as "欢迎各位朋友" and `modified` as `true` while `text_original` remains "欢迎大家"

#### Scenario: Immutable timestamps and speaker

- **WHEN** subtitles are saved after any number of edit sessions
- **THEN** each cue's `start_ms`, `end_ms`, and `spk` remain identical to the values produced by ASR

## REMOVED Requirements

### Requirement: Modification on timestamp or speaker change

**Reason**: Subtitle editor no longer permits timestamp or speaker editing; only text changes trigger modification tracking.

**Migration**: `modified` is computed solely from `text_edited != text_original`. Existing projects with timestamp-only diffs are not supported.
