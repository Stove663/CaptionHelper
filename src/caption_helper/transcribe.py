from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from caption_helper.models import Sentence

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"
DEFAULT_VAD_MODEL = "fsmn-vad"
DEFAULT_SPK_MODEL = "cam++"
DEFAULT_LANGUAGE = "中文"


@dataclass
class TranscriberConfig:
    device: str | None = None
    hub: str | None = None
    language: str = DEFAULT_LANGUAGE
    max_single_segment_time: int = 30_000
    model: str = DEFAULT_MODEL
    vad_model: str = DEFAULT_VAD_MODEL
    spk_model: str = DEFAULT_SPK_MODEL


class BaseTranscriber(Protocol):
    def transcribe(self, audio_path: str) -> list[Sentence]: ...


def resolve_device(device: str | None) -> str:
    if device is not None:
        return device
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


def sentences_from_sentence_info(sentence_info: list[dict[str, Any]]) -> list[Sentence]:
    """Map FunASR sentence_info to Sentence list."""
    sentences: list[Sentence] = []
    for item in sentence_info:
        text = item.get("text") or item.get("sentence") or ""
        sentences.append(
            Sentence(
                text=str(text).strip(),
                spk=int(item["spk"]),
                start=int(item["start"]),
                end=int(item["end"]),
            )
        )
    return sentences


class FunASRTranscriber:
    """FunASR wrapper for Fun-ASR-Nano + VAD + speaker diarization."""

    def __init__(self, config: TranscriberConfig | None = None) -> None:
        self.config = config or TranscriberConfig()
        self._model = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        from funasr import AutoModel

        device = resolve_device(self.config.device)
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "vad_model": self.config.vad_model,
            "spk_model": self.config.spk_model,
            "vad_kwargs": {"max_single_segment_time": self.config.max_single_segment_time},
            "trust_remote_code": True,
            "device": device,
        }
        if self.config.hub:
            kwargs["hub"] = self.config.hub

        logger.info("Loading FunASR model on %s", device)
        self._model = AutoModel(**kwargs)
        return self._model

    def transcribe(self, audio_path: str) -> list[Sentence]:
        model = self._load_model()
        result = model.generate(
            input=[audio_path],
            cache={},
            batch_size=1,
            language=self.config.language,
        )
        if not result:
            return []
        sentence_info = result[0].get("sentence_info") or []
        return sentences_from_sentence_info(sentence_info)


Transcriber = FunASRTranscriber


def get_transcriber(config: TranscriberConfig | None = None) -> BaseTranscriber:
    return FunASRTranscriber(config)
