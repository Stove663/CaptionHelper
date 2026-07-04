## ADDED Requirements

### Requirement: Automatic reference fallback hierarchy

The system SHALL resolve TTS reference audio using a fallback hierarchy when a cue's own segment is inadequate: (1) cue segment, (2) speaker reference bank, (3) longest same-speaker segment, (4) concatenated adjacent same-speaker segments up to 10 s.

#### Scenario: Cue segment used when adequate

- **WHEN** a modified cue's own segment passes validation
- **THEN** TTS uses `segments/{cue}.wav` as reference with `reference_source: "cue"`

#### Scenario: Fallback to speaker bank

- **WHEN** a modified cue's segment is 400 ms and `speaker_refs/spk1.wav` is 3.2 s and adequate
- **THEN** TTS uses `speaker_refs/spk1.wav` with `reference_source: "speaker_bank"`

#### Scenario: Fallback to longest same-speaker segment

- **WHEN** the speaker bank is unavailable but another same-speaker segment of 2.5 s is adequate
- **THEN** TTS uses that segment with `reference_source: "longest_same_speaker"`

#### Scenario: Fallback to adjacent concatenation

- **WHEN** no single adequate same-speaker segment exists but concatenating adjacent same-speaker segments reaches ≥ 1500 ms
- **THEN** TTS uses the concatenated clip with `reference_source: "adjacent_concat"`

#### Scenario: No reference available

- **WHEN** no adequate reference audio exists for the cue's speaker
- **THEN** the cue is marked `failed` in `synthesis_manifest.json` with reason `no_adequate_reference` and synthesis continues for other cues

### Requirement: Manual reference override

The system SHALL allow the user to manually select an alternate same-speaker segment as the TTS reference for a specific cue.

#### Scenario: User overrides reference

- **WHEN** the user selects cue 5's reference to `segments/0012_spk1_*.wav` via the UI
- **THEN** TTS for cue 5 uses that segment with `reference_source: "manual_override"`

#### Scenario: Reject cross-speaker override

- **WHEN** the user selects a reference segment with a different `spk` than the cue
- **THEN** the server returns HTTP 422 with a validation error

### Requirement: Fallback metadata in synthesis manifest

The system SHALL record reference resolution details in `synthesis_manifest.json` for every synthesized cue.

#### Scenario: Manifest records fallback

- **WHEN** cue 3 uses speaker bank fallback because its segment was too short
- **THEN** the manifest entry includes `reference_source: "speaker_bank"`, `reference_path`, `reference_fallback_reason: "cue_segment_too_short: 420ms < 1500ms"`, `reference_duration_ms`, and `reference_quality_score`
