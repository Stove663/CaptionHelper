from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caption_helper.tts.moss_tts import MossTTSConfig

logger = logging.getLogger(__name__)

MODEL_GLM_TTS = "zai-org/GLM-TTS"
PIPELINE_SAMPLE_RATE = 16_000
GLM_DEFAULT_SAMPLE_RATE = 24_000
MIN_VRAM_GB_GLM = 8.0


@dataclass
class GLMTTSConfig(MossTTSConfig):
    """Config for GLM-TTS integration."""

    provider: str = "glm-tts"
    model: str = MODEL_GLM_TTS
    glm_home: str | None = None
    sample_rate: int = GLM_DEFAULT_SAMPLE_RATE


def glm_tts_home(config: GLMTTSConfig | None = None) -> Path | None:
    """Resolve GLM-TTS install root (clone with populated ``ckpt/``)."""
    candidates: list[str] = []
    if config and config.glm_home:
        candidates.append(config.glm_home)
    env_home = os.environ.get("GLM_TTS_HOME", "").strip()
    if env_home:
        candidates.append(env_home)
    for raw in candidates:
        home = Path(raw).expanduser().resolve()
        if (home / "ckpt").is_dir():
            return home
    return None


def glm_tts_installed(config: GLMTTSConfig | None = None) -> bool:
    home = glm_tts_home(config)
    if home is None:
        return False
    ckpt = home / "ckpt"
    return (ckpt / "llm").is_dir() and (ckpt / "flow" / "flow.pt").is_file()


@contextmanager
def _glm_workdir(home: Path):
    prev = Path.cwd()
    os.chdir(home)
    try:
        if str(home) not in sys.path:
            sys.path.insert(0, str(home))
        yield
    finally:
        os.chdir(prev)


class _GLMRuntime:
    """Lazy-loaded GLM-TTS models (one instance per engine config home)."""

    _cache: dict[str, _GLMRuntime] = {}

    def __init__(self, home: Path, config: GLMTTSConfig) -> None:
        self.home = home
        self.config = config
        self._loaded = False
        self.frontend: Any = None
        self.text_frontend: Any = None
        self.llm: Any = None
        self.flow: Any = None
        self.device: Any = None

    @classmethod
    def get(cls, config: GLMTTSConfig) -> _GLMRuntime:
        home = glm_tts_home(config)
        if home is None:
            raise RuntimeError(
                "GLM-TTS is not installed. Clone https://github.com/zai-org/GLM-TTS, "
                "download checkpoints to ckpt/, and set GLM_TTS_HOME to the repo root."
            )
        key = str(home)
        if key not in cls._cache:
            cls._cache[key] = cls(home, config)
        return cls._cache[key]

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        with _glm_workdir(self.home):
            import torch

            from glmtts_inference import load_models

            self.device = torch.device(
                self.config.device or ("cuda" if torch.cuda.is_available() else "cpu")
            )
            logger.info("Loading GLM-TTS from %s on %s", self.home, self.device)
            self.frontend, self.text_frontend, _, self.llm, self.flow = load_models(
                use_phoneme=False,
                sample_rate=self.config.sample_rate,
            )
            self._loaded = True

    def synthesize_utterance(
        self,
        text: str,
        reference_wav: Path,
        *,
        reference_text: str | None = None,
    ) -> tuple[Any, int]:
        """Return (audio_tensor [1, samples], sample_rate)."""
        self.ensure_loaded()
        with _glm_workdir(self.home):
            import torch
            from glmtts_inference import generate_long

            prompt_text = reference_text or text
            prompt_text = self.text_frontend.text_normalize(prompt_text)
            synth_text = self.text_frontend.text_normalize(text)

            prompt_text_token = self.frontend._extract_text_token(prompt_text + " ")
            prompt_speech_token = self.frontend._extract_speech_token([str(reference_wav)])
            speech_feat = self.frontend._extract_speech_feat(
                str(reference_wav), sample_rate=self.config.sample_rate
            )
            embedding = self.frontend._extract_spk_embedding(str(reference_wav))
            cache_speech_token = [prompt_speech_token.squeeze().tolist()]
            flow_prompt_token = torch.tensor(cache_speech_token, dtype=torch.int32).to(self.device)

            cache = {
                "cache_text": [prompt_text],
                "cache_text_token": [prompt_text_token],
                "cache_speech_token": cache_speech_token,
                "use_cache": False,
            }

            tts_speech, _, _, _ = generate_long(
                frontend=self.frontend,
                text_frontend=self.text_frontend,
                llm=self.llm,
                flow=self.flow,
                text_info=["caption-helper", synth_text],
                cache=cache,
                device=self.device,
                embedding=embedding,
                flow_prompt_token=flow_prompt_token,
                speech_feat=speech_feat,
                use_phoneme=False,
            )
            return tts_speech, self.config.sample_rate


class GLMTTSEngine:
    def __init__(self, config: GLMTTSConfig | None = None) -> None:
        self.config = config or GLMTTSConfig()
        self.peak_vram_mb: int = 0

    def _resolve_device(self) -> str:
        if self.config.device:
            return self.config.device
        import torch

        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def clear_cuda_cache(self) -> None:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            self._update_peak_vram()

    def reset_vram_stats(self) -> None:
        import torch

        self.peak_vram_mb = 0
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def _update_peak_vram(self) -> None:
        import torch

        if torch.cuda.is_available():
            peak = torch.cuda.max_memory_allocated() // (1024 * 1024)
            self.peak_vram_mb = max(self.peak_vram_mb, peak)

    def _resample_and_save(self, audio: Any, sample_rate: int, output_path: Path) -> Path:
        import torch
        import torchaudio

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio = audio.detach().cpu().to(torch.float32)
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)
        if sample_rate != PIPELINE_SAMPLE_RATE:
            audio = torchaudio.transforms.Resample(sample_rate, PIPELINE_SAMPLE_RATE)(audio)
        torchaudio.save(str(output_path), audio, PIPELINE_SAMPLE_RATE)
        return output_path

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        tokens: int | None,
        *,
        output_path: Path,
        reference_text: str | None = None,
    ) -> Path:
        """Synthesize voice-cloned audio via GLM-TTS.

        ``tokens`` is ignored; duration fitting is handled downstream by ``fit_duration``.
        """
        if not glm_tts_installed(self.config):
            raise RuntimeError(
                "GLM-TTS is not installed. Clone https://github.com/zai-org/GLM-TTS, "
                "run `huggingface-cli download zai-org/GLM-TTS --local-dir ckpt`, "
                "and set GLM_TTS_HOME to the repo root. Install extras: "
                "uv pip install -e \".[glm-tts]\" from the GLM-TTS directory."
            )

        runtime = _GLMRuntime.get(self.config)
        audio, sample_rate = runtime.synthesize_utterance(
            text,
            Path(reference_wav),
            reference_text=reference_text,
        )
        result = self._resample_and_save(audio, sample_rate, output_path)
        self._update_peak_vram()
        return result
