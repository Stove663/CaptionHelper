## ADDED Requirements

### Requirement: Per-cue clip source selection

The system SHALL select the audio clip for each subtitle cue based on its `modified` flag: use `tts_segments/` for modified cues and `segments/` for unmodified cues.

#### Scenario: Unmodified cue uses original segment

- **WHEN** cue index 4 has `modified: false`
- **THEN** the assembly uses `segments/0004_spk*_*.wav` for that time slot

#### Scenario: Modified cue uses TTS segment

- **WHEN** cue index 2 has `modified: true` and `tts_segments/0002_spk*_*.wav` exists
- **THEN** the assembly uses the TTS segment for that time slot

#### Scenario: Missing TTS blocks assembly

- **WHEN** cue index 2 has `modified: true` but no corresponding file exists in `tts_segments/`
- **THEN** the assembly job fails with an error listing the missing cue indices

### Requirement: Timeline-aligned audio assembly

The system SHALL assemble all per-cue clips into a single `output_audio.wav` file aligned to each cue's `start_ms` and `end_ms` timestamps on the full video timeline.

#### Scenario: Clips placed at correct timestamps

- **WHEN** cue 1 spans 880–5195 ms and cue 2 spans 5200–8100 ms
- **THEN** `output_audio.wav` contains cue 1 audio starting at 880 ms and cue 2 audio starting at 5200 ms

#### Scenario: Full video duration coverage

- **WHEN** the source video is 120 seconds long
- **THEN** `output_audio.wav` has a duration of 120 seconds (±100 ms)

#### Scenario: Non-cue regions preserve original audio

- **WHEN** a time region is not covered by any subtitle cue
- **THEN** that region retains audio from the original extracted `audio.wav`

### Requirement: Output audio format

The system SHALL produce `output_audio.wav` as mono PCM at 16000 Hz to match the pipeline's internal audio format.

#### Scenario: Output format

- **WHEN** audio assembly completes
- **THEN** `output_audio.wav` is mono 16 kHz PCM WAV

### Requirement: Assembly manifest

The system SHALL write `remux_manifest.json` documenting which clip source was used for each cue.

#### Scenario: Manifest records clip sources

- **WHEN** assembly completes for a project with 3 modified and 7 unmodified cues
- **THEN** `remux_manifest.json` lists all 10 cues with `clip_source` (`original` or `tts`), `clip_path`, `start_ms`, and `end_ms`
