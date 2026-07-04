from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import soundfile as sf

from caption_helper.extract import check_ffmpeg


def ms_to_tokens(duration_ms: int, *, tokens_per_second: float = 25.0) -> int:
    """Map cue slot duration to MOSS-TTS token count."""
    return max(1, int((duration_ms / 1000.0) * tokens_per_second))


def wav_duration_ms(path: Path) -> int:
    info = sf.info(str(path))
    return int(info.duration * 1000)


def fit_duration(
    wav_path: Path,
    target_ms: int,
    *,
    output_path: Path | None = None,
) -> Path:
    """Trim or pad WAV to exact target duration via ffmpeg."""
    ffmpeg = check_ffmpeg()
    wav_path = Path(wav_path)
    target_s = target_ms / 1000.0
    out = output_path or wav_path
    in_place = output_path is None
    tmp = wav_path.with_suffix(".fit.tmp.wav") if in_place else out

    current_ms = wav_duration_ms(wav_path)
    if abs(current_ms - target_ms) <= 50:
        if not in_place and out != wav_path:
            shutil.copy2(wav_path, out)
        return out

    if current_ms > target_ms:
        cmd = [ffmpeg, "-y", "-i", str(wav_path), "-t", f"{target_s:.3f}", str(tmp)]
    else:
        pad_s = max(0.0, target_s - current_ms / 1000.0)
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(wav_path),
            "-af",
            f"apad=pad_dur={pad_s:.3f}",
            "-t",
            f"{target_s:.3f}",
            str(tmp),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to fit duration for {wav_path}:\n{result.stderr}")

    if in_place:
        tmp.replace(wav_path)
        return wav_path

    if tmp != out:
        shutil.move(str(tmp), str(out))
    return out
