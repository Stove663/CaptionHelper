import shutil
import subprocess
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg is not available on PATH."""


def check_ffmpeg() -> str:
    """Return ffmpeg executable path or raise with install instructions."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise FFmpegNotFoundError(
            "ffmpeg is not installed or not on PATH. "
            "Install it first (e.g. `brew install ffmpeg` on macOS, "
            "`sudo apt-get install -y ffmpeg` on Debian/Ubuntu)."
        )
    return path


def extract_audio(video_path: Path, output_wav: Path) -> None:
    """Extract mono 16 kHz PCM WAV from a video file."""
    ffmpeg = check_ffmpeg()
    video_path = Path(video_path)
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed to extract audio from {video_path}:\n{result.stderr}"
        )
