from __future__ import annotations

from dataclasses import dataclass, field

from caption_helper.tts.preflight import GPUInfo, get_gpu_info


@dataclass
class AsrPreflightResult:
    ok: bool
    message: str
    gpu: GPUInfo
    warnings: list[str] = field(default_factory=list)


def check_asr_compatibility(*, hub: str | None = None) -> AsrPreflightResult:
    del hub  # reserved for future hub-specific checks
    return AsrPreflightResult(ok=True, message="FunASR ready", gpu=get_gpu_info())
