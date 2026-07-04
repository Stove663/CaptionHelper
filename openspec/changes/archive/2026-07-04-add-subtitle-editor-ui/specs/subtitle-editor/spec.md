## ADDED Requirements

### Requirement: Subtitle editor page

The system SHALL provide a browser-based subtitle editor accessible at `/projects/{id}/edit` after ASR processing completes.

#### Scenario: Editor loads after processing

- **WHEN** a project's status is `ready`
- **THEN** the user can navigate to the editor and see all subtitle cues with text, speaker label, and timestamps

#### Scenario: Editor blocked during processing

- **WHEN** a project's status is not `ready`
- **THEN** the editor displays a processing indicator instead of editable cues

### Requirement: Video playback synchronization

The system SHALL synchronize video playback with subtitle cues in the editor.

#### Scenario: Cue click seeks video

- **WHEN** the user clicks a subtitle cue in the editor
- **THEN** the video player seeks to that cue's `start_ms` timestamp and pauses

#### Scenario: Active cue highlight during playback

- **WHEN** the video is playing
- **THEN** the cue whose time range contains the current playback position is visually highlighted

### Requirement: Inline subtitle editing

The system SHALL allow the user to edit subtitle text, speaker ID, and timestamps for each cue in the editor.

#### Scenario: Edit cue text

- **WHEN** the user changes the text of cue index 3 and clicks Save
- **THEN** the updated text is persisted and reflected on reload

#### Scenario: Visual modified indicator

- **WHEN** a cue's edited text differs from its original ASR text
- **THEN** that cue displays a visual "modified" badge in the editor

### Requirement: Original text comparison

The system SHALL allow the user to view the original ASR text alongside or on demand for each cue.

#### Scenario: View original text

- **WHEN** the user hovers over or toggles "show original" on a modified cue
- **THEN** the original ASR text (`text_original`) is displayed for comparison

### Requirement: Save edited subtitles

The system SHALL persist user edits via `PUT /api/projects/{id}/subtitles` and regenerate `subtitles_edited.srt`.

#### Scenario: Successful save

- **WHEN** the user clicks Save with valid cue data
- **THEN** the server writes updated `subtitles.json` and `subtitles_edited.srt` and returns HTTP 200

#### Scenario: Invalid cue data

- **WHEN** the user submits a cue with `end_ms` before `start_ms`
- **THEN** the server returns HTTP 422 with a validation error
