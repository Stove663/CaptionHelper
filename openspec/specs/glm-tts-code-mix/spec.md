# glm-tts-code-mix

GLM-TTS phoneme-in, mixed-text preprocessing, and manifest metadata for zh-en code-mixed subtitle synthesis.

## Requirements

### Requirement: GLM phoneme-in auto mode for code-mixed cues

The system SHALL enable GLM-TTS Phoneme-in (`use_phoneme=True`) for synthesis when the project `glm_phoneme_mode` is `on`, or when `glm_phoneme_mode` is `auto` (default) and the cue `text_edited` is classified as code-mixed.

#### Scenario: Auto mode enables phoneme for mixed cue

- **WHEN** `tts_provider=glm-tts`, `glm_phoneme_mode=auto`, and `text_edited` contains both CJK and Latin words
- **THEN** the GLM synthesis path calls `load_models(use_phoneme=True)` and `generate_long(use_phoneme=True)` for that cue

#### Scenario: Auto mode disables phoneme for pure Chinese cue

- **WHEN** `tts_provider=glm-tts`, `glm_phoneme_mode=auto`, and `text_edited` is not code-mixed
- **THEN** the GLM synthesis path uses `use_phoneme=False` for that cue

#### Scenario: Project forces phoneme off

- **WHEN** `glm_phoneme_mode=off`
- **THEN** all GLM cues synthesize with `use_phoneme=False` regardless of code-mix classification

#### Scenario: Project forces phoneme on

- **WHEN** `glm_phoneme_mode=on`
- **THEN** all GLM cues synthesize with `use_phoneme=True` regardless of code-mix classification

### Requirement: GLM mixed-text preprocessing

The system SHALL apply mixed-text preprocessing to `text_edited` before GLM `text_normalize` when the cue is code-mixed.

#### Scenario: CJK-Latin boundary spacing

- **WHEN** a code-mixed cue text lacks whitespace between a CJK character and a Latin word (e.g. `打开terminal`)
- **THEN** the text passed to GLM normalizes boundaries to include a space (e.g. `打开 terminal`)

#### Scenario: Pure Chinese cue skips prep

- **WHEN** a cue is not code-mixed
- **THEN** mixed-text preprocessing is not applied

### Requirement: GLM code-mix synthesis manifest metadata

The system SHALL record GLM code-mix processing metadata in `synthesis_manifest.json` for each cue when `tts_provider=glm-tts`.

#### Scenario: Manifest records phoneme and prep flags

- **WHEN** GLM-TTS synthesis completes for a cue
- **THEN** the cue entry includes `phoneme_enabled` (bool), `text_prep_applied` (bool), and `glm_phoneme_mode` (string snapshot of project setting)

#### Scenario: Manifest retains code-mix classification

- **WHEN** any TTS provider synthesizes a cue
- **THEN** the cue entry continues to include `code_mixed` and `language_mode` as defined by existing synthesis requirements

### Requirement: GLM phoneme mode project setting

The system SHALL persist `glm_phoneme_mode` in project `meta.json` with allowed values `auto`, `on`, or `off`, defaulting to `auto` for existing and new projects.

#### Scenario: Default phoneme mode

- **WHEN** a project is loaded and `glm_phoneme_mode` is absent
- **THEN** the system treats the project as `glm_phoneme_mode=auto`
