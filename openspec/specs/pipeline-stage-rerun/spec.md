# pipeline-stage-rerun Specification

## Purpose
TBD - created by archiving change ui-rerun-pipeline-stages. Update Purpose after archive.

## Requirements
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

### Requirement: Rerun speaker reference bank

The system SHALL allow rebuilding the per-speaker reference bank (`speaker_refs/`) from existing `segments/` without re-running ASR or modifying subtitles.

#### Scenario: Successful reference bank rerun

- **WHEN** the client calls `POST /api/projects/{id}/rerun/references` and `segments/` plus `subtitles.json` exist
- **THEN** the server returns HTTP 202, rebuilds `speaker_refs/` via `build_speaker_reference_bank`, and sets status to `ready` on success

#### Scenario: Reference rerun prerequisites missing

- **WHEN** `segments/` is empty or `subtitles.json` is missing
- **THEN** `POST /api/projects/{id}/rerun/references` returns HTTP 400

#### Scenario: Reference rerun blocked during ASR

- **WHEN** ASR processing is in progress for the project
- **THEN** `POST /api/projects/{id}/rerun/references` returns HTTP 409

### Requirement: Rerun TTS synthesis

The system SHALL allow re-running TTS synthesis for modified subtitle segments on an existing project without re-uploading the source video.

#### Scenario: Successful synthesis rerun

- **WHEN** the client calls `POST /api/projects/{id}/rerun/synthesis` and `modified_segments.json` contains at least one entry
- **THEN** the server returns HTTP 202, enqueues synthesis, and project status becomes `synthesizing` then `synthesis_ready` or `synthesis_failed` per existing synthesis rules

#### Scenario: Synthesis rerun with no modified segments

- **WHEN** `modified_segments.json` is missing or empty
- **THEN** `POST /api/projects/{id}/rerun/synthesis` returns HTTP 400

#### Scenario: Synthesis rerun blocked while in progress

- **WHEN** synthesis is already running for the project
- **THEN** `POST /api/projects/{id}/rerun/synthesis` returns HTTP 409

### Requirement: Rerun remux

The system SHALL allow re-running audio assembly and video remux on an existing project without re-uploading the source video.

#### Scenario: Successful remux rerun

- **WHEN** the client calls `POST /api/projects/{id}/rerun/remux` and all required TTS clips validate
- **THEN** the server returns HTTP 202, enqueues remux, and project status becomes `remuxing` then `remux_ready` or `remux_failed`

#### Scenario: Remux rerun missing clips

- **WHEN** modified cues lack corresponding TTS clips
- **THEN** `POST /api/projects/{id}/rerun/remux` returns HTTP 400 with missing clip details

#### Scenario: Remux rerun blocked while in progress

- **WHEN** remux is already running for the project
- **THEN** `POST /api/projects/{id}/rerun/remux` returns HTTP 409

### Requirement: Web UI pipeline rerun controls

The Web UI SHALL expose controls to trigger ASR, reference bank, TTS, and remux reruns from the project list and editor pages, enabled only when prerequisites are met.

#### Scenario: Home page rerun actions

- **WHEN** a project is in `ready` or a post-ready status on the home page
- **THEN** the user can access rerun actions appropriate to that status (e.g., rerun ASR, rebuild references)

#### Scenario: ASR rerun confirmation

- **WHEN** the user initiates ASR rerun from the Web UI
- **THEN** the UI shows a confirmation explaining that subtitles, edits, and downstream outputs will be discarded before calling the API

#### Scenario: Rerun in progress feedback

- **WHEN** a rerun job is executing
- **THEN** the UI disables conflicting rerun buttons and shows processing status via existing project polling
