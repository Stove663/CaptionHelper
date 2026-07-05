# architecture-stabilization

## Purpose
Stabilize the CaptionHelper backend architecture so project lifecycle, pipeline execution, storage contracts, and cleanup behavior remain evolvable without accumulating workflow and state-management technical debt.

## Requirements

### Requirement: Unified project domain model

The system SHALL define a single source of truth for project lifecycle state, pipeline stage, sync mode, TTS provider, and GLM phoneme mode, with validation centralized in the domain layer.

#### Scenario: Project metadata uses canonical enums

- **WHEN** project metadata is created or loaded
- **THEN** lifecycle state, sync mode, TTS provider, and GLM phoneme mode are validated against canonical domain values before use

#### Scenario: Invalid metadata is rejected early

- **WHEN** persisted project metadata contains an unsupported state or option value
- **THEN** the system fails fast with a validation error instead of propagating the invalid value into pipeline logic

#### Scenario: Default values are centrally defined

- **WHEN** a new project is created or legacy metadata is loaded without optional fields
- **THEN** the system applies defaults from the domain model rather than duplicating fallback logic across storage and jobs

### Requirement: Explicit project state transition rules

The system SHALL route all project status changes through a single transition mechanism that enforces allowed state changes and records the reason for the change.

#### Scenario: Allowed transitions succeed

- **WHEN** a project moves from upload to processing and then to ready or failed
- **THEN** the transition is accepted only if it is allowed by the lifecycle rules

#### Scenario: Illegal transitions are blocked

- **WHEN** code attempts to transition a project from a terminal state back into an incompatible active state without a rerun action
- **THEN** the transition is rejected and the project metadata is not mutated

#### Scenario: Transition reasons are retained

- **WHEN** a state transition occurs because of success, failure, or rerun request
- **THEN** the system records the trigger or reason alongside the new state for debugging and auditability

### Requirement: Pipeline orchestration is separated from transport and persistence

The system SHALL keep HTTP handlers, project storage, and pipeline execution in separate layers so workflow changes do not require Web route rewrites or storage refactors.

#### Scenario: Web layer delegates to application services

- **WHEN** a request starts upload processing, synthesis, remux, or rerun work
- **THEN** the Web API calls an application service instead of implementing pipeline steps inline

#### Scenario: Pipeline services are individually testable

- **WHEN** a developer tests extraction, transcription, reference building, synthesis, or remux behavior
- **THEN** each service can be exercised without starting the FastAPI application

#### Scenario: Job runner is scheduling-only

- **WHEN** background work is queued
- **THEN** the job runner is responsible for dispatch and concurrency control, not for embedding all business-stage implementation details

### Requirement: Storage contract is versioned and manifest-driven

The system SHALL version project metadata and stage artifacts so on-disk file contracts can evolve safely.

#### Scenario: Metadata schema version is stored

- **WHEN** project metadata is written
- **THEN** the metadata includes a schema version field that can be used for future migrations

#### Scenario: Stage outputs are manifestable

- **WHEN** a pipeline stage produces artifacts
- **THEN** the stage writes or updates a manifest that lists expected inputs, outputs, and versioned metadata for that stage

#### Scenario: Missing artifacts are detected via contract checks

- **WHEN** a later stage or API depends on a prior artifact set
- **THEN** the system validates the presence and freshness of the required artifacts before continuing

### Requirement: Progress and job state are persisted beyond process memory

The system SHALL persist job progress and terminal job outcomes so pipeline status survives process restarts and does not rely solely on in-memory dictionaries.

#### Scenario: Progress survives restart

- **WHEN** a pipeline job is in progress and the process restarts
- **THEN** the project retains the last known stage and progress snapshot in persistent project metadata or a dedicated job record

#### Scenario: Terminal errors are durable

- **WHEN** a job fails
- **THEN** the failure state and error message are stored durably and remain visible after the server restarts

### Requirement: Cleanup and deletion use safe lifecycle policy

The system SHALL separate hard deletion from retention cleanup and ensure project removal is governed by explicit lifecycle policy rather than ad hoc directory scans.

#### Scenario: Expiration cleanup skips active work

- **WHEN** cleanup evaluates a project that is currently processing or queued for synthesis, references, or remux
- **THEN** the project is retained until it is idle or terminal

#### Scenario: Deletion supports recovery strategy

- **WHEN** a user deletes a project or cleanup removes an expired project
- **THEN** the removal path is compatible with a soft-delete or quarantine strategy so accidental loss can be reduced in future iterations

#### Scenario: Cleanup policy is centrally configured

- **WHEN** retention behavior is applied
- **THEN** the retention window, cleanup interval, and deletion strategy are read from a single policy source instead of being hard-coded in multiple modules

### Requirement: Background execution model is explicit

The system SHALL document and enforce the concurrency model for background jobs so async code, thread-pool work, and serial execution do not conflict implicitly.

#### Scenario: Single execution model is declared

- **WHEN** developers add a new background pipeline operation
- **THEN** they can determine whether it runs on the event loop, in the thread pool, or in a dedicated worker path from the application service boundary

#### Scenario: Concurrency limits are intentional

- **WHEN** multiple jobs are submitted
- **THEN** the system enforces concurrency limits through a clearly named scheduler or lock strategy rather than relying on accidental serialization

#### Scenario: Blocking work stays off the event loop

- **WHEN** CPU-bound or blocking external tool execution is triggered
- **THEN** the work is isolated from the request event loop so API responsiveness is preserved
