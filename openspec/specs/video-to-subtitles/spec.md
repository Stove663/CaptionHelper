# video-to-subtitles Specification

## Purpose
TBD - created by archiving change funasr-video-subtitles-audio-split. Update Purpose after archive.
## Requirements
### Requirement: Video audio extraction

The system SHALL extract a mono 16 kHz PCM WAV file from any input video file supported by ffmpeg.

#### Scenario: Successful extraction from MP4

- **WHEN** the user provides a valid `.mp4` video file path
- **THEN** the system produces a `audio.wav` file in the output directory with exactly one audio channel and a 16000 Hz sample rate

#### Scenario: Missing ffmpeg

- **WHEN** ffmpeg is not available on the system PATH
- **THEN** the system exits with a non-zero status and an error message instructing the user to install ffmpeg

### Requirement: Diarized transcription with Fun-ASR-Nano

The system SHALL transcribe extracted audio using FunASR with Fun-ASR-Nano-2512, fsmn-vad, and cam++ speaker diarization, producing per-sentence text with speaker ID and millisecond timestamps.

#### Scenario: Successful FunASR transcription

- **WHEN** a valid 16 kHz mono WAV file is passed to the transcription step
- **THEN** the system returns a list of sentence records, each containing `text`, `spk` (integer speaker ID), `start` (ms), and `end` (ms)

#### Scenario: Long audio segmentation with FunASR

- **WHEN** the input audio exceeds the VAD maximum single-segment duration
- **THEN** the system segments the audio via fsmn-vad and still returns complete sentence records covering the full duration

### Requirement: SRT subtitle generation with speaker labels

The system SHALL write an SRT subtitle file where each cue corresponds to one diarized sentence, includes a speaker label prefix, and uses standard SRT timestamp format.

#### Scenario: SRT format and speaker prefix

- **WHEN** transcription produces sentence records with `spk=0`, `start=880`, `end=5195`, `text="欢迎大家"`
- **THEN** the first SRT cue has index `1`, timestamps `00:00:00,880 --> 00:00:05,195`, and text `[说话人 0] 欢迎大家`

#### Scenario: Multiple speakers

- **WHEN** transcription produces sentences from different speaker IDs
- **THEN** each SRT cue retains its own speaker label reflecting the `spk` value from that sentence

### Requirement: CLI process command

The system SHALL expose a `caption-helper process <video>` command that runs extraction, transcription, and SRT generation in sequence.

#### Scenario: End-to-end processing

- **WHEN** the user runs `caption-helper process meeting.mp4`
- **THEN** the system creates `meeting_output/subtitles.srt` and `meeting_output/audio.wav` containing diarized subtitles for the full video

#### Scenario: Custom output directory

- **WHEN** the user runs `caption-helper process meeting.mp4 --output-dir /tmp/out`
- **THEN** all generated files are written under `/tmp/out` instead of the default `<stem>_output/` directory

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

