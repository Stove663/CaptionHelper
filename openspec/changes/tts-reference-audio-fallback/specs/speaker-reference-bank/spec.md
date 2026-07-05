## ADDED Requirements

### Requirement: Per-speaker reference bank construction

The system SHALL build a per-speaker voice reference bank after ASR segment splitting, selecting the best-quality longest segment per speaker.

#### Scenario: Bank file created per speaker

- **WHEN** ASR processing completes for a project with speakers 0 and 1
- **THEN** the system creates `speaker_refs/spk0.wav` and `speaker_refs/spk1.wav`

#### Scenario: Best segment selection

- **WHEN** speaker 0 has segments of 0.8 s, 3.2 s, and 1.5 s duration
- **THEN** the bank clip for speaker 0 is derived from the highest-scoring adequate segment (typically the 3.2 s clip)

#### Scenario: Bank metadata recorded

- **WHEN** the speaker reference bank is built
- **THEN** `reference_quality.json` records per speaker: `bank_path`, `source_cue_index`, `duration_ms`, and `quality_score`
