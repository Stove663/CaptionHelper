## ADDED Requirements

### Requirement: Output preview page

The system SHALL provide a preview page at `/projects/{id}/preview` for reviewing the remuxed output video after remux completes.

#### Scenario: Preview available after remux

- **WHEN** a project's remux status is `remux_ready` and `output_video.mp4` exists
- **THEN** the user can navigate to the preview page and play the output video

#### Scenario: Preview blocked before remux

- **WHEN** `output_video.mp4` does not exist
- **THEN** the preview page shows a prompt to run "Build output" instead of a video player

### Requirement: In-browser video playback

The system SHALL stream `output_video.mp4` to the preview page video player.

#### Scenario: Stream output video

- **WHEN** the preview page loads and remux is complete
- **THEN** the video player requests `GET /api/projects/{id}/output-video` and plays the remuxed file

#### Scenario: Subtitle visibility during preview

- **WHEN** the user plays the output video in the preview page
- **THEN** the edited subtitles from `subtitles_edited.srt` are visible during playback (via embedded soft subtitle track or synchronized SRT overlay)

### Requirement: Build and rebuild controls

The system SHALL expose a "Build output" button on the preview page and editor to trigger remux.

#### Scenario: Trigger build from preview

- **WHEN** the user clicks "Build output" on the preview page
- **THEN** the system calls `POST /api/projects/{id}/remux` and shows remux progress

#### Scenario: Rebuild after further edits

- **WHEN** the user edits subtitles after a previous remux and clicks "Rebuild output"
- **THEN** the system re-runs assembly and remux, overwriting `output_audio.wav` and `output_video.mp4`

### Requirement: Download exported files

The system SHALL provide download links for the assembled output files on the preview page.

#### Scenario: Download output video

- **WHEN** remux is complete
- **THEN** the preview page offers a download link for `output_video.mp4`

#### Scenario: Download output audio

- **WHEN** remux is complete
- **THEN** the preview page offers a download link for `output_audio.wav`

### Requirement: Original vs output comparison

The system SHALL allow the user to switch between the original source video and the remuxed output video on the preview page for comparison.

#### Scenario: Toggle original and output

- **WHEN** the user clicks "Show original" on the preview page
- **THEN** the player switches to stream the source video (`source.mp4`) with original audio

#### Scenario: Switch back to output

- **WHEN** the user clicks "Show output" after viewing the original
- **THEN** the player switches back to `output_video.mp4`
