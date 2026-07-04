from __future__ import annotations

import subprocess
from pathlib import Path

from caption_helper.extract import check_ffmpeg


def get_media_duration_s(path: Path) -> float:
    ffmpeg = check_ffmpeg()
    cmd = [
        ffmpeg,
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr
    for line in stderr.splitlines():
        if "Duration:" in line:
            part = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            h, m, s = part.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    raise RuntimeError(f"Could not determine duration for {path}")


def _pad_audio_to_duration(audio_path: Path, target_s: float, output_path: Path) -> Path:
    ffmpeg = check_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(audio_path),
        "-af",
        f"apad=pad_dur={max(0.0, target_s):.3f}",
        "-t",
        f"{target_s:.3f}",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to pad audio:\n{result.stderr}")
    return output_path


def remux_video(
    source_video: Path,
    output_audio: Path,
    subtitles_srt: Path,
    output_path: Path,
    *,
    video_copy: bool = True,
) -> Path:
    """Remux final output video with AAC audio and mov_text subtitles."""
    ffmpeg = check_ffmpeg()
    source_video = Path(source_video)
    output_audio = Path(output_audio)
    subtitles_srt = Path(subtitles_srt)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    video_duration = get_media_duration_s(source_video)
    audio_duration = get_media_duration_s(output_audio)
    padded_audio = output_audio
    tmp_audio: Path | None = None

    if abs(audio_duration - video_duration) > 0.1:
        if audio_duration + 0.05 < video_duration:
            tmp_audio = output_path.parent / ".padded_output_audio.wav"
            padded_audio = _pad_audio_to_duration(output_audio, video_duration, tmp_audio)
        elif audio_duration > video_duration + 0.05 and not video_copy:
            video_duration = audio_duration

    video_codec = ["-c:v", "copy"] if video_copy else ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    shortest = ["-shortest"] if video_copy else []

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source_video),
        "-i",
        str(padded_audio),
        "-i",
        str(subtitles_srt),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-map",
        "2:0",
        *video_codec,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-c:s",
        "mov_text",
        *shortest,
        str(output_path),
    ]
    if not video_copy and audio_duration > video_duration + 0.05:
        cmd.extend(["-t", f"{audio_duration:.3f}"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if tmp_audio and tmp_audio.is_file():
        tmp_audio.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg remux failed:\n{result.stderr}")
    return output_path
