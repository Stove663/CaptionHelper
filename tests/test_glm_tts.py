from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
import soundfile as sf
import torch

from caption_helper.tts.glm_tts import GLMTTSEngine, GLMTTSConfig
from caption_helper.tts.synthesizer import synthesize_modified_segments


class TestGLMTTSEngine:
    def test_synthesize_call_shape(self, tmp_path: Path, monkeypatch) -> None:
        ref = tmp_path / "ref.wav"
        out = tmp_path / "out.wav"
        sf.write(str(ref), np.zeros(8000, dtype=np.float32), 16000)

        monkeypatch.setattr("caption_helper.tts.glm_tts.glm_tts_installed", lambda config=None: True)

        mock_runtime = MagicMock()
        mock_runtime.synthesize_utterance.return_value = (torch.zeros(1, 24000), 24000)
        monkeypatch.setattr(
            "caption_helper.tts.glm_tts._GLMRuntime.get",
            lambda config, use_phoneme=False: mock_runtime,
        )

        saved: list[Path] = []

        def fake_resample(self, audio, sample_rate, output_path):
            saved.append(Path(output_path))
            sf.write(str(output_path), np.zeros(16000, dtype=np.float32), 16000)
            return Path(output_path)

        monkeypatch.setattr(GLMTTSEngine, "_resample_and_save", fake_resample)

        engine = GLMTTSEngine()
        engine.synthesize(
            "你好世界",
            ref,
            50,
            output_path=out,
            reference_text="参考文本",
        )

        mock_runtime.synthesize_utterance.assert_called_once()
        call = mock_runtime.synthesize_utterance.call_args
        assert call.args[0] == "你好世界"
        assert call.args[1] == ref
        assert call.kwargs["reference_text"] == "参考文本"
        assert call.kwargs["use_phoneme"] is False
        assert call.kwargs["apply_text_prep"] is False
        assert saved == [out]

    def test_synthesize_code_mixed_enables_phoneme_auto(self, tmp_path: Path, monkeypatch) -> None:
        ref = tmp_path / "ref.wav"
        out = tmp_path / "out.wav"
        sf.write(str(ref), np.zeros(8000, dtype=np.float32), 16000)

        monkeypatch.setattr("caption_helper.tts.glm_tts.glm_tts_installed", lambda config=None: True)

        captured: dict[str, bool] = {}

        def fake_get(config, use_phoneme=False):
            captured["use_phoneme"] = use_phoneme
            mock_runtime = MagicMock()
            mock_runtime.synthesize_utterance.return_value = (torch.zeros(1, 24000), 24000)
            return mock_runtime

        monkeypatch.setattr("caption_helper.tts.glm_tts._GLMRuntime.get", fake_get)
        monkeypatch.setattr(
            GLMTTSEngine,
            "_resample_and_save",
            lambda self, audio, sample_rate, output_path: output_path,
        )

        engine = GLMTTSEngine(GLMTTSConfig(glm_phoneme_mode="auto"))
        engine.synthesize(
            "打开 terminal 窗口",
            ref,
            None,
            output_path=out,
        )

        assert captured["use_phoneme"] is True
        detail = engine.last_synthesis_detail
        assert detail is not None
        assert detail.phoneme_enabled is True
        assert detail.text_prep_applied is True

    def test_synthesize_raises_when_not_installed(self, tmp_path: Path, monkeypatch) -> None:
        ref = tmp_path / "ref.wav"
        out = tmp_path / "out.wav"
        sf.write(str(ref), np.zeros(100, dtype=np.float32), 16000)
        monkeypatch.setattr("caption_helper.tts.glm_tts.glm_tts_installed", lambda config=None: False)

        engine = GLMTTSEngine()
        with pytest.raises(RuntimeError, match="GLM-TTS is not installed"):
            engine.synthesize("test", ref, None, output_path=out)


class TestGLMSynthesisManifest:
    def test_manifest_includes_glm_code_mix_fields(self, tmp_path: Path, monkeypatch) -> None:
        project = tmp_path / "proj"
        segments = project / "segments"
        segments.mkdir(parents=True)
        ref = segments / "0001_spk0_0-1000.wav"
        sf.write(str(ref), np.zeros(16000, dtype=np.float32), 16000)

        (project / "modified_segments.json").write_text(
            json.dumps(
                [
                    {
                        "index": 1,
                        "spk": 0,
                        "start_ms": 0,
                        "end_ms": 1000,
                        "text_original": "打开终端",
                        "text_edited": "打开 terminal",
                        "segment_path": "segments/0001_spk0_0-1000.wav",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (project / "subtitles.json").write_text(
            json.dumps(
                {
                    "cues": [
                        {
                            "index": 1,
                            "spk": 0,
                            "start_ms": 0,
                            "end_ms": 1000,
                            "text_original": "打开终端",
                            "text_edited": "打开 terminal",
                            "modified": True,
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        mock_engine = MagicMock()
        mock_engine.config = GLMTTSConfig()
        mock_engine.peak_vram_mb = 0
        mock_engine.last_synthesis_detail = type(
            "D",
            (),
            {
                "phoneme_enabled": True,
                "text_prep_applied": True,
                "glm_phoneme_mode": "auto",
            },
        )()

        def fake_synthesize(text, reference_wav, tokens, *, output_path, reference_text=None):
            import soundfile as sf

            sf.write(str(output_path), np.zeros(16000, dtype=np.float32), 16000)
            return Path(output_path)

        mock_engine.synthesize.side_effect = fake_synthesize
        mock_engine.reset_vram_stats = MagicMock()
        mock_engine.clear_cuda_cache = MagicMock()

        monkeypatch.setattr(
            "caption_helper.tts.synthesizer.resolve_reference",
            lambda cue, project_dir, config=None: type(
                "R",
                (),
                {
                    "path": ref,
                    "rel_path": "segments/0001_spk0_0-1000.wav",
                    "source": "cue",
                    "fallback_reason": None,
                    "duration_ms": 1000,
                    "quality_score": 1.0,
                },
            )(),
        )

        synthesize_modified_segments(
            project,
            engine=mock_engine,
            tts_provider="glm-tts",
            glm_phoneme_mode="auto",
        )

        manifest = json.loads((project / "synthesis_manifest.json").read_text(encoding="utf-8"))
        cue = manifest["cues"][0]
        assert cue["phoneme_enabled"] is True
        assert cue["text_prep_applied"] is True
        assert cue["glm_phoneme_mode"] == "auto"
        assert cue["code_mixed"] is True
