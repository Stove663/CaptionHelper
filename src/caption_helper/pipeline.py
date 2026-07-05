import logging
from pathlib import Path

from caption_helper.extract import extract_audio
from caption_helper.split import split_segments
from caption_helper.srt import write_srt
from caption_helper.transcribe import TranscriberConfig, get_transcriber
from caption_helper.tts.reference import build_speaker_reference_bank

logger = logging.getLogger(__name__)


def default_output_dir(video_path: Path) -> Path:
    return video_path.parent / f"{video_path.stem}_output"


def process(
    video_path: Path,
    output_dir: Path | None = None,
    *,
    device: str | None = None,
    language: str = "中文",
    hub: str | None = None,
    max_single_segment_time: int = 30_000,
) -> Path:
    """Run extract → transcribe → SRT → split for one video file."""
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    out = Path(output_dir) if output_dir else default_output_dir(video_path)
    out.mkdir(parents=True, exist_ok=True)
    segments_dir = out / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    audio_wav = out / "audio.wav"
    subtitles_srt = out / "subtitles.srt"

    logger.info("Extracting audio from %s", video_path.name)
    extract_audio(video_path, audio_wav)

    logger.info("Transcribing audio with FunASR")
    transcriber = get_transcriber(
        TranscriberConfig(
            device=device,
            language=language,
            hub=hub,
            max_single_segment_time=max_single_segment_time,
        )
    )
    sentences = transcriber.transcribe(str(audio_wav))
    if not sentences:
        raise RuntimeError("Transcription returned no sentences")

    logger.info("Writing subtitles (%d cues)", len(sentences))
    write_srt(sentences, subtitles_srt)

    logger.info("Splitting audio into %d segments", len(sentences))
    split_segments(audio_wav, sentences, segments_dir)

    logger.info("Building speaker reference bank")
    build_speaker_reference_bank(out)

    logger.info("Done. Output: %s", out)
    return out
