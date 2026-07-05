## MODIFIED Requirements

### Requirement: MOSS-TTS model configuration

The system SHALL use `OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5` (4B) as the default TTS model when the configured TTS GPU has at least 12 GB total VRAM, with `OpenMOSS-Team/MOSS-TTS-Local-Transformer` (1.7B) available via `--tts-model local-1.7b`, and configurable `--tts-device` on Debian 12 with Nvidia T4-class GPUs.

#### Scenario: Default 4B model on capable GPU

- **WHEN** synthesis runs without explicit model configuration and preflight detects at least 12 GB VRAM on the configured TTS device
- **THEN** the system loads `OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5` via `AutoModel` and `AutoProcessor` with `trust_remote_code=True`, `dtype=bfloat16`, and `attn_implementation=sdpa`

#### Scenario: Fallback 1.7B preset

- **WHEN** the user specifies `--tts-model local-1.7b`
- **THEN** the system loads `OpenMOSS-Team/MOSS-TTS-Local-Transformer` regardless of the 4B default

#### Scenario: Block 8B model on 16 GB GPU

- **WHEN** the user requests `OpenMOSS-Team/MOSS-TTS-v1.5` (8B) and preflight detects ≤ 16 GB total VRAM on the TTS device
- **THEN** the system rejects the request with an error recommending the 4B default model

#### Scenario: GPU device selection

- **WHEN** CUDA is available and `--tts-device cuda:1` is specified
- **THEN** the system loads and runs MOSS-TTS on `cuda:1`

#### Scenario: T4 attention backend

- **WHEN** running on an Nvidia T4 GPU (compute capability 7.5)
- **THEN** the system uses `attn_implementation=sdpa` and does not attempt FlashAttention 2

### Requirement: Synthesis manifest

The system SHALL write `synthesis_manifest.json` recording metadata for each synthesized cue.

#### Scenario: Manifest contents

- **WHEN** synthesis completes for a modified cue
- **THEN** `synthesis_manifest.json` includes `index`, `spk`, `text_edited`, `reference_segment`, `target_duration_ms`, `tokens`, `tokens_per_second`, `output_path`, `status` (`success` or `failed`), `code_mixed`, `language_mode`, `model_id`, and `gpu_name`

## ADDED Requirements

### Requirement: MOSS-TTS pipeline sample rate normalization

The system SHALL resample and downmix MOSS-TTS synthesized audio to 16 kHz mono before writing cue output files used by duration fitting and remux.

#### Scenario: v1.5 48 kHz stereo output normalized

- **WHEN** MOSS-TTS generates 48 kHz stereo audio for a modified cue
- **THEN** the saved `tts_segments/` WAV is 16 kHz mono at the pipeline sample rate

#### Scenario: Native rate already matches pipeline

- **WHEN** the model outputs audio at 16 kHz mono
- **THEN** the system saves the file without unnecessary resampling

### Requirement: Model-specific token duration mapping

The system SHALL use model-appropriate `tokens_per_second` defaults when mapping cue slot duration to MOSS-TTS `tokens` in fixed-slot mode.

#### Scenario: 4B v1.5 default token rate

- **WHEN** the active model is `OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5` and sync mode is `fixed-slot`
- **THEN** the system uses a default `tokens_per_second` of 12.5 unless overridden by CLI

#### Scenario: 1.7B preset retains existing mapping

- **WHEN** the active model is `OpenMOSS-Team/MOSS-TTS-Local-Transformer` and sync mode is `fixed-slot`
- **THEN** the system uses a default `tokens_per_second` of 25.0 unless overridden by CLI

#### Scenario: CLI override

- **WHEN** the user passes `--tokens-per-second 20`
- **THEN** synthesis uses 20 for token mapping regardless of model preset
