import pytest
from pathlib import Path

from caption_helper.extract import FFmpegNotFoundError, check_ffmpeg
from caption_helper.models import Sentence
from caption_helper.split import segment_filename, split_segments
from caption_helper.srt import format_cue_text, ms_to_srt_timestamp, write_srt
from caption_helper.transcribe import sentences_from_sentence_info


class TestMsToSrtTimestamp:
    def test_zero(self) -> None:
        assert ms_to_srt_timestamp(0) == "00:00:00,000"

    def test_milliseconds(self) -> None:
        assert ms_to_srt_timestamp(880) == "00:00:00,880"

    def test_hour_rollover(self) -> None:
        assert ms_to_srt_timestamp(3_601_250) == "01:00:01,250"

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            ms_to_srt_timestamp(-1)


class TestWriteSrt:
    def test_srt_format(self, tmp_path) -> None:
        sentences = [
            Sentence(text="欢迎大家", spk=0, start=880, end=5195),
            Sentence(text="体验语音识别", spk=1, start=5200, end=8100),
        ]
        out = tmp_path / "subtitles.srt"
        write_srt(sentences, out)
        content = out.read_text(encoding="utf-8")
        assert "1\n00:00:00,880 --> 00:00:05,195\n[说话人 0] 欢迎大家" in content
        assert "[说话人 1] 体验语音识别" in content


class TestSegmentFilename:
    def test_filename_pattern(self) -> None:
        sentence = Sentence(text="test", spk=1, start=5200, end=8100)
        assert segment_filename(3, sentence) == "0003_spk1_5200-8100.wav"


class TestSentencesFromSentenceInfo:
    def test_maps_fields(self) -> None:
        info = [
            {"text": "你好", "spk": 0, "start": 100, "end": 500},
            {"sentence": "世界", "spk": 1, "start": 600, "end": 900},
        ]
        sentences = sentences_from_sentence_info(info)
        assert len(sentences) == 2
        assert sentences[0].text == "你好"
        assert sentences[1].text == "世界"


class TestCheckFfmpeg:
    def test_check_ffmpeg_found(self, monkeypatch) -> None:
        monkeypatch.setattr("caption_helper.extract.shutil.which", lambda _: "/usr/bin/ffmpeg")
        assert check_ffmpeg() == "/usr/bin/ffmpeg"

    def test_check_ffmpeg_missing(self, monkeypatch) -> None:
        monkeypatch.setattr("caption_helper.extract.shutil.which", lambda _: None)
        with pytest.raises(FFmpegNotFoundError):
            check_ffmpeg()


class TestTranscriber:
    def test_transcribe_from_mock(self, monkeypatch, tmp_path) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        class FakeModel:
            def generate(self, **kwargs):
                return [
                    {
                        "sentence_info": [
                            {"text": "测试", "spk": 0, "start": 0, "end": 1000},
                        ]
                    }
                ]

        from caption_helper.transcribe import Transcriber

        t = Transcriber()
        monkeypatch.setattr(t, "_load_model", lambda: FakeModel())
        sentences = t.transcribe(str(wav))
        assert len(sentences) == 1
        assert sentences[0].text == "测试"


class TestSplitSegments:
    def test_segment_count(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr("caption_helper.split.check_ffmpeg", lambda: "ffmpeg")

        def fake_run(cmd, capture_output=True, text=True):
            with open(cmd[-1], "wb") as f:
                f.write(b"wav")
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("caption_helper.split.subprocess.run", fake_run)

        full_wav = tmp_path / "audio.wav"
        full_wav.write_bytes(b"full")
        sentences = [
            Sentence(text="a", spk=0, start=0, end=1000),
            Sentence(text="b", spk=1, start=1000, end=2000),
        ]
        outputs = split_segments(full_wav, sentences, tmp_path / "segments")
        assert len(outputs) == 2
        assert outputs[0].name == "0001_spk0_0-1000.wav"
        assert outputs[1].name == "0002_spk1_1000-2000.wav"
