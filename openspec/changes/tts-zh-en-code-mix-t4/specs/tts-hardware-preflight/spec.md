## ADDED Requirements

### Requirement: GPU availability check

The system SHALL verify CUDA GPU availability before starting a TTS synthesis job.

#### Scenario: CUDA available

- **WHEN** a TTS synthesis job starts and `torch.cuda.is_available()` returns `True`
- **THEN** the preflight check passes and synthesis proceeds

#### Scenario: CUDA unavailable

- **WHEN** a TTS synthesis job starts and no CUDA GPU is detected
- **THEN** the system aborts with an error message stating that MOSS-TTS synthesis requires a CUDA GPU

### Requirement: VRAM compatibility gating

The system SHALL check total GPU VRAM against the requested TTS model and block incompatible combinations.

#### Scenario: T4 16 GB with default 1.7B model

- **WHEN** preflight detects an Nvidia GPU with 16 GB total VRAM and the default 1.7B model is selected
- **THEN** the preflight check passes

#### Scenario: 16 GB GPU blocks 8B model

- **WHEN** preflight detects ≤ 16 GB total VRAM and the user requests MOSS-TTS-v1.5 (8B)
- **THEN** the system returns an error recommending `MOSS-TTS-Local-Transformer` (1.7B)

#### Scenario: 4B model requires sufficient VRAM

- **WHEN** the user requests MOSS-TTS-Local-Transformer-v1.5 (4B) and available VRAM is below 12 GB
- **THEN** the system returns an error recommending the 1.7B default model

### Requirement: GPU info logging

The system SHALL log GPU name, total VRAM, and CUDA version at synthesis startup for diagnostics on Debian 12 deployments.

#### Scenario: Log GPU details

- **WHEN** preflight runs successfully
- **THEN** the log output includes GPU device name (e.g., "Tesla T4"), total VRAM in GB, and CUDA version

### Requirement: Debian 12 platform support

The system SHALL document and support installation on Debian 12 with Nvidia T4 GPU.

#### Scenario: Debian dependencies documented

- **WHEN** a user follows the README install guide on Debian 12
- **THEN** the documentation covers `ffmpeg` via `apt`, NVIDIA driver installation, and MOSS-TTS Python dependencies via `uv pip install --torch-backend cu128 -e ".[tts]"`

#### Scenario: Preflight on Debian 12 T4

- **WHEN** the application runs on Debian 12 with a properly configured T4 GPU and CUDA drivers
- **THEN** preflight detects the T4, reports 16 GB VRAM, and allows the default 1.7B model
