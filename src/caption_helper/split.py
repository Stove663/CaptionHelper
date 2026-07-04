import subprocess
from pathlib import Path

from caption_helper.extract import check_ffmpeg
from caption_helper.models import Sentence


def segment_filename(index: int, sentence: Sentence) -> str:
    """Return segment WAV filename for a sentence."""
    return f"{index:04d}_spk{sentence.spk}_{sentence.start}-{sentence.end}.wav"


def split_segments(full_wav: Path, sentences: list[Sentence], segments_dir: Path) -> list[Path]:
    """Split full WAV into per-sentence clips aligned to timestamps."""
    ffmpeg = check_ffmpeg()
    full_wav = Path(full_wav)
    segments_dir = Path(segments_dir)
    segments_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for index, sentence in enumerate(sentences, start=1):
        output = segments_dir / segment_filename(index, sentence)
        start_s = sentence.start / 1000.0
        end_s = sentence.end / 1000.0
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(full_wav),
            "-ss",
            f"{start_s:.3f}",
            "-to",
            f"{end_s:.3f}",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed to split segment {index}:\n{result.stderr}"
            )
        outputs.append(output)
    return outputs
