## MODIFIED Requirements

### Requirement: MOSS-TTS synthesis for modified segments

The system SHALL re-synthesize speech audio for every subtitle cue marked `modified: true` using MOSS-TTS voice cloning, and MUST NOT synthesize unmodified cues. Synthesis MUST support Chinese–English code-mixed `text_edited` content where users have replaced Chinese words with English equivalents.

#### Scenario: Synthesize only modified cues

- **WHEN** the user triggers synthesis and cues 2 and 5 are marked `modified: true` while other cues are unmodified
- **THEN** the system generates TTS audio only for cues 2 and 5

#### Scenario: Skip when no modifications

- **WHEN** the user triggers synthesis and no cues are modified
- **THEN** the system returns without generating any TTS files and reports zero segments synthesized

#### Scenario: Zh-en code-mixed text synthesis

- **WHEN** a modified cue has `text_edited` of "请大家打开 terminal 窗口" containing both Chinese and English
- **THEN** the system synthesizes speech that pronounces both the Chinese and English portions naturally without requiring the user to split the cue

#### Scenario: Pure Chinese text synthesis

- **WHEN** a modified cue has `text_edited` containing only Chinese characters
- **THEN** the system passes `language="Chinese"` to MOSS-TTS `build_user_message`

#### Scenario: Code-mixed text omits fixed language tag

- **WHEN** a modified cue is detected as zh-en code-mixed
- **THEN** the system calls `build_user_message` without a fixed `language` tag so MOSS-TTS handles code-switching automatically

### Requirement: Synthesis manifest

The system SHALL write `synthesis_manifest.json` recording metadata for each synthesized cue.

#### Scenario: Manifest contents

- **WHEN** synthesis completes for a modified cue
- **THEN** `synthesis_manifest.json` includes `index`, `spk`, `text_edited`, `reference_segment`, `target_duration_ms`, `tokens`, `output_path`, `status` (`success` or `failed`), `code_mixed`, `language_mode`, `model_id`, and `gpu_name`

### Requirement: MOSS-TTS model configuration

The system SHALL use `OpenMOSS-Team/MOSS-TTS-Local-Transformer` (1.7B) as the default TTS model, optimized for Nvidia T4 16 GB VRAM on Debian 12, with configurable `--tts-model` and `--tts-device` options.

#### Scenario: Default model on T4 16 GB

- **WHEN** synthesis runs without explicit model configuration on a GPU with ≤ 16 GB VRAM
- **THEN** the system loads `OpenMOSS-Team/MOSS-TTS-Local-Transformer` via `AutoModel` and `AutoProcessor` with `trust_remote_code=True`, `dtype=bfloat16`, and `attn_implementation=sdpa`

#### Scenario: Optional 4B model

- **WHEN** the user specifies `--tts-model OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5` and preflight detects ≥ 12 GB available VRAM
- **THEN** the system loads the 4B model and proceeds with synthesis

#### Scenario: Block 8B model on 16 GB GPU

- **WHEN** the user requests `OpenMOSS-Team/MOSS-TTS-v1.5` (8B) and preflight detects ≤ 16 GB total VRAM
- **THEN** the system rejects the request with an error recommending the 1.7B default model

#### Scenario: GPU device selection

- **WHEN** CUDA is available and no device is specified
- **THEN** the system uses `cuda:0` for MOSS-TTS inference

#### Scenario: T4 attention backend

- **WHEN** running on an Nvidia T4 GPU (compute capability 7.5)
- **THEN** the system uses `attn_implementation=sdpa` and does not attempt FlashAttention 2

## ADDED Requirements

### Requirement: Code-mix text detection

The system SHALL detect zh-en code-mixed subtitle text before calling MOSS-TTS to select the appropriate language handling mode.

#### Scenario: Detect mixed cue

- **WHEN** `text_edited` contains both CJK characters and Latin-alphabet words
- **THEN** the system classifies the cue as `code_mixed: true`

#### Scenario: Detect pure Chinese cue

- **WHEN** `text_edited` contains CJK characters and no Latin-alphabet words
- **THEN** the system classifies the cue as `code_mixed: false` with `language_mode: Chinese`
