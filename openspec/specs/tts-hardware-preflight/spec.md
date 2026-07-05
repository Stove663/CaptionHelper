# tts-hardware-preflight

GPU and VRAM preflight checks before MOSS-TTS synthesis jobs.

## Requirements

### Requirement: GPU availability check

The system SHALL verify CUDA GPU availability before starting a TTS synthesis job.

#### Scenario: CUDA available

- **WHEN** a TTS synthesis job starts and `torch.cuda.is_available()` returns `True`
- **THEN** the preflight check passes and synthesis proceeds

#### Scenario: CUDA unavailable

- **WHEN** a TTS synthesis job starts and no CUDA GPU is detected
- **THEN** the system aborts with an error message stating that MOSS-TTS synthesis requires a CUDA GPU

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

### Requirement: Debian 12 platform support

The system SHALL document and support installation on Debian 12 with Nvidia T4 GPU.

#### Scenario: Debian dependencies documented

- **WHEN** a user follows the README install guide on Debian 12
- **THEN** the documentation covers `ffmpeg` via `apt`, NVIDIA driver installation, and MOSS-TTS Python dependencies via `uv pip install --torch-backend cu128 -e ".[tts]"`

#### Scenario: Preflight on Debian 12 T4

- **WHEN** the application runs on Debian 12 with a properly configured T4 GPU and CUDA drivers
- **THEN** preflight detects the T4, reports 16 GB VRAM, and allows the default 4B model

### Requirement: Dual-GPU deployment documentation

The system SHALL document running ASR and MOSS-TTS on separate CUDA devices for dual-T4 deployments.

#### Scenario: README dual-GPU example

- **WHEN** a user reads the MOSS-TTS setup section
- **THEN** the documentation shows `--device cuda:0` for ASR and `--tts-device cuda:1` with `--tts-model local-v1.5-4b` for TTS
