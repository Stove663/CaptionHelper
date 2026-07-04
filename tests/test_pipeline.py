from pathlib import Path
from unittest.mock import patch

import pytest

from caption_helper.models import Sentence
from caption_helper.pipeline import process
from caption_helper.srt import write_srt


class TestPipelineIntegration:
  def test_full_pipeline_with_mocks(self, tmp_path, monkeypatch) -> None:
    video = tmp_path / "meeting.mp4"
    video.write_bytes(b"fake-video")

    sentences = [
      Sentence(text="欢迎大家", spk=0, start=880, end=5195),
      Sentence(text="体验语音识别", spk=1, start=5200, end=8100),
    ]

    monkeypatch.setattr(
      "caption_helper.pipeline.extract_audio",
      lambda v, o: o.write_bytes(b"RIFF"),
    )

    class FakeTranscriber:
      def __init__(self, config=None):
        pass

      def transcribe(self, audio_path):
        return sentences

    monkeypatch.setattr("caption_helper.pipeline.Transcriber", FakeTranscriber)

    def fake_split(full_wav, sents, segments_dir):
      paths = []
      for i, s in enumerate(sents, start=1):
        p = Path(segments_dir) / f"{i:04d}_spk{s.spk}_{s.start}-{s.end}.wav"
        p.write_bytes(b"seg")
        paths.append(p)
      return paths

    monkeypatch.setattr("caption_helper.pipeline.split_segments", fake_split)
    monkeypatch.setattr(
      "caption_helper.pipeline.build_speaker_reference_bank",
      lambda project_dir, **kwargs: {"speakers": {}},
    )

    out = process(video)
    assert (out / "audio.wav").is_file()
    assert (out / "subtitles.srt").is_file()
    srt = (out / "subtitles.srt").read_text(encoding="utf-8")
    assert "[说话人 0] 欢迎大家" in srt
    assert "00:00:00,880 --> 00:00:05,195" in srt
    assert "[说话人 1] 体验语音识别" in srt
    segments = list((out / "segments").glob("*.wav"))
    assert len(segments) == len(sentences)

  def test_missing_video_raises(self, tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
      process(tmp_path / "nope.mp4")
