from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
import soundfile as sf
import torch

from caption_helper.tts.glm_tts import GLMTTSEngine


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
            lambda config: mock_runtime,
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
        assert saved == [out]

    def test_synthesize_raises_when_not_installed(self, tmp_path: Path, monkeypatch) -> None:
        ref = tmp_path / "ref.wav"
        out = tmp_path / "out.wav"
        sf.write(str(ref), np.zeros(100, dtype=np.float32), 16000)
        monkeypatch.setattr("caption_helper.tts.glm_tts.glm_tts_installed", lambda config=None: False)

        engine = GLMTTSEngine()
        with pytest.raises(RuntimeError, match="GLM-TTS is not installed"):
            engine.synthesize("test", ref, None, output_path=out)
