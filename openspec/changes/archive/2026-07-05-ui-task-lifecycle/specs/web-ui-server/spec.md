## ADDED Requirements

### Requirement: Project deletion API

The system SHALL expose `DELETE /api/projects/{id}` to permanently remove a project and all on-disk artifacts.

#### Scenario: Delete returns no content

- **WHEN** the client calls `DELETE /api/projects/{id}` for an existing, non-processing project
- **THEN** the server responds with HTTP 204 and removes the project directory

#### Scenario: Delete unknown project

- **WHEN** the client calls `DELETE /api/projects/{id}` for a non-existent project ID
- **THEN** the server responds with HTTP 404

#### Scenario: Delete busy project

- **WHEN** the client calls `DELETE /api/projects/{id}` while the project has an in-progress job
- **THEN** the server responds with HTTP 409

### Requirement: Project list excludes deleted projects

The system SHALL only include projects whose directories exist on disk in `GET /api/projects` responses.

#### Scenario: List after deletion

- **WHEN** a project is deleted manually or by expiration cleanup
- **THEN** subsequent `GET /api/projects` responses do not include that project
