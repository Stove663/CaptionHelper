## ADDED Requirements

### Requirement: Video remux with new audio and edited subtitles

The system SHALL combine the source video, assembled `output_audio.wav`, and `subtitles_edited.srt` into `output_video.mp4`.

#### Scenario: Successful remux

- **WHEN** `output_audio.wav` and `subtitles_edited.srt` exist for a project
- **THEN** the system produces `output_video.mp4` containing the original video stream, the new audio track, and a soft subtitle track from the edited SRT

#### Scenario: Video stream copy

- **WHEN** remux runs
- **THEN** the video stream is copied without re-encoding (`-c:v copy`)

#### Scenario: Audio encoding

- **WHEN** remux runs
- **THEN** the new audio track is encoded as AAC at 192 kbps

#### Scenario: Subtitle track attachment

- **WHEN** remux runs with `subtitles_edited.srt`
- **THEN** the output video includes a subtitle track compatible with browser and VLC playback

### Requirement: Remux job execution

The system SHALL run audio assembly and video remux as a background job triggered via API or CLI.

#### Scenario: Start remux via API

- **WHEN** the client calls `POST /api/projects/{id}/remux`
- **THEN** the server enqueues a background job and returns HTTP 202 with status `remuxing`

#### Scenario: Remux without modified cues

- **WHEN** no cues are modified and the user triggers remux
- **THEN** the system assembles audio using only original `segments/` clips and proceeds with remux without requiring `tts_segments/`

#### Scenario: Remux progress

- **WHEN** a remux job is in progress
- **THEN** `GET /api/projects/{id}/remux-status` returns `status`, current stage (`assembling` or `muxing`), and progress percentage

#### Scenario: Remux failure

- **WHEN** ffmpeg remux fails
- **THEN** project status is set to `remux_failed` with an error message in `meta.json`

### Requirement: CLI remux command

The system SHALL provide `caption-helper remux <project-dir>` to rebuild output without the Web UI.

#### Scenario: CLI remux

- **WHEN** the user runs `caption-helper remux ~/.caption-helper/projects/<id>`
- **THEN** the system produces `output_audio.wav` and `output_video.mp4` in the project directory
