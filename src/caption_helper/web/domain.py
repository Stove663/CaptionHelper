from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProjectStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    TRANSCRIBING = "transcribing"
    SPLITTING = "splitting"
    READY = "ready"
    FAILED = "failed"
    SYNTHESIZING = "synthesizing"
    SYNTHESIS_READY = "synthesis_ready"
    SYNTHESIS_FAILED = "synthesis_failed"
    REMUXING = "remuxing"
    REMUX_READY = "remux_ready"
    REMUX_FAILED = "remux_failed"
    BUILDING_REFERENCES = "building_references"


class SyncMode(StrEnum):
    FIXED_SLOT = "fixed-slot"
    NATURAL_PACE = "natural-pace"


class TTSProvider(StrEnum):
    MOSS_TTS = "moss-tts"
    GLM_TTS = "glm-tts"


class GLMPhonemeMode(StrEnum):
    AUTO = "auto"
    ON = "on"
    OFF = "off"


@dataclass(frozen=True)
class PipelineState:
    status: ProjectStatus
    terminal: bool = False
