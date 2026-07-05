## MODIFIED Requirements

### Requirement: Diarized transcription with Fun-ASR-Nano

The system SHALL transcribe extracted audio using the project's selected ASR provider (`funasr` or `moss-audio`), producing per-sentence text with speaker ID and millisecond timestamps. When the provider is `funasr`, the system SHALL use FunASR with Fun-ASR-Nano-2512, fsmn-vad, and cam++ speaker diarization. When the provider is `moss-audio`, the system SHALL use the MOSS-Audio backend defined in `moss-audio-asr`.

#### Scenario: Successful FunASR transcription

- **WHEN** `asr_provider` is `funasr` and a valid 16 kHz mono WAV file is passed to the transcription step
- **THEN** the system returns a list of sentence records, each containing `text`, `spk` (integer speaker ID), `start` (ms), and `end` (ms)

#### Scenario: Successful MOSS-Audio transcription

- **WHEN** `asr_provider` is `moss-audio` and a valid 16 kHz mono WAV file is passed to the transcription step
- **THEN** the system returns a list of sentence records, each containing `text`, `spk` (integer speaker ID), `start` (ms), and `end` (ms)

#### Scenario: Long audio segmentation with FunASR

- **WHEN** `asr_provider` is `funasr` and the input audio exceeds the VAD maximum single-segment duration
- **THEN** the system segments the audio via fsmn-vad and still returns complete sentence records covering the full duration

### Requirement: ASR model hub defaults to ModelScope

The transcription pipeline SHALL download ASR model weights from ModelScope by default for the active provider. For FunASR, this includes Fun-ASR-Nano, fsmn-vad, and cam++. For MOSS-Audio, this includes `openmoss/MOSS-Audio-4B-Instruct`. The system SHALL use HuggingFace Hub only when the user explicitly sets `--hub hf` on the CLI or a web pipeline hub override.

#### Scenario: Default FunASR model download

- **WHEN** the user runs `caption-helper process <video>` with `asr_provider` `funasr` (explicit or default) and without `--hub hf`
- **THEN** FunASR loads models from ModelScope rather than HuggingFace

#### Scenario: Default MOSS-Audio model download

- **WHEN** transcription runs with `asr_provider` `moss-audio` and without a HuggingFace hub override
- **THEN** MOSS-Audio loads models from ModelScope rather than HuggingFace

#### Scenario: Overseas HuggingFace hub

- **WHEN** the user runs `caption-helper process <video> --hub hf`
- **THEN** the active ASR provider downloads models from HuggingFace Hub instead of ModelScope

#### Scenario: Web UI ASR without hub override

- **WHEN** a video is uploaded via the web UI and no hub override is configured
- **THEN** background ASR processing uses ModelScope as the model hub for the project's selected ASR provider
