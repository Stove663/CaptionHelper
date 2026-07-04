from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caption_helper.tts.code_mix import detect_language_mode
from caption_helper.tts.preflight import DEFAULT_MODEL

logger = logging.getLogger(__name__)


@dataclass
class MossTTSConfig:
    model: str = DEFAULT_MODEL
    device: str | None = None
    tokens_per_second: float = 25.0
    language: str = "Chinese"


def max_new_tokens_for_slot(tokens: int) -> int:
    """Cap generation length from slot duration to avoid runaway output."""
    return min(4096, max(256, int(tokens) * 4))


class MossTTSEngine:
    """Lazy-loaded MOSS-TTS voice cloning engine (Local-Transformer 1.7B default)."""

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

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        tokens: int | None,
        *,
        language: str | None = None,
        output_path: Path,
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
            if audio.ndim == 1:
                audio = audio.unsqueeze(0)
            torchaudio.save(
                str(output_path),
                audio.detach().cpu().to(torch.float32),
                self._processor.model_config.sampling_rate,
            )

        self._update_peak_vram()
        return output_path
