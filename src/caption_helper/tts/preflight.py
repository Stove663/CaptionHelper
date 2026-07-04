from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# HuggingFace model ids
MODEL_LOCAL_1_7B = "OpenMOSS-Team/MOSS-TTS-Local-Transformer"
MODEL_LOCAL_V15_4B = "OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5"
MODEL_V15_8B = "OpenMOSS-Team/MOSS-TTS-v1.5"

TTS_MODEL_PRESETS: dict[str, str] = {
    "local-1.7b": MODEL_LOCAL_1_7B,
    "local-v1.5-4b": MODEL_LOCAL_V15_4B,
}

DEFAULT_MODEL = MODEL_LOCAL_1_7B

# Minimum total VRAM (GB) per model tier
_MIN_VRAM_GB: dict[str, float] = {
    MODEL_LOCAL_1_7B: 8.0,
    MODEL_LOCAL_V15_4B: 12.0,
    MODEL_V15_8B: 20.0,
}


def resolve_tts_model(name: str) -> str:
    """Resolve CLI preset alias or pass through full HuggingFace model id."""
    return TTS_MODEL_PRESETS.get(name, name)


def is_8b_model(model_id: str) -> bool:
    normalized = model_id.lower()
    return "moss-tts-v1.5" in normalized and "local" not in normalized


@dataclass
class GPUInfo:
    available: bool
    name: str | None = None
    total_vram_gb: float | None = None
    cuda_version: str | None = None


@dataclass
class PreflightResult:
    ok: bool
    message: str
    gpu: GPUInfo
    warnings: list[str] = field(default_factory=list)


def get_gpu_info() -> GPUInfo:
    try:
        import torch
    except (ImportError, OSError, ValueError):
        return GPUInfo(available=False)

    if not torch.cuda.is_available():
        return GPUInfo(available=False)

    props = torch.cuda.get_device_properties(0)
    total_gb = props.total_memory / (1024**3)
    cuda_version = getattr(torch.version, "cuda", None)
    return GPUInfo(
        available=True,
        name=props.name,
        total_vram_gb=round(total_gb, 2),
        cuda_version=str(cuda_version) if cuda_version else None,
    )


def _min_vram_for_model(model_id: str) -> float:
    if is_8b_model(model_id):
        return _MIN_VRAM_GB[MODEL_V15_8B]
    if model_id == MODEL_LOCAL_V15_4B or "local-transformer-v1.5" in model_id.lower():
        return _MIN_VRAM_GB[MODEL_LOCAL_V15_4B]
    return _MIN_VRAM_GB[MODEL_LOCAL_1_7B]


def check_tts_compatibility(model_id: str) -> PreflightResult:
    """Validate GPU + model combination before synthesis."""
    gpu = get_gpu_info()
    warnings: list[str] = []

    if not gpu.available:
        return PreflightResult(
            ok=False,
            message="MOSS-TTS synthesis requires a CUDA GPU. Install NVIDIA drivers and CUDA-enabled PyTorch.",
            gpu=gpu,
        )

    assert gpu.total_vram_gb is not None
    min_vram = _min_vram_for_model(model_id)

    if is_8b_model(model_id) and gpu.total_vram_gb <= 16:
        return PreflightResult(
            ok=False,
            message=(
                f"Model {model_id} (~8B) requires >16 GB VRAM. "
                f"Use --tts-model local-1.7b ({MODEL_LOCAL_1_7B}) on this GPU."
            ),
            gpu=gpu,
        )

    if gpu.total_vram_gb < min_vram:
        return PreflightResult(
            ok=False,
            message=(
                f"Model {model_id} needs ~{min_vram:.0f} GB VRAM but GPU has "
                f"{gpu.total_vram_gb:.1f} GB. Use --tts-model local-1.7b."
            ),
            gpu=gpu,
        )

    if model_id == MODEL_LOCAL_V15_4B and gpu.total_vram_gb < 14:
        warnings.append(
            f"4B model on {gpu.total_vram_gb:.1f} GB GPU may OOM on long segments; "
            "consider local-1.7b if synthesis fails."
        )

    return PreflightResult(ok=True, message="OK", gpu=gpu, warnings=warnings)


def log_gpu_info(model_id: str | None = None) -> PreflightResult:
    """Log GPU details at startup; returns preflight result if model given."""
    gpu = get_gpu_info()
    if gpu.available:
        logger.info(
            "GPU: %s, VRAM: %.1f GB, CUDA: %s",
            gpu.name,
            gpu.total_vram_gb or 0,
            gpu.cuda_version,
        )
    else:
        logger.warning("No CUDA GPU detected; TTS synthesis will not be available")

    if model_id:
        result = check_tts_compatibility(model_id)
        for warning in result.warnings:
            logger.warning(warning)
        if not result.ok:
            logger.error("TTS preflight: %s", result.message)
        return result

    return PreflightResult(ok=gpu.available, message="GPU logged", gpu=gpu)
