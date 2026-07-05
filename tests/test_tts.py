from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from caption_helper.models import Sentence
from caption_helper.subtitles_json import Cue, initialize_subtitle_files, save_subtitles, load_subtitles
from caption_helper.tts.duration import fit_duration, ms_to_tokens, wav_duration_ms
from caption_helper.tts.moss_tts import MossTTSEngine
from caption_helper.tts.synthesizer import synthesize_modified_segments
from tests.helpers import write_test_wav


class TestDuration:
    def test_ms_to_tokens(self) -> None:
        assert ms_to_tokens(2900, tokens_per_second=25) == 72
        assert ms_to_tokens(40, tokens_per_second=25) == 1

    def test_wav_duration_ms(self, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        sf.write(str(wav), np.zeros(16000, dtype=np.float32), 16000)
        assert wav_duration_ms(wav) == 1000

    def test_fit_duration_trim(self, tmp_path: Path) -> None:
        wav = tmp_path / "long.wav"
        sf.write(str(wav), np.zeros(32000, dtype=np.float32), 16000)
        out = tmp_path / "trimmed.wav"
        fit_duration(wav, 1000, output_path=out)
        assert abs(wav_duration_ms(out) - 1000) <= 50


class TestMossTTS:
    def test_synthesize_call_shape(self, tmp_path: Path) -> None:
        import torch

        ref = tmp_path / "ref.wav"
        out = tmp_path / "out.wav"
        sf.write(str(ref), np.zeros(8000, dtype=np.float32), 16000)

        mock_processor = MagicMock()
        mock_processor.model_config.sampling_rate = 24000
        mock_processor.build_user_message.return_value = {"role": "user"}
        mock_processor.return_value = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock(),
        }
        mock_processor.decode.return_value = [
            MagicMock(audio_codes_list=[torch.zeros(24000)])
        ]

        mock_model = MagicMock()
        mock_model.generate.return_value = "outputs"

        engine = MossTTSEngine()
        engine._processor = mock_processor
        engine._model = mock_model
        engine._device = "cpu"

        with patch.dict(sys.modules, {"torchaudio": MagicMock()}) as mocked:
            engine.synthesize("你好", ref, 50, output_path=out)
            mocked["torchaudio"].save.assert_called_once()

        mock_processor.build_user_message.assert_called_once()
        kwargs = mock_processor.build_user_message.call_args.kwargs
        assert kwargs["text"] == "你好"
        assert kwargs["reference"] == [str(ref)]
        assert kwargs["tokens"] == 50
        assert kwargs["language"] == "Chinese"
        mock_processor.assert_called_once()
        mock_model.generate.assert_called_once()

    def test_normalize_audio_stereo_48k_to_mono_16k(self) -> None:
        import torch
        from caption_helper.tts.moss_tts import _normalize_audio

        stereo = torch.zeros(2, 48000)
        mock_ta = MagicMock()

        class _Resample:
            def __init__(self, src: int, dst: int) -> None:
                self._ratio = dst / src

            def __call__(self, audio: torch.Tensor) -> torch.Tensor:
                out_len = max(1, int(audio.shape[-1] * self._ratio))
                return audio[:, :out_len]

        mock_ta.transforms.Resample = _Resample

        with patch.dict(sys.modules, {"torchaudio": mock_ta}):
            audio, sample_rate = _normalize_audio(stereo, 48000)

        assert sample_rate == 16000
        assert audio.shape[0] == 1
        assert audio.shape[1] == 16000


    def test_build_message_kwargs_code_mixed(self) -> None:
        from caption_helper.tts.code_mix import detect_language_mode

        text = "打开 terminal 窗口"
        assert detect_language_mode(text) == "auto"
        mode = detect_language_mode(text)
        user_kwargs: dict = {"text": text, "reference": ["/ref.wav"], "tokens": 50}
        if mode != "auto":
            user_kwargs["language"] = mode
        assert "language" not in user_kwargs


