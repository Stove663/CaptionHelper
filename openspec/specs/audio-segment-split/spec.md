# audio-segment-split Specification

## Purpose
TBD - created by archiving change funasr-video-subtitles-audio-split. Update Purpose after archive.
## Requirements
### Requirement: Per-sentence audio segment export

The system SHALL split the extracted full audio into individual WAV files, one per subtitle sentence, using each sentence's `start` and `end` timestamps in milliseconds.

#### Scenario: Segment files created

- **WHEN** transcription produces N sentence records and the full `audio.wav` exists
- **THEN** the system writes N WAV files under `segments/` in the output directory

#### Scenario: Segment filename convention

- **WHEN** the third sentence has `spk=1`, `start=5200`, `end=8100`
- **THEN** the corresponding segment file is named `0003_spk1_5200-8100.wav`

#### Scenario: Segment audio format

- **WHEN** a segment is exported
- **THEN** the output WAV is mono 16 kHz PCM, time-aligned to the sentence's start and end timestamps

### Requirement: Segment coverage matches subtitles

The system SHALL ensure every SRT cue has a corresponding audio segment with matching time boundaries.

#### Scenario: One-to-one mapping

- **WHEN** the SRT file contains 42 cues
- **THEN** the `segments/` directory contains exactly 42 WAV files in sequential index order

#### Scenario: Timestamp alignment

- **WHEN** SRT cue 5 spans `00:00:12,500 --> 00:00:18,300`
- **THEN** segment file `0005_*.wav` has a duration of approximately 5.8 seconds (±50 ms tolerance for encoder rounding)

### Requirement: Integrated pipeline segment step

The system SHALL run audio segment splitting automatically as the final step of `caption-helper process`, after SRT generation.

#### Scenario: Full pipeline includes segments

- **WHEN** the user runs `caption-helper process meeting.mp4`
- **THEN** the output directory contains `segments/` with one WAV per subtitle entry, in addition to `subtitles.srt` and `audio.wav`

