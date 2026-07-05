## ADDED Requirements

### Requirement: ASR model hub defaults to ModelScope

The transcription pipeline SHALL download FunASR models (Fun-ASR-Nano, fsmn-vad, cam++) from ModelScope by default. The system SHALL pass `hub="hf"` to FunASR only when the user explicitly sets `--hub hf` on the CLI or web pipeline options.

#### Scenario: Default ASR model download

- **WHEN** the user runs `caption-helper process <video>` without `--hub hf`
- **THEN** FunASR loads models from ModelScope (China-accessible hub) rather than HuggingFace

#### Scenario: Overseas HuggingFace hub

- **WHEN** the user runs `caption-helper process <video> --hub hf`
- **THEN** FunASR downloads models from HuggingFace Hub instead of ModelScope

#### Scenario: Web UI ASR without hub override

- **WHEN** a video is uploaded via the web UI and no hub override is configured
- **THEN** background ASR processing uses ModelScope as the model hub
