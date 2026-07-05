from __future__ import annotations

import logging
import re
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

DEFAULT_MODEL = MODEL_LOCAL_V15_4B
MODEL_GLM_TTS = "zai-org/GLM-TTS"
VALID_TTS_PROVIDERS = frozenset({"moss-tts", "glm-tts"})

TOKENS_PER_SECOND_BY_PRESET: dict[str, float] = {
    "local-1.7b": 25.0,
    "local-v1.5-4b": 12.5,
}

TOKENS_PER_SECOND_BY_MODEL: dict[str, float] = {
    MODEL_LOCAL_1_7B: 25.0,
    MODEL_LOCAL_V15_4B: 12.5,
}

# Minimum total VRAM (GB) per model tier
_MIN_VRAM_GB: dict[str, float] = {
    MODEL_LOCAL_1_7B: 8.0,
    MODEL_LOCAL_V15_4B: 12.0,
    MODEL_V15_8B: 20.0,
}

_CUDA_DEVICE_RE = re.compile(r"^cuda:(\d+)$")


def resolve_tts_model(name: str) -> str:
    """Resolve CLI preset alias or pass through full HuggingFace model id."""
    return TTS_MODEL_PRESETS.get(name, name)


def resolve_tokens_per_second(model_id: str, override: float | None = None) -> float:
    """Return tokens/s for duration mapping; CLI override wins when set."""
    if override is not None:
        return override
    for preset, mid in TTS_MODEL_PRESETS.items():
        if model_id == mid:
            return TOKENS_PER_SECOND_BY_PRESET[preset]
    if model_id in TOKENS_PER_SECOND_BY_MODEL:
        return TOKENS_PER_SECOND_BY_MODEL[model_id]
    if "local-transformer-v1.5" in model_id.lower():
        return TOKENS_PER_SECOND_BY_PRESET["local-v1.5-4b"]
    return TOKENS_PER_SECOND_BY_PRESET["local-1.7b"]


def is_8b_model(model_id: str) -> bool:
    normalized = model_id.lower()
    return "moss-tts-v1.5" in normalized and "local" not in normalized


def parse_cuda_device_index(device: str | None) -> int:
    """Parse torch device string to CUDA index; default 0 when CUDA available."""
    if device is None:
        return 0
    match = _CUDA_DEVICE_RE.match(device.strip())
    if match:
        return int(match.group(1))
    if device == "cuda":
        return 0
    raise ValueError(f"Not a CUDA device: {device!r}")


@dataclass
class GPUInfo:
    available: bool
    name: str | None = None
    total_vram_gb: float | None = None
    cuda_version: str | None = None
    device_index: int | None = None


@dataclass
class PreflightResult:
    ok: bool
    message: str
    gpu: GPUInfo
    warnings: list[str] = field(default_factory=list)


def get_gpu_info(device: str | None = None) -> GPUInfo:
    try:
        import torch
    except (ImportError, OSError, ValueError):
        return GPUInfo(available=False)

    if not torch.cuda.is_available():
        return GPUInfo(available=False)

    if device is not None and not device.startswith("cuda"):
        return GPUInfo(available=False)

    try:
        index = parse_cuda_device_index(device)
    except ValueError:
        return GPUInfo(available=False)

    if index < 0 or index >= torch.cuda.device_count():
        return GPUInfo(available=False, device_index=index)

    props = torch.cuda.get_device_properties(index)
    total_gb = props.total_memory / (1024**3)
    cuda_version = getattr(torch.version, "cuda", None)
    return GPUInfo(
        available=True,
        name=props.name,
        total_vram_gb=round(total_gb, 2),
        cuda_version=str(cuda_version) if cuda_version else None,
        device_index=index,
    )


def _min_vram_for_model(model_id: str) -> float:
    if is_8b_model(model_id):
        return _MIN_VRAM_GB[MODEL_V15_8B]
    if model_id == MODEL_LOCAL_V15_4B or "local-transformer-v1.5" in model_id.lower():
        return _MIN_VRAM_GB[MODEL_LOCAL_V15_4B]
    return _MIN_VRAM_GB[MODEL_LOCAL_1_7B]


