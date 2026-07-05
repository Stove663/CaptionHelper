## ADDED Requirements

### Requirement: MOSS-Audio transcription backend

The system SHALL provide a MOSS-Audio-based transcription backend that loads `MOSS-Audio-4B-Instruct` (or a configured override) and transcribes a mono WAV file into `Sentence` records.

#### Scenario: Successful MOSS-Audio transcription

- **WHEN** `asr_provider` is `moss-audio` and a valid audio file is passed to the transcription step
- **THEN** the system returns a non-empty list of `Sentence` records, each containing `text`, `spk` (integer speaker ID), `start` (ms), and `end` (ms)

#### Scenario: Optional extra not installed

- **WHEN** `asr_provider` is `moss-audio` and the `[moss-audio]` optional dependencies are not installed
- **THEN** the system fails with a clear error instructing the user to install the extra

#### Scenario: CUDA required for MOSS-Audio

- **WHEN** `asr_provider` is `moss-audio` and no CUDA device is available
- **THEN** the system fails before model load with an error explaining GPU is required

### Requirement: MOSS-Audio model download defaults to ModelScope

The MOSS-Audio backend SHALL download model weights from ModelScope (`openmoss/MOSS-Audio-4B-Instruct`) by default. The system SHALL use HuggingFace Hub (respecting `HF_ENDPOINT` / hf-mirror bootstrap) only when the user explicitly sets `--hub hf` on the CLI or an equivalent web pipeline hub override.

#### Scenario: Default MOSS-Audio model download

- **WHEN** MOSS-Audio transcription runs without a HuggingFace hub override
- **THEN** model weights are fetched from ModelScope

#### Scenario: HuggingFace hub override

- **WHEN** the user sets `--hub hf` on the CLI or the web pipeline hub override to HuggingFace
- **THEN** MOSS-Audio loads weights from HuggingFace Hub instead of ModelScope

### Requirement: MOSS-Audio long audio chunking

The MOSS-Audio backend SHALL split input audio longer than a configurable maximum duration into sequential chunks, transcribe each chunk, and merge results with timestamp offsets so the combined `Sentence` list covers the full audio duration.

#### Scenario: Long audio produces full coverage

- **WHEN** input audio exceeds the configured chunk duration
- **THEN** merged `Sentence` records span from the start of the first chunk through the end of the last chunk without gaps

### Requirement: MOSS-Audio diarization fallback

When MOSS-Audio structured speaker output cannot be parsed, the backend SHALL still return timestamped sentences with `spk=0` for all cues and log a warning, rather than failing the entire transcription.

#### Scenario: Parse failure degrades gracefully

- **WHEN** MOSS-Audio returns text that does not match the expected structured speaker format
- **THEN** the system produces `Sentence` records with `spk=0` and emits a warning in logs
