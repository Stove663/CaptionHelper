from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from caption_helper.tts.glm_phoneme import GLM_PROVIDER_GUIDANCE
from caption_helper.tts.compression_risk import SYNC_MODE_FIXED, SYNC_MODE_NATURAL
from caption_helper.tts.glm_phoneme import glm_provider_guidance
from caption_helper.web.app import create_app
from caption_helper.web.store import ProjectStore


class TestGlmProviderGuidance:
    def test_returns_guidance_for_glm_fixed_slot_mixed(self) -> None:
        guidance = glm_provider_guidance(
            tts_provider="glm-tts",
            sync_mode=SYNC_MODE_FIXED,
            code_mixed_modified_count=1,
        )
        assert guidance == GLM_PROVIDER_GUIDANCE

    def test_none_for_moss(self) -> None:
        assert (
            glm_provider_guidance(
                tts_provider="moss-tts",
                sync_mode=SYNC_MODE_FIXED,
                code_mixed_modified_count=1,
            )
            is None
        )

    def test_none_for_natural_pace(self) -> None:
        assert (
            glm_provider_guidance(
                tts_provider="glm-tts",
                sync_mode=SYNC_MODE_NATURAL,
                code_mixed_modified_count=1,
            )
            is None
        )


class TestCompressionRiskApi:
    @pytest.fixture
    def client(self, tmp_path):
        app = create_app(tmp_path, frontend_dist=tmp_path / "no-frontend")
        return TestClient(app)

    def test_includes_provider_guidance_for_glm(self, client) -> None:
        from caption_helper.web.store import ProjectStore

        store: ProjectStore = client.app.state.store
        meta = store.create_project("lecture.mp4")
        project_dir = store.project_path(meta.id)
        store.update_tts_provider(meta.id, "glm-tts")

        cues = [
            {
                "index": 1,
                "spk": 0,
                "start_ms": 0,
                "end_ms": 2000,
                "text_original": "打开终端窗口",
                "text_edited": "打开 terminal 窗口",
                "modified": True,
            }
        ]
        (project_dir / "subtitles.json").write_text(
            json.dumps({"cues": cues}, ensure_ascii=False),
            encoding="utf-8",
        )

        res = client.get(f"/api/projects/{meta.id}/compression-risk")
        assert res.status_code == 200
        data = res.json()
        assert data["code_mixed_modified_count"] == 1
        assert data["provider_guidance"] == GLM_PROVIDER_GUIDANCE

    def test_no_provider_guidance_for_moss(self, client) -> None:
        from caption_helper.web.store import ProjectStore

        store: ProjectStore = client.app.state.store
        meta = store.create_project("lecture.mp4")
        project_dir = store.project_path(meta.id)

        cues = [
            {
                "index": 1,
                "spk": 0,
                "start_ms": 0,
                "end_ms": 2000,
                "text_original": "打开终端窗口",
                "text_edited": "打开 terminal 窗口",
                "modified": True,
            }
        ]
        (project_dir / "subtitles.json").write_text(
            json.dumps({"cues": cues}, ensure_ascii=False),
            encoding="utf-8",
        )

        res = client.get(f"/api/projects/{meta.id}/compression-risk")
        assert res.status_code == 200
        assert res.json()["provider_guidance"] is None
