from __future__ import annotations

import re
from dataclasses import dataclass

from caption_helper.subtitles_json import Cue

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[A-Za-z]")

MS_PER_CJK = 120
MS_PER_LATIN = 60
COMPRESSION_RISK_THRESHOLD = 1.3

SYNC_MODE_FIXED = "fixed-slot"
SYNC_MODE_NATURAL = "natural-pace"
VALID_SYNC_MODES = {SYNC_MODE_FIXED, SYNC_MODE_NATURAL}


@dataclass
class CompressionRisk:
    index: int
    text_edited: str
    slot_ms: int
    estimated_ms: int
    compression_ratio: float
    at_risk: bool
    cjk_chars: int
    latin_chars: int


def count_speech_chars(text: str) -> tuple[int, int]:
    """Return (cjk_char_count, latin_char_count) for duration estimation."""
    cjk = len(_CJK_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    return cjk, latin


def estimate_speech_ms(text: str) -> int:
    cjk, latin = count_speech_chars(text)
    return cjk * MS_PER_CJK + latin * MS_PER_LATIN


def assess_cue_compression(cue: Cue) -> CompressionRisk:
    slot_ms = max(1, cue.end_ms - cue.start_ms)
    cjk, latin = count_speech_chars(cue.text_edited)
    estimated_ms = cjk * MS_PER_CJK + latin * MS_PER_LATIN
    ratio = estimated_ms / slot_ms if estimated_ms > 0 else 0.0
    return CompressionRisk(
        index=cue.index,
        text_edited=cue.text_edited,
        slot_ms=slot_ms,
        estimated_ms=estimated_ms,
        compression_ratio=ratio,
        at_risk=ratio > COMPRESSION_RISK_THRESHOLD,
        cjk_chars=cjk,
        latin_chars=latin,
    )


def scan_compression_risks(cues: list[Cue]) -> list[CompressionRisk]:
    return [assess_cue_compression(c) for c in cues if c.modified]


def compression_risks_at_risk(cues: list[Cue]) -> list[CompressionRisk]:
    return [r for r in scan_compression_risks(cues) if r.at_risk]
