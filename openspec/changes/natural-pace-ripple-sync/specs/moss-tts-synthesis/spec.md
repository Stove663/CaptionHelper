## MODIFIED Requirements

### Requirement: Duration matching to cue time slot

The system SHALL support two duration strategies based on `sync_mode`. In `fixed-slot` mode, TTS audio MUST match the cue time slot within ±50 ms. In `natural-pace` mode, TTS audio SHALL be synthesized at natural speech rate without forced compression.

#### Scenario: Fixed-slot duration match

- **WHEN** `sync_mode` is `fixed-slot` and cue index 2 has `start_ms=5200` and `end_ms=8100`
- **THEN** the synthesized `tts_segments/0002_*.wav` has a duration of approximately 2.9 seconds

#### Scenario: Fixed-slot tokens parameter

- **WHEN** synthesizing in `fixed-slot` mode with target duration 2.9 seconds
- **THEN** the system passes a `tokens` value derived from the duration to MOSS-TTS `build_user_message`

#### Scenario: Fixed-slot post-process trim and pad

- **WHEN** MOSS-TTS output duration differs from the target slot in `fixed-slot` mode
- **THEN** the system uses ffmpeg to trim or pad to the exact target duration

#### Scenario: Natural-pace no forced compression

- **WHEN** `sync_mode` is `natural-pace`
- **THEN** the system calls MOSS-TTS without a `tokens` duration parameter and records the actual output duration in `synthesis_manifest.json`

#### Scenario: Natural-pace actual duration recorded

- **WHEN** natural-pace synthesis produces a 3.4 s clip for a 2.9 s original slot
- **THEN** `synthesis_manifest.json` records `actual_duration_ms: 3400`, `slot_duration_ms: 2900`, `delta_ms: 500`
