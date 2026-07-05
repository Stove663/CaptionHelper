from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from caption_helper.tts.audio import PIPELINE_SAMPLE_RATE
from caption_helper.tts.code_mix import detect_language_mode
from caption_helper.tts.preflight import DEFAULT_MODEL, resolve_tokens_per_second

logger = logging.getLogger(__name__)


@dataclass
class MossTTSConfig:
    model: str = DEFAULT_MODEL
    device: str | None = None
    tokens_per_second: float = field(
        default_factory=lambda: resolve_tokens_per_second(DEFAULT_MODEL)
    )
    language: str = "Chinese"


def max_new_tokens_for_slot(tokens: int) -> int:
    """Cap generation length from slot duration to avoid runaway output."""
    return min(4096, max(256, int(tokens) * 4))


def _normalize_audio(audio: Any, sample_rate: int) -> tuple[Any, int]:
    """Downmix to mono and resample to pipeline rate."""
    import torch
    import torchaudio

    audio = audio.detach().cpu().to(torch.float32)
    if audio.ndim == 1:
        audio = audio.unsqueeze(0)
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)
    if sample_rate != PIPELINE_SAMPLE_RATE:
        audio = torchaudio.transforms.Resample(sample_rate, PIPELINE_SAMPLE_RATE)(audio)
    return audio, PIPELINE_SAMPLE_RATE


class MossTTSEngine:
    """Lazy-loaded MOSS-TTS voice cloning engine (Local-Transformer-v1.5 4B default)."""

    def __init__(self, config: MossTTSConfig | None = None) -> None:
        self.config = config or MossTTSConfig()
        self._model: Any = None
        self._processor: Any = None
        self._device: str = "cpu"
        self.peak_vram_mb: int = 0

    def _resolve_device(self) -> str:
        if self.config.device:
            return self.config.device
        import torch

        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def _cuda_device_index(self) -> int | None:
        device = self._resolve_device()
        if device.startswith("cuda:"):
            return int(device.split(":", 1)[1])
        if device == "cuda":
            return 0
        return None

    def _configure_cuda_backends(self) -> None:
        import torch

        if torch.cuda.is_available():
            torch.backends.cuda.enable_cudnn_sdp(False)

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        import torch
        from transformers import AutoModel, AutoProcessor

        self._configure_cuda_backends()
        device = self._resolve_device()
        logger.info("Loading MOSS-TTS model %s on %s", self.config.model, device)

        processor = AutoProcessor.from_pretrained(
            self.config.model,
            trust_remote_code=True,
        )
        processor.audio_tokenizer = processor.audio_tokenizer.to(device)

        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        model = AutoModel.from_pretrained(
            self.config.model,
            trust_remote_code=True,
            attn_implementation="sdpa",
            dtype=dtype,
        ).to(device)

        model.eval()
        self._model = model
        self._processor = processor
        self._device = device

    def clear_cuda_cache(self) -> None:
        import torch

        if torch.cuda.is_available():
            index = self._cuda_device_index()
            if index is not None:
                with torch.cuda.device(index):
                    torch.cuda.empty_cache()
            else:
                torch.cuda.empty_cache()
            self._update_peak_vram()

    def reset_vram_stats(self) -> None:
        import torch

        self.peak_vram_mb = 0
        if torch.cuda.is_available():
            index = self._cuda_device_index()
            if index is not None:
                with torch.cuda.device(index):
                    torch.cuda.reset_peak_memory_stats()
            else:
                torch.cuda.reset_peak_memory_stats()

    def _update_peak_vram(self) -> None:
        import torch

        if not torch.cuda.is_available():
            return
        index = self._cuda_device_index()
        if index is not None:
            with torch.cuda.device(index):
                peak = torch.cuda.max_memory_allocated() // (1024 * 1024)
        else:
            peak = torch.cuda.max_memory_allocated() // (1024 * 1024)
        self.peak_vram_mb = max(self.peak_vram_mb, peak)

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        tokens: int | None,
        *,
        language: str | None = None,
        output_path: Path,
        reference_text: str | None = None,
    ) -> Path:
        """Synthesize voice-cloned audio and write WAV to output_path.

        When ``tokens`` is None (natural-pace mode), MOSS-TTS runs without a
        duration token constraint.
        """
        self._ensure_loaded()
        import torch
        import torchaudio

        reference_wav = Path(reference_wav)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mode = language or detect_language_mode(text)
        user_kwargs: dict[str, Any] = {
            "text": text,
            "reference": [str(reference_wav)],
        }
        if tokens is not None:
            user_kwargs["tokens"] = int(tokens)
        if mode != "auto":
            user_kwargs["language"] = mode

        conversations = [[self._processor.build_user_message(**user_kwargs)]]
        max_tokens = max_new_tokens_for_slot(tokens) if tokens is not None else 4096

        with torch.no_grad():
            batch = self._processor(conversations, mode="generation")
            input_ids = batch["input_ids"].to(self._device)
            attention_mask = batch["attention_mask"].to(self._device)
            outputs = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_tokens,
            )

            messages = self._processor.decode(outputs)
            if not messages:
                raise RuntimeError("MOSS-TTS returned no audio")
            audio = messages[0].audio_codes_list[0]
            sample_rate = self._processor.model_config.sampling_rate
            audio, sample_rate = _normalize_audio(audio, sample_rate)
            torchaudio.save(str(output_path), audio, sample_rate)

        self._update_peak_vram()
        return output_path
