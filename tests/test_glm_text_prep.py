from __future__ import annotations

from caption_helper.tts.glm_phoneme import resolve_glm_use_phoneme
from caption_helper.tts.glm_text_prep import prepare_glm_mixed_text


class TestPrepareGlmMixedText:
    def test_inserts_space_between_cjk_and_latin(self) -> None:
        assert prepare_glm_mixed_text("打开terminal") == "打开 terminal"

    def test_pure_chinese_unchanged(self) -> None:
        text = "欢迎大家参加本次会议"
        assert prepare_glm_mixed_text(text) == text

    def test_already_spaced_unchanged(self) -> None:
        text = "请大家打开 terminal 窗口"
        assert prepare_glm_mixed_text(text) == text


class TestResolveGlmUsePhoneme:
    def test_auto_enables_for_mixed(self) -> None:
        assert resolve_glm_use_phoneme("打开 terminal 窗口", "auto") is True

    def test_auto_disables_for_pure_chinese(self) -> None:
        assert resolve_glm_use_phoneme("欢迎大家", "auto") is False

    def test_on_always_true(self) -> None:
        assert resolve_glm_use_phoneme("欢迎大家", "on") is True

    def test_off_always_false(self) -> None:
        assert resolve_glm_use_phoneme("打开 terminal", "off") is False
