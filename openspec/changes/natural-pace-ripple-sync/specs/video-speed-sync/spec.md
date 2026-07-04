## ADDED Requirements

### Requirement: Per-segment video speed adjustment

The system SHALL adjust video playback speed per segment in natural-pace mode so that each video segment's duration matches its corresponding audio segment's adjusted duration.

#### Scenario: Video slows when TTS is longer

- **WHEN** a speech segment's adjusted audio duration is 3.5 s but the original video segment was 3.0 s
- **THEN** the system applies a slow-down factor of approximately 0.857 (`setpts=PTS/0.857`) to that video segment

#### Scenario: Video speeds up when TTS is shorter

- **WHEN** a speech segment's adjusted audio duration is 2.0 s but the original video segment was 2.5 s
- **THEN** the system applies a speed-up factor to that video segment so its output duration is 2.0 s

### Requirement: Video segment splitting and concatenation

The system SHALL split the source video at original cue boundaries, speed-adjust each segment, and concatenate into the final output video.

#### Scenario: Segment files created

- **WHEN** natural-pace remux runs on a project with 10 cues
- **THEN** the system creates speed-adjusted clips in `video_segments/` and concatenates them into `output_video.mp4`

#### Scenario: Fixed-slot mode skips speed adjustment

- **WHEN** `sync_mode` is `fixed-slot`
- **THEN** the system remuxes with `-c:v copy` and does not apply per-segment speed adjustment

### Requirement: Slow-down limit warning

The system SHALL warn the user when any video segment requires slow-down beyond a configurable minimum speed factor (default 0.75x).

#### Scenario: Excessive slow-down warning

- **WHEN** a video segment requires slow-down below 0.75x (25% slower than original)
- **THEN** the UI displays a warning before remux with the affected cue indices and speed factors

### Requirement: Audio-video duration alignment

The system SHALL ensure the final `output_video.mp4` duration matches `output_audio.wav` duration within ±100 ms in natural-pace mode.

#### Scenario: Final duration match

- **WHEN** natural-pace remux completes
- **THEN** `output_video.mp4` and `output_audio.wav` have equal duration within ±100 ms
