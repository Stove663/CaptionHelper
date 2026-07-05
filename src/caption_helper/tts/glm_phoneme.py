from __future__ import annotations

from caption_helper.tts.code_mix import is_code_mixed
from caption_helper.tts.compression_risk import SYNC_MODE_FIXED

VALID_GLM_PHONEME_MODES = frozenset({"auto", "on", "off"})
DEFAULT_GLM_PHONEME_MODE = "auto"

GLM_PROVIDER_GUIDANCE = (
    "GLM-TTS 在固定槽位模式下无法使用时长 token 约束，中英混合片段的英文发音可能被压缩。"
    "建议切换为自然语速模式。"
)


def resolve_glm_use_phoneme(text: str, mode: str) -> bool:
    """Resolve whether GLM-TTS Phoneme-in should be enabled for ``text``."""
    if mode == "on":
        return True
    if mode == "off":
        return False
    return is_code_mixed(text)


def count_code_mixed_modified(cues) -> int:
    """Count modified cues classified as zh-en code-mixed."""
    return sum(1 for c in cues if c.modified and is_code_mixed(c.text_edited))


def glm_provider_guidance(
    *,
    tts_provider: str,
    sync_mode: str,
    code_mixed_modified_count: int,
) -> str | None:
    if (
        tts_provider == "glm-tts"
        and sync_mode == SYNC_MODE_FIXED
        and code_mixed_modified_count > 0
    ):
        return GLM_PROVIDER_GUIDANCE
    return None
