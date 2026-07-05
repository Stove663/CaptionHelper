from __future__ import annotations

import re

from caption_helper.tts.code_mix import is_code_mixed

_CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"


def prepare_glm_mixed_text(text: str) -> str:
    """Insert spaces at CJK↔Latin boundaries for GLM-TTS mixed-text input."""
    if not is_code_mixed(text):
        return text

    spaced = re.sub(rf"({_CJK})([A-Za-z])", r"\1 \2", text)
    spaced = re.sub(rf"([A-Za-z])({_CJK})", r"\1 \2", spaced)
    spaced = re.sub(r"\s+", " ", spaced).strip()
    return spaced