class TestSynthesizer:
    def test_synthesize_modified_only(self, tmp_path: Path) -> None:
        sentences = [
            Sentence("a", 0, 0, 1000),
            Sentence("b", 1, 1000, 2000),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        (tmp_path / "segments").mkdir(exist_ok=True)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 2.0)
        write_test_wav(tmp_path / "segments" / segment_filename(2, sentences[1]), 2.0)
        from caption_helper.tts.reference import build_speaker_reference_bank

        build_speaker_reference_bank(tmp_path)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[1].text_edited = "changed"
        save_subtitles(tmp_path / "subtitles.json", cues)
        from caption_helper.subtitles_json import generate_modified_segments

        generate_modified_segments(tmp_path, cues)

        class FakeEngine:
            config = MossTTSEngine().config
            peak_vram_mb = 0

            def synthesize(
                self,
                text,
                reference_wav,
                tokens,
                *,
                output_path: Path,
                language=None,
                reference_text=None,
            ):
                duration_samples = 48000 if tokens is None else 32000
                sf.write(str(output_path), np.zeros(duration_samples, dtype=np.float32), 16000)
                return output_path

            def clear_cuda_cache(self) -> None:
                pass

            def reset_vram_stats(self) -> None:
                pass

        gpu = __import__(
            "caption_helper.tts.preflight", fromlist=["GPUInfo"]
        ).GPUInfo(available=False)
        with patch("caption_helper.tts.synthesizer.get_gpu_info", return_value=gpu):
            result = synthesize_modified_segments(tmp_path, engine=FakeEngine())
        assert result.total == 1
        assert result.completed == 1
        assert (tmp_path / "tts_segments" / "0002_spk1_1000-2000.wav").is_file()

        manifest = json.loads((tmp_path / "synthesis_manifest.json").read_text(encoding="utf-8"))
        assert manifest["completed"] == 1
        assert manifest["cues"][0]["tokens"] == 12
        assert manifest["cues"][0]["tokens_per_second"] == 12.5
        assert manifest["cues"][0]["reference_segment"] == "segments/0002_spk1_1000-2000.wav"

    def test_natural_pace_skips_trim(self, tmp_path: Path) -> None:
        sentences = [Sentence("a", 0, 0, 1000)]
        initialize_subtitle_files(tmp_path, sentences)
        from caption_helper.split import segment_filename

        write_test_wav(tmp_path / "segments" / segment_filename(1, sentences[0]), 2.0)
        from caption_helper.tts.reference import build_speaker_reference_bank

        build_speaker_reference_bank(tmp_path)

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "changed longer text"
        save_subtitles(tmp_path / "subtitles.json", cues)
        from caption_helper.subtitles_json import generate_modified_segments

        generate_modified_segments(tmp_path, cues)

        class FakeEngine:
            config = MossTTSEngine().config
            peak_vram_mb = 0

            def synthesize(
                self,
                text,
                reference_wav,
                tokens,
                *,
                output_path: Path,
                language=None,
                reference_text=None,
            ):
                assert tokens is None
                sf.write(str(output_path), np.zeros(48000, dtype=np.float32), 16000)
                return output_path

            def clear_cuda_cache(self) -> None:
                pass

            def reset_vram_stats(self) -> None:
                pass

        gpu = __import__(
            "caption_helper.tts.preflight", fromlist=["GPUInfo"]
        ).GPUInfo(available=False)
        with patch("caption_helper.tts.synthesizer.get_gpu_info", return_value=gpu):
            result = synthesize_modified_segments(
                tmp_path,
                engine=FakeEngine(),
                sync_mode="natural-pace",
            )
        assert result.sync_mode == "natural-pace"
        manifest = json.loads((tmp_path / "synthesis_manifest.json").read_text(encoding="utf-8"))
        assert manifest["cues"][0]["tokens"] is None
        assert manifest["cues"][0]["actual_duration_ms"] == 3000
        assert manifest["cues"][0]["delta_ms"] == 2000

    def test_missing_reference_continues(self, tmp_path: Path) -> None:
        modified = [
            {
                "index": 1,
                "spk": 0,
                "text_original": "a",
                "text_edited": "b",
                "start_ms": 0,
                "end_ms": 1000,
                "segment_path": "segments/missing.wav",
            }
        ]
        (tmp_path / "modified_segments.json").write_text(json.dumps(modified), encoding="utf-8")

        class FakeEngine:
            config = MossTTSEngine().config
            peak_vram_mb = 0

            def synthesize(self, *args, **kwargs):
                raise AssertionError("should not be called")

            def clear_cuda_cache(self) -> None:
                pass

            def reset_vram_stats(self) -> None:
                pass

        gpu = __import__(
            "caption_helper.tts.preflight", fromlist=["GPUInfo"]
        ).GPUInfo(available=False)
        with patch("caption_helper.tts.synthesizer.get_gpu_info", return_value=gpu):
            result = synthesize_modified_segments(tmp_path, engine=FakeEngine())
        assert result.failed == 1
        assert result.cues[0].status == "failed"
