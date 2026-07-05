## MODIFIED Requirements

### Requirement: Video remux with new audio and edited subtitles

The system SHALL combine source video, assembled audio, and subtitles into `output_video.mp4`. In `fixed-slot` mode the video stream is copied. In `natural-pace` mode the video is speed-adjusted per segment before muxing.

#### Scenario: Fixed-slot remux with stream copy

- **WHEN** `sync_mode` is `fixed-slot`
- **THEN** the system remuxes with `-c:v copy`, new AAC audio, and `subtitles_edited.srt` as the subtitle track

#### Scenario: Natural-pace remux with speed-adjusted video

- **WHEN** `sync_mode` is `natural-pace`
- **THEN** the system muxes speed-adjusted video segments with rippled `output_audio.wav` and `subtitles_ripple.srt`

#### Scenario: Subtitle track selection

- **WHEN** remux runs in natural-pace mode
- **THEN** the subtitle track is generated from `subtitles_ripple.srt` with adjusted timestamps
