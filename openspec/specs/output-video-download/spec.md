# output-video-download Specification

## Purpose

Web UI and client-side helpers for reliably downloading the remuxed output video (`output_video.mp4`).

## Requirements

### Requirement: Preview page download button

The system SHALL expose a prominent "下载视频" control on the preview page toolbar when the project's remux output is ready.

#### Scenario: Button visible when output ready

- **WHEN** the project status is `remux_ready` and `output_video.mp4` exists
- **THEN** the preview page toolbar shows an enabled download button for the output video

#### Scenario: Button disabled before output ready

- **WHEN** `output_video.mp4` does not exist or remux has not completed
- **THEN** the download button is hidden or disabled with an explanatory label

#### Scenario: User triggers download from preview

- **WHEN** the user clicks "下载视频" on the preview page
- **THEN** the browser saves `output_video.mp4` to the user's downloads folder

#### Scenario: Download in progress feedback

- **WHEN** the user clicks "下载视频" and the file is being fetched
- **THEN** the button shows a loading state and is disabled until the download completes or fails

#### Scenario: Download failure

- **WHEN** the download request returns a non-2xx status or the network fails
- **THEN** the UI shows an error message and re-enables the download button

### Requirement: Project list quick download

The system SHALL provide a download shortcut on the home page project list for projects with completed remux output.

#### Scenario: Download link on ready projects

- **WHEN** a project in the list has status `remux_ready`
- **THEN** the project row includes a "下载" action that saves `output_video.mp4`

#### Scenario: No download for incomplete projects

- **WHEN** a project status is not `remux_ready`
- **THEN** the project row does not show a download action

### Requirement: Client-side download helper

The frontend SHALL implement video download via `fetch` of the output-video API, `Blob` construction, and a programmatic `<a download>` click so saving works consistently across browsers.

#### Scenario: Filename preserved

- **WHEN** a download is triggered programmatically
- **THEN** the saved file is named `output_video.mp4` (or the project's source basename with `_output.mp4` suffix if derived from project metadata)