def check_tts_compatibility(
    model_id: str,
    *,
    provider: str = "moss-tts",
    device: str | None = None,
) -> PreflightResult:
    """Validate GPU + model combination before synthesis."""
    gpu = get_gpu_info(device)
    warnings: list[str] = []

    if provider not in VALID_TTS_PROVIDERS:
        return PreflightResult(
            ok=False,
            message=f"Unknown TTS provider {provider!r}.",
            gpu=gpu,
        )

    if provider == "glm-tts":
        from caption_helper.tts.glm_tts import MIN_VRAM_GB_GLM, glm_tts_installed

        if not glm_tts_installed():
            return PreflightResult(
                ok=False,
                message=(
                    "GLM-TTS is not installed. Clone https://github.com/zai-org/GLM-TTS, "
                    "download checkpoints to ckpt/, set GLM_TTS_HOME, and install GLM-TTS "
                    "dependencies (see README)."
                ),
                gpu=gpu,
            )
        if not gpu.available:
            return PreflightResult(
                ok=False,
                message="GLM-TTS synthesis requires a CUDA GPU.",
                gpu=gpu,
            )
        assert gpu.total_vram_gb is not None
        if gpu.total_vram_gb < MIN_VRAM_GB_GLM:
            return PreflightResult(
                ok=False,
                message=(
                    f"GLM-TTS needs ~{MIN_VRAM_GB_GLM:.0f} GB VRAM but GPU has "
                    f"{gpu.total_vram_gb:.1f} GB."
                ),
                gpu=gpu,
            )
        if gpu.total_vram_gb < 12:
            warnings.append(
                f"GLM-TTS on {gpu.total_vram_gb:.1f} GB GPU may be tight; "
                "use MOSS-TTS local-1.7b if synthesis fails."
            )
        return PreflightResult(ok=True, message="OK", gpu=gpu, warnings=warnings)

    if not gpu.available:
        device_hint = f" on {device}" if device else ""
        return PreflightResult(
            ok=False,
            message=(
                f"MOSS-TTS synthesis requires a CUDA GPU{device_hint}. "
                "Install NVIDIA drivers and CUDA-enabled PyTorch."
            ),
            gpu=gpu,
        )

    assert gpu.total_vram_gb is not None
    min_vram = _min_vram_for_model(model_id)

    if is_8b_model(model_id) and gpu.total_vram_gb <= 16:
        return PreflightResult(
            ok=False,
            message=(
                f"Model {model_id} (~8B) requires >16 GB VRAM. "
                f"Use --tts-model local-v1.5-4b ({MODEL_LOCAL_V15_4B}) on this GPU."
            ),
            gpu=gpu,
        )

    if gpu.total_vram_gb < min_vram:
        return PreflightResult(
            ok=False,
            message=(
                f"Model {model_id} needs ~{min_vram:.0f} GB VRAM on "
                f"cuda:{gpu.device_index} but GPU has {gpu.total_vram_gb:.1f} GB. "
                "Use --tts-model local-1.7b."
            ),
            gpu=gpu,
        )

    if model_id == MODEL_LOCAL_V15_4B and gpu.total_vram_gb < 14:
        warnings.append(
            f"4B model on {gpu.total_vram_gb:.1f} GB GPU may OOM on long segments; "
            "consider local-1.7b if synthesis fails."
        )

    return PreflightResult(ok=True, message="OK", gpu=gpu, warnings=warnings)


def log_gpu_info(model_id: str | None = None, *, device: str | None = None) -> PreflightResult:
    """Log GPU details at startup; returns preflight result if model given."""
    gpu = get_gpu_info(device)
    if gpu.available:
        logger.info(
            "GPU cuda:%s: %s, VRAM: %.1f GB, CUDA: %s",
            gpu.device_index if gpu.device_index is not None else 0,
            gpu.name,
            gpu.total_vram_gb or 0,
            gpu.cuda_version,
        )
    else:
        logger.warning("No CUDA GPU detected; TTS synthesis will not be available")

    if model_id:
        result = check_tts_compatibility(model_id, device=device)
        for warning in result.warnings:
            logger.warning(warning)
        if not result.ok:
            logger.error("TTS preflight: %s", result.message)
        return result

    return PreflightResult(ok=gpu.available, message="GPU logged", gpu=gpu)
