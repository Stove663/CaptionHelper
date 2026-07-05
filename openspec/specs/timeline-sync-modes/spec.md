# timeline-sync-modes

Fixed-slot vs natural-pace timeline synchronization for TTS and remux.

## Requirements

### Requirement: Timeline sync mode selection

The system SHALL support two timeline sync modes per project: `fixed-slot` (default) and `natural-pace`.

#### Scenario: Default fixed-slot mode

- **WHEN** a new project is created
- **THEN** `meta.json` records `sync_mode: "fixed-slot"`

#### Scenario: User selects natural-pace mode

- **WHEN** the user selects natural-pace mode in the Web UI before synthesis
- **THEN** `meta.json` is updated to `sync_mode: "natural-pace"` and subsequent TTS and remux use the ripple pipeline

#### Scenario: Mode persisted across sessions

- **WHEN** the user reloads the editor for a project with `sync_mode: "natural-pace"`
- **THEN** the UI displays natural-pace as the active mode

### Requirement: Compression risk detection

The system SHALL detect modified cues where fixed-slot TTS compression would likely degrade quality and warn the user before synthesis.

#### Scenario: Low-risk edit proceeds silently

- **WHEN** a modified cue has estimated speech duration within 130% of its time slot
- **THEN** no compression warning is shown for that cue

#### Scenario: High-risk edit triggers warning

- **WHEN** a modified cue has estimated speech duration exceeding 130% of its time slot
- **THEN** the UI displays a warning identifying the cue index and offers fixed-slot or natural-pace options

#### Scenario: Zh-en mixed text estimation

- **WHEN** a modified cue contains both CJK and Latin characters
- **THEN** the compression estimate accounts for both character types using separate per-character duration heuristics

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

### Requirement: Lecture and meeting content defaults

The system SHALL optimize defaults for lecture and meeting speech content: speech-dominant audio, sentence-level edits of one or two words, and no terminology glossary.

#### Scenario: No glossary feature

- **WHEN** the user edits subtitle text
- **THEN** the system does not require or offer a terminology glossary

#### Scenario: Audio base track for lecture content

- **WHEN** audio assembly runs for any sync mode
- **THEN** the system uses the full extracted `audio.wav` as the base track and overlays speech clips at cue positions

### Requirement: GLM-TTS provider-aware natural-pace guidance

The system SHALL surface stronger natural-pace recommendations when `tts_provider=glm-tts`, the project uses `sync_mode=fixed-slot`, and the project has at least one modified code-mixed cue.

#### Scenario: Compression-risk API includes GLM guidance

- **WHEN** `GET /api/projects/{id}/compression-risk` is called for a project with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and one or more modified code-mixed cues
- **THEN** the response includes a `provider_guidance` string explaining that GLM-TTS has no duration token hint and fixed-slot mode may compress English pronunciation

#### Scenario: Code-mixed at-risk retains recommend_natural_pace

- **WHEN** a modified cue is code-mixed and compression-at-risk
- **THEN** the compression-risk cue entry includes `recommend_natural_pace: true` regardless of TTS provider

#### Scenario: Editor banner uses GLM-specific text

- **WHEN** the Web UI editor displays a compression banner for a project with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and code-mixed modified cues
- **THEN** the banner text states that GLM-TTS in fixed-slot mode may compress English words and recommends switching to natural-pace

#### Scenario: MOSS-TTS banner unchanged

- **WHEN** `tts_provider=moss-tts` and compression warnings are shown
- **THEN** the existing MOSS-oriented banner text and behavior apply without regression

#### Scenario: No automatic mode switch

- **WHEN** GLM-specific natural-pace guidance is displayed
- **THEN** the system does not change `sync_mode` in `meta.json` without explicit user action

### Requirement: GLM fixed-slot synthesis acknowledgment

The system SHALL allow users to proceed with GLM-TTS fixed-slot synthesis on code-mixed projects after displaying guidance, without forcing a sync mode change.

#### Scenario: Synthesis proceeds after warning

- **WHEN** the user initiates synthesis with `tts_provider=glm-tts`, `sync_mode=fixed-slot`, and code-mixed modified cues
- **THEN** the synthesis job MAY proceed after the UI has shown provider guidance (no hard block in v1)
