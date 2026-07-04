## ADDED Requirements

### Requirement: MOSS-TTS synthesis for modified segments

The system SHALL re-synthesize speech audio for every subtitle cue marked `modified: true` using MOSS-TTS-v1.5 voice cloning, and MUST NOT synthesize unmodified cues.

#### Scenario: Synthesize only modified cues

- **WHEN** the user triggers synthesis and cues 2 and 5 are marked `modified: true` while other cues are unmodified
- **THEN** the system generates TTS audio only for cues 2 and 5

#### Scenario: Skip when no modifications

- **WHEN** the user triggers synthesis and no cues are modified
- **THEN** the system returns without generating any TTS files and reports zero segments synthesized

### Requirement: Voice cloning from original segment

The system SHALL use each modified cue's original `segments/` WAV file as the MOSS-TTS voice-cloning reference audio.

#### Scenario: Reference audio selection

- **WHEN** synthesizing cue index 3 with `spk=1` and segment path `segments/0003_spk1_5200-8100.wav`
- **THEN** MOSS-TTS receives `text_edited` and `reference=[segments/0003_spk1_5200-8100.wav]`

#### Scenario: Missing reference segment

- **WHEN** a modified cue's reference segment WAV does not exist
- **THEN** the system marks that cue as failed in `synthesis_manifest.json` with an error message and continues with remaining cues

### Requirement: Duration matching to cue time slot

The system SHALL generate TTS audio whose final duration matches the cue's time slot (`end_ms - start_ms`) within ±50 ms tolerance.

#### Scenario: Duration from timestamps

- **WHEN** cue index 2 has `start_ms=5200` and `end_ms=8100` (duration 2.9 s)
- **THEN** the synthesized `tts_segments/0002_spk*_5200-8100.wav` has a duration of approximately 2.9 seconds

#### Scenario: MOSS-TTS tokens parameter

- **WHEN** synthesizing a cue with target duration 2.9 seconds
- **THEN** the system passes a `tokens` value derived from the duration to MOSS-TTS `build_user_message`

#### Scenario: Post-process trim and pad

- **WHEN** MOSS-TTS output duration differs from the target slot duration
- **THEN** the system uses ffmpeg to trim excess audio or pad silence to achieve the exact target duration

### Requirement: TTS output storage

The system SHALL write synthesized audio files to `tts_segments/` with filenames mirroring the original segment naming pattern.

#### Scenario: Output filename

- **WHEN** TTS synthesis completes for cue index 3 with `spk=1`, `start_ms=5200`, `end_ms=8100`
- **THEN** the output file is `tts_segments/0003_spk1_5200-8100.wav`

### Requirement: Synthesis manifest

The system SHALL write `synthesis_manifest.json` recording metadata for each synthesized cue.

#### Scenario: Manifest contents

- **WHEN** synthesis completes for a modified cue
- **THEN** `synthesis_manifest.json` includes `index`, `spk`, `text_edited`, `reference_segment`, `target_duration_ms`, `tokens`, `output_path`, and `status` (`success` or `failed`)

### Requirement: Web UI synthesis trigger

The system SHALL expose a "Synthesize modified segments" action in the project editor and a corresponding API endpoint.

#### Scenario: Start synthesis via API

- **WHEN** the client calls `POST /api/projects/{id}/synthesize`
- **THEN** the server enqueues a background TTS job and returns HTTP 202 with job status `synthesizing`

#### Scenario: Synthesis progress polling

- **WHEN** a TTS job is in progress
- **THEN** `GET /api/projects/{id}/synthesis-status` returns `status`, `completed`, and `total` counts

#### Scenario: Synthesis complete

- **WHEN** all modified cues have been synthesized
- **THEN** project status includes `synthesis_ready` and the editor shows a link to preview `tts_segments/`

### Requirement: MOSS-TTS model configuration

The system SHALL use `OpenMOSS-Team/MOSS-TTS-v1.5` as the default TTS model with configurable `--tts-model` and `--tts-device` options.

#### Scenario: Default model

- **WHEN** synthesis runs without explicit model configuration
- **THEN** the system loads `OpenMOSS-Team/MOSS-TTS-v1.5` via `AutoModel` and `AutoProcessor` with `trust_remote_code=True`

#### Scenario: GPU device selection

- **WHEN** CUDA is available and no device is specified
- **THEN** the system uses `cuda:0` for MOSS-TTS inference
