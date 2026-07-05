from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from caption_helper.tts.code_mix import detect_language_mode, is_code_mixed
from caption_helper.tts.moss_tts import max_new_tokens_for_slot
from caption_helper.tts.preflight import (
    MODEL_LOCAL_1_7B,
    MODEL_LOCAL_V15_4B,
    MODEL_V15_8B,
    GPUInfo,
    check_tts_compatibility,
    is_8b_model,
    resolve_tts_model,
)


class TestCodeMix:
    def test_pure_chinese(self) -> None:
        assert is_code_mixed("欢迎大家参加本次会议") is False
        assert detect_language_mode("欢迎大家参加本次会议") == "Chinese"

    def test_pure_english(self) -> None:
        assert is_code_mixed("Welcome everyone") is False
        assert detect_language_mode("Welcome everyone") == "English"

    def test_zh_en_mixed(self) -> None:
        text = "请大家打开 terminal 窗口"
        assert is_code_mixed(text) is True
        assert detect_language_mode(text) == "auto"

    def test_chinese_with_numbers(self) -> None:
        text = "会议在2026年3月5日举行"
        assert is_code_mixed(text) is False
        assert detect_language_mode(text) == "Chinese"


class TestPreflight:
    def test_resolve_presets(self) -> None:
        assert resolve_tts_model("local-1.7b") == MODEL_LOCAL_1_7B
        assert resolve_tts_model("local-v1.5-4b") == MODEL_LOCAL_V15_4B

    def test_is_8b_model(self) -> None:
        assert is_8b_model(MODEL_V15_8B) is True
        assert is_8b_model(MODEL_LOCAL_1_7B) is False

    def test_blocks_8b_on_16gb(self) -> None:
        gpu = GPUInfo(available=True, name="Tesla T4", total_vram_gb=16.0, cuda_version="12.8")
        with patch("caption_helper.tts.preflight.get_gpu_info", return_value=gpu):
            result = check_tts_compatibility(MODEL_V15_8B)
        assert result.ok is False
        assert "local-1.7b" in result.message

    def test_allows_1_7b_on_t4(self) -> None:
        gpu = GPUInfo(available=True, name="Tesla T4", total_vram_gb=16.0, cuda_version="12.8")
        with patch("caption_helper.tts.preflight.get_gpu_info", return_value=gpu):
            result = check_tts_compatibility(MODEL_LOCAL_1_7B)
        assert result.ok is True

    def test_blocks_4b_on_8gb(self) -> None:
        gpu = GPUInfo(available=True, name="GTX 1070", total_vram_gb=8.0, cuda_version="12.1")
        with patch("caption_helper.tts.preflight.get_gpu_info", return_value=gpu):
            result = check_tts_compatibility(MODEL_LOCAL_V15_4B)
        assert result.ok is False

    def test_no_cuda(self) -> None:
        gpu = GPUInfo(available=False)
        with patch("caption_helper.tts.preflight.get_gpu_info", return_value=gpu):
            result = check_tts_compatibility(MODEL_LOCAL_1_7B)
        assert result.ok is False
        assert "CUDA" in result.message


class TestMaxNewTokens:
    def test_caps_from_slot(self) -> None:
        assert max_new_tokens_for_slot(25) == 256
        assert max_new_tokens_for_slot(100) == 400
        assert max_new_tokens_for_slot(2000) == 4096
