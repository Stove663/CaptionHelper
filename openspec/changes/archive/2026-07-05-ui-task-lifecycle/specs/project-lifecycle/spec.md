## ADDED Requirements

### Requirement: Manual project deletion

The system SHALL allow users to permanently delete a project and all associated files from the Web UI, leaving no retained metadata or artifacts.

#### Scenario: Successful deletion

- **WHEN** the user confirms deletion for a project that is not processing
- **THEN** the system removes the entire project directory under `data-dir/projects/{id}/` and the project no longer appears in `GET /api/projects`

#### Scenario: Deleted project returns not found

- **WHEN** a client requests any project API for a deleted project ID
- **THEN** the server responds with HTTP 404

#### Scenario: Deletion requires confirmation in UI

- **WHEN** the user clicks delete on the home page
- **THEN** the UI presents a confirmation dialog describing that all data will be permanently removed before calling the delete API

### Requirement: Deletion blocked during processing

The system SHALL reject deletion requests while a project has an in-progress pipeline, synthesis, reference, or remux job.

#### Scenario: Processing project cannot be deleted

- **WHEN** the client calls `DELETE /api/projects/{id}` and the project status indicates active processing
- **THEN** the server responds with HTTP 409 and an error message indicating the project is busy

### Requirement: Automatic project expiration

The system SHALL automatically delete projects that are older than 7 days based on `created_at`, using the same complete removal as manual deletion.

#### Scenario: Expired project is purged

- **WHEN** a project's `created_at` is more than 7 days before the current UTC time and the project is not processing
- **THEN** the background cleanup removes the project directory entirely

#### Scenario: Recent project is retained

- **WHEN** a project's `created_at` is within the last 7 days
- **THEN** the background cleanup does not delete the project

#### Scenario: Processing project is skipped by cleanup

- **WHEN** an expired project's status indicates active processing
- **THEN** the background cleanup skips deletion until processing completes or the project becomes idle/failed

### Requirement: Background cleanup scheduler

The system SHALL run project expiration cleanup periodically while the Web server is running, without requiring a separate daemon process.

#### Scenario: Cleanup runs on interval

- **WHEN** the Web server is running
- **THEN** expiration cleanup executes on a fixed interval (default: once per hour)

#### Scenario: Cleanup at server startup

- **WHEN** the Web server starts
- **THEN** an initial expiration scan runs shortly after startup
