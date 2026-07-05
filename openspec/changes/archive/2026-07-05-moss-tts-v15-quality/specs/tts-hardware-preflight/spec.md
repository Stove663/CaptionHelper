## MODIFIED Requirements

### Requirement: VRAM compatibility gating

The system SHALL check total GPU VRAM on the **configured TTS device** against the requested TTS model and block incompatible combinations.

#### Scenario: T4 16 GB with default 4B model

- **WHEN** preflight detects an Nvidia GPU with at least 12 GB total VRAM on the configured TTS device and the default 4B model is selected
- **THEN** the preflight check passes

#### Scenario: 16 GB GPU blocks 8B model

- **WHEN** preflight detects ≤ 16 GB total VRAM on the TTS device and the user requests MOSS-TTS-v1.5 (8B)
- **THEN** the system returns an error recommending `MOSS-TTS-Local-Transformer-v1.5` (4B)

#### Scenario: 4B model requires sufficient VRAM

- **WHEN** the user requests MOSS-TTS-Local-Transformer-v1.5 (4B) and the TTS device has below 12 GB total VRAM
- **THEN** the system returns an error recommending the 1.7B preset

#### Scenario: Insufficient VRAM on secondary GPU

- **WHEN** `--tts-device cuda:1` is configured and device 1 has below 12 GB VRAM while device 0 has 16 GB
- **THEN** preflight evaluates device 1 only and blocks 4B synthesis with a device-specific error message

### Requirement: GPU info logging

The system SHALL log GPU name, total VRAM, CUDA device index, and CUDA version for the **TTS device** at synthesis startup.

#### Scenario: Log TTS GPU details

- **WHEN** preflight runs successfully for `--tts-device cuda:1`
- **THEN** the log output includes device index `1`, GPU device name (e.g., "Tesla T4"), total VRAM in GB, and CUDA version

## ADDED Requirements

### Requirement: Dual-GPU deployment documentation

The system SHALL document running ASR and MOSS-TTS on separate CUDA devices for dual-T4 deployments.

#### Scenario: README dual-GPU example

- **WHEN** a user reads the MOSS-TTS setup section
- **THEN** the documentation shows `--device cuda:0` for ASR and `--tts-device cuda:1` with `--tts-model local-v1.5-4b` for TTS
