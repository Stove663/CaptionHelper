## MODIFIED Requirements

### Requirement: Inline subtitle editing

The system SHALL allow the user to edit subtitle text only for each cue in the editor. Timestamps (`start_ms`, `end_ms`) and speaker ID (`spk`) MUST be displayed as read-only and MUST NOT be editable in the UI.

#### Scenario: Edit cue text

- **WHEN** the user changes the text of cue index 3 and clicks Save
- **THEN** the updated text is persisted and reflected on reload

#### Scenario: Visual modified indicator

- **WHEN** a cue's edited text differs from its original ASR text
- **THEN** that cue displays a visual "modified" badge in the editor

#### Scenario: Timestamps are read-only

- **WHEN** the user views a cue in the editor
- **THEN** `start_ms` and `end_ms` are displayed as non-editable labels

#### Scenario: Speaker is read-only

- **WHEN** the user views a cue in the editor
- **THEN** the speaker label (`spk`) is displayed as a non-editable label

### Requirement: Save edited subtitles

The system SHALL persist user edits via `PUT /api/projects/{id}/subtitles` and regenerate `subtitles_edited.srt`. The API MUST reject requests that attempt to change `start_ms`, `end_ms`, or `spk` from their stored values.

#### Scenario: Successful save

- **WHEN** the user clicks Save with valid cue text changes only
- **THEN** the server writes updated `subtitles.json` and `subtitles_edited.srt` and returns HTTP 200

#### Scenario: Reject timestamp change

- **WHEN** the user submits a cue with `start_ms` or `end_ms` different from the stored value
- **THEN** the server returns HTTP 422 with a validation error indicating timestamps are immutable

#### Scenario: Reject speaker change

- **WHEN** the user submits a cue with `spk` different from the stored value
- **THEN** the server returns HTTP 422 with a validation error indicating speaker is immutable

## REMOVED Requirements

### Requirement: Invalid cue data

**Reason**: Timestamp validation on user input is no longer applicable because timestamps are read-only and cannot be submitted for editing.

**Migration**: Server-side validation now only checks text fields and rejects any attempt to modify immutable fields.
