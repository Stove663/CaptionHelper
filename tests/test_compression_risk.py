from __future__ import annotations

from caption_helper.subtitles_json import Cue
from caption_helper.tts.compression_risk import (
    assess_cue_compression,
    compression_risks_at_risk,
    estimate_speech_ms,
)


class TestCompressionRisk:
    def test_pure_chinese_fits_slot(self) -> None:
        cue = Cue(1, 0, 0, 2400, "你好世界", "你好世界", modified=True)
        risk = assess_cue_compression(cue)
        assert risk.compression_ratio <= 1.3
        assert not risk.at_risk

    def test_pure_english_long_text_at_risk(self) -> None:
        text = "Docker container orchestration platform deployment"
        cue = Cue(1, 0, 0, 1200, "短", text, modified=True)
        risk = assess_cue_compression(cue)
        assert risk.latin_chars > 0
        assert risk.at_risk

    def test_mixed_zh_en_at_risk(self) -> None:
        text = "今天我们学习 Docker container orchestration platform 的基本概念"
        cue = Cue(1, 0, 0, 2000, "原句", text, modified=True)
        risk = assess_cue_compression(cue)
        assert risk.cjk_chars > 0
        assert risk.latin_chars > 0
        assert risk.at_risk

    def test_scan_returns_only_modified_at_risk(self) -> None:
        cues = [
            Cue(1, 0, 0, 1000, "a", "a", modified=False),
            Cue(2, 0, 1000, 2000, "b", "very long English replacement phrase here", modified=True),
        ]
        risks = compression_risks_at_risk(cues)
        assert len(risks) == 1
        assert risks[0].index == 2
