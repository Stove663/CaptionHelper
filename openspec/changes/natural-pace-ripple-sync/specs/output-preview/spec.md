## MODIFIED Requirements

### Requirement: Build and rebuild controls

The system SHALL expose sync mode selection and compression warnings on the preview and editor pages before triggering synthesis and remux.

#### Scenario: Compression warning before synthesis

- **WHEN** modified cues have `compression_risk: true` and `sync_mode` is `fixed-slot`
- **THEN** the UI shows a warning with options to proceed with fixed-slot or switch to natural-pace

#### Scenario: Ripple duration preview

- **WHEN** the user selects natural-pace and TTS synthesis completes
- **THEN** the preview page shows total duration change before remux (e.g., "+3.5 s")

#### Scenario: Slow-down warning before remux

- **WHEN** natural-pace remux would slow any video segment below 0.75x
- **THEN** the UI warns the user and requires confirmation before proceeding

### Requirement: Original vs output comparison

The system SHALL allow comparison between original and output video, displaying which sync mode was used.

#### Scenario: Output shows sync mode

- **WHEN** the user views the output preview
- **THEN** the page displays the active `sync_mode` (`fixed-slot` or `natural-pace`)
