from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from caption_helper.extract import FFmpegNotFoundError, check_ffmpeg
from caption_helper.models import Sentence
from caption_helper.remux.assemble import (
    MissingTTSClipsError,
    assemble_timeline,
    resolve_clip,
    validate_clips,
)
from caption_helper.remux.manifest import load_remux_manifest
from caption_helper.remux.mux import remux_video
from caption_helper.remux.pipeline import remux_pipeline
from caption_helper.split import segment_filename
from caption_helper.subtitles_json import Cue, initialize_subtitle_files, load_subtitles, save_subtitles
from tests.helpers import write_test_wav


def _tone(path: Path, *, freq: float, duration_s: float, amplitude: float = 0.5) -> None:
    sr = 16000
    n = int(duration_s * sr)
    t = np.arange(n, dtype=np.float32)
    audio = amplitude * np.sin(2 * np.pi * freq * t / sr)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr)


class TestResolveClip:
    def test_modified_uses_tts_when_present(self, tmp_path) -> None:
        cue = Cue(1, 0, 0, 1000, "a", "changed", modified=True)
        seg = tmp_path / "segments" / segment_filename(1, cue.to_sentence())
        tts = tmp_path / "tts_segments" / segment_filename(1, cue.to_sentence())
        seg.parent.mkdir(parents=True, exist_ok=True)
        tts.parent.mkdir(parents=True, exist_ok=True)
        seg.write_bytes(b"x")
        tts.write_bytes(b"y")
        path, source = resolve_clip(cue, tmp_path)
        assert path == tts
        assert source == "tts"

    def test_unmodified_uses_segment(self, tmp_path) -> None:
        cue = Cue(1, 0, 0, 1000, "a", "a", modified=False)
        seg = tmp_path / "segments" / segment_filename(1, cue.to_sentence())
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_bytes(b"x")
        path, source = resolve_clip(cue, tmp_path)
        assert path == seg
        assert source == "original"


class TestValidateClips:
    def test_raises_for_missing_tts(self, tmp_path) -> None:
        cues = [
            Cue(1, 0, 0, 1000, "a", "changed", modified=True),
            Cue(2, 1, 1000, 2000, "b", "b", modified=False),
        ]
        seg = tmp_path / "segments" / segment_filename(1, cues[0].to_sentence())
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_bytes(b"x")
        with pytest.raises(MissingTTSClipsError) as exc:
            validate_clips(cues, tmp_path)
        assert exc.value.missing == [1]

    def test_passes_when_no_modified_cues(self, tmp_path) -> None:
        cues = [Cue(1, 0, 0, 1000, "a", "a", modified=False)]
        validate_clips(cues, tmp_path)


class TestAssembleTimeline:
    def test_replaces_modified_and_original_regions(self, tmp_path) -> None:
        sentences = [
            Sentence("a", 0, 0, 1000),
            Sentence("b", 1, 1000, 2000),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        _tone(tmp_path / "audio.wav", freq=440, duration_s=2.0, amplitude=0.2)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "changed"
        save_subtitles(tmp_path / "subtitles.json", cues)

        seg0 = tmp_path / "segments" / segment_filename(1, cues[0].to_sentence())
        seg1 = tmp_path / "segments" / segment_filename(2, cues[1].to_sentence())
        tts0 = tmp_path / "tts_segments" / segment_filename(1, cues[0].to_sentence())
        _tone(seg0, freq=880, duration_s=1.0, amplitude=0.9)
        _tone(seg1, freq=660, duration_s=1.0, amplitude=0.9)
        _tone(tts0, freq=220, duration_s=1.0, amplitude=0.9)

        manifest = assemble_timeline(tmp_path)
        assert (tmp_path / "output_audio.wav").is_file()
        assert manifest.cues[0].source == "tts"
        assert manifest.cues[1].source == "original"

        out, sr = sf.read(str(tmp_path / "output_audio.wav"), dtype="float32")
        assert sr == 16000
        first = out[: int(0.5 * sr)]
        second = out[int(1.25 * sr) : int(1.75 * sr)]
        assert np.max(np.abs(first)) > 0.5
        assert np.max(np.abs(second)) > 0.5

        saved = load_remux_manifest(tmp_path)
        assert saved is not None
        assert saved["output_audio"] == "output_audio.wav"


def _ffmpeg_available() -> bool:
    try:
        check_ffmpeg()
        return True
    except FFmpegNotFoundError:
        return False


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg required")
class TestRemuxIntegration:
    def test_remux_pipeline_with_short_video(self, tmp_path) -> None:
        video = tmp_path / "source.mp4"
        cmd = [
            check_ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=2",
            "-f",
            "lavfi",
            "-i",
            "sine=f=440:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

        sentences = [
            Sentence("hello", 0, 0, 1000),
            Sentence("world", 1, 1000, 2000),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        write_test_wav(tmp_path / "audio.wav", duration_s=2.0)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "hi"
        save_subtitles(tmp_path / "subtitles.json", cues)
        (tmp_path / "subtitles_edited.srt").write_text(
            (tmp_path / "subtitles_original.srt").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        seg0 = tmp_path / "segments" / segment_filename(1, cues[0].to_sentence())
        seg1 = tmp_path / "segments" / segment_filename(2, cues[1].to_sentence())
        tts0 = tmp_path / "tts_segments" / segment_filename(1, cues[0].to_sentence())
        write_test_wav(seg0, duration_s=1.0)
        write_test_wav(seg1, duration_s=1.0)
        write_test_wav(tts0, duration_s=1.0, amplitude=0.6)

        manifest = remux_pipeline(tmp_path)
        assert (tmp_path / manifest.output_video).is_file()
        assert (tmp_path / manifest.output_audio).is_file()

    def test_remux_video_creates_output(self, tmp_path) -> None:
        video = tmp_path / "input.mp4"
        audio = tmp_path / "output_audio.wav"
        srt = tmp_path / "subs.srt"
        out = tmp_path / "output_video.mp4"

        cmd = [
            check_ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x120:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=f=880:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        write_test_wav(audio, duration_s=1.0)
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\n[说话人 0] test\n",
            encoding="utf-8",
        )

        remux_video(video, audio, srt, out)
        assert out.is_file()
        assert out.stat().st_size > 0
