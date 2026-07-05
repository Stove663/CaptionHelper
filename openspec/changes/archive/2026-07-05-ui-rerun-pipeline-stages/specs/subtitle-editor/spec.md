## ADDED Requirements

### Requirement: Editor pipeline rerun toolbar

The subtitle editor SHALL provide toolbar actions to rerun ASR, rebuild the speaker reference bank, and re-run TTS synthesis for the current project when prerequisites are met.

#### Scenario: Rerun controls visible after ASR

- **WHEN** the user opens `/projects/{id}/edit` and project status is `ready`, `synthesis_ready`, `synthesis_failed`, `remux_ready`, or `remux_failed`
- **THEN** the editor toolbar displays rerun actions for ASR, reference bank, and TTS as applicable

#### Scenario: Rerun controls hidden during ASR processing

- **WHEN** project status is `extracting`, `transcribing`, `splitting`, or `building_references`
- **THEN** the editor shows a processing indicator and disables rerun actions that would conflict

#### Scenario: ASR rerun destroys edits warning

- **WHEN** the user clicks rerun ASR in the editor
- **THEN** the UI requires explicit confirmation before submitting the request

### Requirement: Editor reload after rerun completion

The subtitle editor SHALL refresh cues, reference quality, and synthesis state when a rerun job completes while the editor is open.

#### Scenario: Reload after ASR rerun

- **WHEN** ASR rerun completes and status becomes `ready`
- **THEN** the editor reloads subtitles from the server and clears prior edit/synthesis UI state

#### Scenario: Reload after reference bank rerun

- **WHEN** reference bank rerun completes
- **THEN** the editor refreshes the reference quality report without requiring a full page reload
