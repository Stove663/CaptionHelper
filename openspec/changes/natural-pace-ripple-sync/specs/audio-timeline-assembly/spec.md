## MODIFIED Requirements

### Requirement: Timeline-aligned audio assembly

The system SHALL assemble per-cue clips into `output_audio.wav` using original timestamps in `fixed-slot` mode and ripple-adjusted timestamps in `natural-pace` mode. Assembly MUST use `audio.wav` as the base track for lecture/meeting content.

#### Scenario: Fixed-slot uses original timestamps

- **WHEN** `sync_mode` is `fixed-slot` and cue 1 spans 880–5195 ms
- **THEN** cue 1 audio is placed at 880 ms in `output_audio.wav`

#### Scenario: Natural-pace uses adjusted timestamps

- **WHEN** `sync_mode` is `natural-pace` and cue 3 has `start_ms_adj=5200` after ripple
- **THEN** cue 3 audio is placed at 5200 ms in `output_audio.wav`

#### Scenario: Natural-pace total duration may exceed original

- **WHEN** natural-pace ripple extends the final cue end beyond the original video duration
- **THEN** `output_audio.wav` duration equals the adjusted final cue end time

#### Scenario: Lecture base track

- **WHEN** audio assembly runs
- **THEN** the system starts from the full `audio.wav` and overlays cue clips at their respective positions

#### Scenario: Non-cue regions preserve original audio

- **WHEN** a time region is not covered by any subtitle cue
- **THEN** that region retains audio from the original extracted `audio.wav`
