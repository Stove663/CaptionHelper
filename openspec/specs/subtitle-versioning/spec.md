# subtitle-versioning Specification

## Purpose
TBD - created by archiving change add-subtitle-editor-ui. Update Purpose after archive.
## Requirements
### Requirement: Immutable original subtitle storage

The system SHALL write ASR-generated subtitles to `subtitles_original.srt` and MUST NOT overwrite this file after initial creation.

#### Scenario: Original preserved after edit

- **WHEN** the user saves edited subtitles multiple times
- **THEN** `subtitles_original.srt` remains identical to the initial ASR output

### Requirement: Separate edited subtitle storage

The system SHALL maintain `subtitles_edited.srt` as the working copy for user modifications, initially identical to the original upon first ASR completion.

#### Scenario: Initial edited copy

- **WHEN** ASR processing completes for a new project
- **THEN** the system creates both `subtitles_original.srt` and `subtitles_edited.srt` with identical content

#### Scenario: Edited file updated on save

- **WHEN** the user saves subtitle edits
- **THEN** only `subtitles_edited.srt` is updated to reflect the current edited state

### Requirement: Structured subtitle manifest with modification tracking

The system SHALL maintain `subtitles.json` as the canonical structured representation of all cues, including per-cue `text_original`, `text_edited`, and `modified` boolean fields.

#### Scenario: Unmodified cue after ASR

- **WHEN** ASR produces a cue with text "欢迎大家"
- **THEN** `subtitles.json` records `text_original` and `text_edited` both as "欢迎大家" and `modified` as `false`

#### Scenario: Modified cue after edit

- **WHEN** the user changes cue text from "欢迎大家" to "欢迎各位朋友"
- **THEN** `subtitles.json` records `text_edited` as "欢迎各位朋友" and `modified` as `true` while `text_original` remains "欢迎大家"

#### Scenario: Modification on timestamp or speaker change

- **WHEN** the user changes a cue's `start_ms`, `end_ms`, or `spk` without changing text
- **THEN** `modified` is set to `true` for that cue

### Requirement: Modified segments export for TTS pipeline

The system SHALL generate and expose `modified_segments.json` listing all cues marked `modified: true`, including segment file paths for downstream voice cloning and TTS synthesis.

#### Scenario: Export modified segments

- **WHEN** the client calls `GET /api/projects/{id}/modified-segments` after the user has edited cues 2 and 5
- **THEN** the response lists exactly cues 2 and 5 with their `index`, `spk`, `text_original`, `text_edited`, `start_ms`, `end_ms`, and corresponding `segments/` WAV path

#### Scenario: No modifications

- **WHEN** no cues have been edited
- **THEN** `modified_segments.json` contains an empty list and the API returns `[]`

#### Scenario: Regenerate on save

- **WHEN** the user saves subtitle edits
- **THEN** `modified_segments.json` is regenerated to reflect the current modification state

