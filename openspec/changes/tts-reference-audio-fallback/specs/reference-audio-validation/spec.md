## ADDED Requirements

### Requirement: Reference audio duration validation

The system SHALL validate that a candidate reference audio clip meets a minimum duration threshold (default 1500 ms) before use for TTS voice cloning.

#### Scenario: Adequate duration passes

- **WHEN** a reference clip has duration 2000 ms
- **THEN** the clip passes duration validation

#### Scenario: Short clip fails duration check

- **WHEN** a cue segment has duration 400 ms
- **THEN** the clip is marked `inadequate` with reason `too_short`

### Requirement: Reference audio quality scoring

The system SHALL score reference audio quality using heuristics for clipping, low volume, and excessive silence.

#### Scenario: Clipping detected

- **WHEN** a reference clip has peak amplitude above 0.99
- **THEN** the quality score is penalized and clipping is recorded in validation metadata

#### Scenario: Low RMS detected

- **WHEN** a reference clip RMS is below 0.01
- **THEN** the quality score is penalized and low volume is recorded in validation metadata

#### Scenario: Adequate quality threshold

- **WHEN** a clip has `quality_score` below 0.5
- **THEN** the clip is marked `inadequate` regardless of duration

### Requirement: Per-cue reference quality report

The system SHALL produce a per-cue reference quality assessment for all modified cues before TTS synthesis.

#### Scenario: Quality report via API

- **WHEN** the client calls `GET /api/projects/{id}/reference-quality`
- **THEN** the response lists each modified cue with `adequate`, `quality_score`, `duration_ms`, and `issues` array

#### Scenario: UI quality indicators

- **WHEN** a modified cue's own segment is inadequate but a fallback is available
- **THEN** the editor displays a warning badge on that cue indicating fallback will be used
