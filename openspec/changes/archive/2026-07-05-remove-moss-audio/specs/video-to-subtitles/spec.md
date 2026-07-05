## MODIFIED Requirements

### Requirement: Diarized transcription with Fun-ASR-Nano

The system SHALL transcribe extracted audio using FunASR with Fun-ASR-Nano-2512, fsmn-vad, and cam++ speaker diarization, producing per-sentence text with speaker ID and millisecond timestamps.

#### Scenario: Successful FunASR transcription

- **WHEN** a valid 16 kHz mono WAV file is passed to the transcription step
- **THEN** the system returns a list of sentence records, each containing `text`, `spk` (integer speaker ID), `start` (ms), and `end` (ms)

#### Scenario: Long audio segmentation with FunASR

- **WHEN** the input audio exceeds the VAD maximum single-segment duration
- **THEN** the system segments the audio via fsmn-vad and still returns complete sentence records covering the full duration

### Requirement: ASR model hub defaults to ModelScope

The transcription pipeline SHALL download FunASR model weights from ModelScope by default, including Fun-ASR-Nano, fsmn-vad, and cam++. The system SHALL use HuggingFace Hub only when the user explicitly sets `--hub hf` on the CLI or a web pipeline hub override.

#### Scenario: Default FunASR model download

- **WHEN** the user runs `caption-helper process <video>` without `--hub hf`
- **THEN** FunASR loads models from ModelScope rather than HuggingFace

#### Scenario: Overseas HuggingFace hub

- **WHEN** the user runs `caption-helper process <video> --hub hf`
- **THEN** FunASR downloads models from HuggingFace Hub instead of ModelScope

#### Scenario: Web UI ASR without hub override

- **WHEN** a video is uploaded via the web UI and no hub override is configured
- **THEN** background ASR processing uses ModelScope as the model hub
