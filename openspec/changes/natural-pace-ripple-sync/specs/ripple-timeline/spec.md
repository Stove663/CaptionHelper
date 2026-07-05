## ADDED Requirements

### Requirement: Ripple timestamp recalculation

The system SHALL recalculate subtitle cue timestamps in natural-pace mode by shifting all cues after an extended modified segment forward by the cumulative duration delta.

#### Scenario: Single extended cue ripples subsequent cues

- **WHEN** cue 3 in natural-pace mode has `delta_ms=+500` (TTS 500 ms longer than original slot) and cue 4 originally started at 8100 ms
- **THEN** cue 4's adjusted start becomes 8600 ms

#### Scenario: Cumulative ripple across multiple extended cues

- **WHEN** cue 3 extends by 500 ms and cue 7 extends by 300 ms in natural-pace mode
- **THEN** cues 4–6 shift by 500 ms and cues 8+ shift by 800 ms cumulatively

#### Scenario: Unmodified cues shift with ripple

- **WHEN** cue 5 is unmodified and cue 3 extended by 500 ms
- **THEN** cue 5's adjusted timestamps shift forward by 500 ms while retaining its original audio content

### Requirement: Timeline manifest

The system SHALL write `timeline.json` recording original and adjusted timestamps for every cue.

#### Scenario: Timeline manifest contents

- **WHEN** ripple recalculation completes
- **THEN** `timeline.json` contains per cue: `index`, `start_ms_orig`, `end_ms_orig`, `start_ms_adj`, `end_ms_adj`, `delta_ms`, and `modified`

### Requirement: Ripple subtitle output

The system SHALL generate `subtitles_ripple.srt` with adjusted timestamps and edited text in natural-pace mode.

#### Scenario: Ripple SRT uses adjusted timestamps

- **WHEN** cue 3 has `start_ms_adj=5200` and `end_ms_adj=8700` after ripple
- **THEN** `subtitles_ripple.srt` shows `00:00:05,200 --> 00:00:08,700` for cue 3

#### Scenario: Fixed-slot mode uses original timestamps

- **WHEN** `sync_mode` is `fixed-slot`
- **THEN** output subtitles use original ASR timestamps from `subtitles_edited.srt` without ripple adjustment

### Requirement: Total duration change reporting

The system SHALL report the total duration change after ripple recalculation.

#### Scenario: Duration delta displayed

- **WHEN** ripple shifts the final cue end from 120000 ms to 123500 ms
- **THEN** the UI reports a total extension of +3.5 seconds before remux
