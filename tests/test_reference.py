from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from caption_helper.models import Sentence
from caption_helper.subtitles_json import (
    Cue,
    initialize_subtitle_files,
    load_subtitles,
    save_subtitles,
)
from caption_helper.tts.reference import (
    ReferenceConfig,
    ReferenceUnavailable,
    build_reference_quality_report,
    build_speaker_reference_bank,
    resolve_reference,
    save_reference_override,
    validate_reference,
)


from tests.helpers import write_test_wav


class TestValidateReference:
    def test_good_clip(self, tmp_path: Path) -> None:
        wav = tmp_path / "good.wav"
        write_test_wav(wav, 2.0)
        result = validate_reference(wav)
        assert result.adequate is True
        assert result.duration_ms >= 1500
        assert result.quality_score >= 0.5

    def test_short_clip(self, tmp_path: Path) -> None:
        wav = tmp_path / "short.wav"
        write_test_wav(wav, 0.4)
        result = validate_reference(wav)
        assert result.adequate is False
        assert "too_short" in result.issues[0]

    def test_quiet_clip(self, tmp_path: Path) -> None:
        wav = tmp_path / "quiet.wav"
        write_test_wav(wav, 2.0, amplitude=0.001)
        result = validate_reference(wav)
        assert result.adequate is False
        assert "quiet" in result.issues

    def test_clipped(self, tmp_path: Path) -> None:
        wav = tmp_path / "clip.wav"
        write_test_wav(wav, 2.0, amplitude=1.0)
        result = validate_reference(wav)
        assert "clipping" in result.issues


class TestSpeakerBank:
    def _setup_project(self, tmp_path: Path) -> None:
        sentences = [
            Sentence("a", 0, 0, 400),
            Sentence("b", 0, 500, 2500),
            Sentence("c", 1, 3000, 6000),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        for i, s in enumerate(sentences, start=1):
            from caption_helper.split import segment_filename

            write_test_wav(tmp_path / "segments" / segment_filename(i, s), 2.0)

    def test_multi_speaker_bank(self, tmp_path: Path) -> None:
        self._setup_project(tmp_path)
        result = build_speaker_reference_bank(tmp_path)
        assert "0" in result["speakers"]
        assert "1" in result["speakers"]
        assert (tmp_path / "speaker_refs" / "spk0.wav").is_file()
        assert (tmp_path / "reference_quality.json").is_file()

    def test_all_short_segments(self, tmp_path: Path) -> None:
        sentences = [Sentence("x", 0, 0, 300)]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 0.3)
        result = build_speaker_reference_bank(tmp_path)
        assert result["speakers"]["0"]["adequate"] is False


class TestResolveReference:
    def test_short_cue_uses_speaker_bank(self, tmp_path: Path) -> None:
        sentences = [
            Sentence("short", 0, 0, 400),
            Sentence("long enough text here", 0, 1000, 3500),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 0.4)
        write_test_wav(tmp_path / "segments" / segment_filename(2, sentences[1]), 2.0)
        build_speaker_reference_bank(tmp_path)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "changed"
        save_subtitles(tmp_path / "subtitles.json", cues)

        resolved = resolve_reference(cues[0], tmp_path)
        assert resolved.source == "speaker_bank"
        assert resolved.fallback_reason is not None

    def test_manual_override(self, tmp_path: Path) -> None:
        sentences = [
            Sentence("a", 0, 0, 400),
            Sentence("b", 0, 1000, 3500),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 0.4)
        seg2 = tmp_path / "segments" / segment_filename(2, sentences[1])
        write_test_wav(seg2, 2.0)
        build_speaker_reference_bank(tmp_path)

        cues = load_subtitles(tmp_path / "subtitles.json")
        save_reference_override(tmp_path, 1, str(seg2.relative_to(tmp_path)))

        resolved = resolve_reference(cues[0], tmp_path)
        assert resolved.source == "manual_override"

    def test_no_adequate_reference_raises(self, tmp_path: Path) -> None:
        sentences = [Sentence("tiny", 0, 0, 300)]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 0.3)
        build_speaker_reference_bank(tmp_path)
        cues = load_subtitles(tmp_path / "subtitles.json")

        with pytest.raises(ReferenceUnavailable):
            resolve_reference(cues[0], tmp_path)


class TestReferenceQualityReport:
    def test_modified_cue_report(self, tmp_path: Path) -> None:
        sentences = [
            Sentence("a", 0, 0, 400),
            Sentence("b", 0, 1000, 3500),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 0.4)
        write_test_wav(tmp_path / "segments" / segment_filename(2, sentences[1]), 2.0)
        build_speaker_reference_bank(tmp_path)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "changed"
        save_subtitles(tmp_path / "subtitles.json", cues)

        report = build_reference_quality_report(tmp_path)
        assert len(report["cues"]) == 1
        assert report["cues"][0]["status"] == "fallback"
