from __future__ import annotations

import re

# CJK unified + extension blocks
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# Latin words (2+ letters to avoid single-letter noise in mixed text)
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def is_code_mixed(text: str) -> bool:
    """Return True when text contains both CJK and Latin words."""
    return bool(_CJK_RE.search(text)) and bool(_LATIN_WORD_RE.search(text))


def detect_language_mode(text: str) -> str:
    """Return MOSS-TTS language mode: auto, Chinese, or English."""
    has_cjk = bool(_CJK_RE.search(text))
    has_latin = bool(_LATIN_WORD_RE.search(text))
    if has_cjk and has_latin:
        return "auto"
    if has_latin and not has_cjk:
        return "English"
    return "Chinese"
