## ADDED Requirements

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

### Requirement: Lecture and meeting content defaults

The system SHALL optimize defaults for lecture and meeting speech content: speech-dominant audio, sentence-level edits of one or two words, and no terminology glossary.

#### Scenario: No glossary feature

- **WHEN** the user edits subtitle text
- **THEN** the system does not require or offer a terminology glossary

#### Scenario: Audio base track for lecture content

- **WHEN** audio assembly runs for any sync mode
- **THEN** the system uses the full extracted `audio.wav` as the base track and overlays speech clips at cue positions
