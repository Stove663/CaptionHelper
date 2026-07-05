## ADDED Requirements

### Requirement: Output video download endpoint

The system SHALL expose `GET /api/projects/{id}/output-video` to serve the remuxed `output_video.mp4` file for download.

#### Scenario: Serve output video when ready

- **WHEN** the client requests `GET /api/projects/{id}/output-video` and `output_video.mp4` exists
- **THEN** the server responds with HTTP 200, `Content-Type: video/mp4`, and the file bytes

#### Scenario: Attachment disposition for download

- **WHEN** the client requests `GET /api/projects/{id}/output-video` for download
- **THEN** the response includes `Content-Disposition: attachment` with filename `output_video.mp4`

#### Scenario: Output not ready

- **WHEN** `output_video.mp4` does not exist
- **THEN** the server responds with HTTP 404 and a descriptive error body
