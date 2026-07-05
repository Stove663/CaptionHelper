## ADDED Requirements

### Requirement: Code-mixed compression guidance

The system SHALL identify modified cues that are both zh-en code-mixed and compression-at-risk, and recommend natural-pace mode before fixed-slot synthesis.

#### Scenario: Code-mixed high-risk cue flagged

- **WHEN** a modified cue is classified as code-mixed and its estimated speech duration exceeds 130% of its time slot
- **THEN** the compression-risk response includes `recommend_natural_pace: true`

#### Scenario: Pure Chinese high-risk cue unchanged

- **WHEN** a modified cue is not code-mixed but exceeds the compression threshold
- **THEN** the compression-risk response includes `recommend_natural_pace: false` and the existing compression warning behavior applies

#### Scenario: Editor shows code-mixed recommendation

- **WHEN** the user views compression warnings for a code-mixed high-risk cue in the Web UI
- **THEN** the UI displays text recommending natural-pace mode to preserve English word pronunciation quality

#### Scenario: No automatic mode switch

- **WHEN** code-mixed high-risk cues are detected
- **THEN** the system does not change `sync_mode` in `meta.json` without explicit user action
