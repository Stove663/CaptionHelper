import json
import time

import pytest
from fastapi.testclient import TestClient

from caption_helper.models import Sentence
from caption_helper.subtitles_json import (
    Cue,
    compute_modified,
    generate_modified_segments,
    initialize_subtitle_files,
    load_subtitles,
    save_subtitles,
    validate_save_request,
)
from caption_helper.web.app import create_app
from caption_helper.web.store import ProjectStore
from caption_helper.tts.preflight import GPUInfo, MODEL_V15_8B, PreflightResult
from tests.helpers import write_test_wav


class TestSubtitlesJson:
    def test_compute_modified_text_only(self) -> None:
        cue = Cue(1, 0, 0, 1000, "你好", "hello")
        assert compute_modified(cue) is True

    def test_original_srt_unchanged_after_save(self, tmp_path) -> None:
        sentences = [Sentence("原文", 0, 0, 1000)]
        initialize_subtitle_files(tmp_path, sentences)
        original = (tmp_path / "subtitles_original.srt").read_text(encoding="utf-8")

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[0].text_edited = "修改后"
        save_subtitles(tmp_path / "subtitles.json", cues)

        assert (tmp_path / "subtitles_original.srt").read_text(encoding="utf-8") == original

    def test_modified_segments(self, tmp_path) -> None:
        sentences = [
            Sentence("a", 0, 0, 1000),
            Sentence("b", 1, 1000, 2000),
        ]
        initialize_subtitle_files(tmp_path, sentences)
        (tmp_path / "segments").mkdir(exist_ok=True)
        (tmp_path / "segments" / "0002_spk1_1000-2000.wav").write_bytes(b"x")

        cues = load_subtitles(tmp_path / "subtitles.json")
        cues[1].text_edited = "changed"
        save_subtitles(tmp_path / "subtitles.json", cues)
        modified = generate_modified_segments(tmp_path, cues)
        assert len(modified) == 1
        assert modified[0]["index"] == 2

    def test_reject_timestamp_change(self) -> None:
        existing = [Cue(1, 0, 100, 500, "a", "a")]
        with pytest.raises(ValueError, match="Timestamps are immutable"):
            validate_save_request(existing, [{"index": 1, "start_ms": 200, "text_edited": "a"}])

    def test_reject_speaker_change(self) -> None:
        existing = [Cue(1, 0, 100, 500, "a", "a")]
        with pytest.raises(ValueError, match="Speaker is immutable"):
            validate_save_request(existing, [{"index": 1, "spk": 1, "text_edited": "a"}])


class TestWebApi:
    @pytest.fixture
    def client(self, tmp_path):
        app = create_app(tmp_path, frontend_dist=tmp_path / "no-frontend")
        return TestClient(app)

    def test_upload_and_list(self, client, monkeypatch) -> None:
        async def noop_enqueue(project_id: str) -> None:
            client.app.state.store.update_status(project_id, "ready")

        monkeypatch.setattr(client.app.state.jobs, "enqueue", noop_enqueue)

        res = client.post(
            "/api/projects",
            files={"file": ("test.mp4", b"fake-video", "video/mp4")},
        )
        assert res.status_code == 202
        project_id = res.json()["id"]

        listed = client.get("/api/projects").json()
        assert any(p["id"] == project_id for p in listed)

    def test_save_subtitles(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        sentences = [Sentence("欢迎", 0, 880, 5195)]
        initialize_subtitle_files(project_dir, sentences)
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        cues[0].text_edited = "欢迎朋友"
        payload = {"cues": [c.__dict__ for c in cues]}
        res = client.put(f"/api/projects/{meta.id}/subtitles", json=payload)
        assert res.status_code == 200

        modified = client.get(f"/api/projects/{meta.id}/modified-segments").json()
        assert len(modified) == 1

    def test_reject_timestamp_via_api(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        sentences = [Sentence("欢迎", 0, 880, 5195)]
        initialize_subtitle_files(project_dir, sentences)
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        payload = {"cues": [{**cues[0].__dict__, "start_ms": 9999}]}
        res = client.put(f"/api/projects/{meta.id}/subtitles", json=payload)
        assert res.status_code == 422

    def test_synthesize_modified_segments(self, client, monkeypatch) -> None:
        gpu = GPUInfo(available=True, name="Tesla T4", total_vram_gb=16.0, cuda_version="12.8")
        monkeypatch.setattr(
            "caption_helper.web.routes.projects.check_tts_compatibility",
            lambda model_id, provider="moss-tts": __import__(
                "caption_helper.tts.preflight", fromlist=["PreflightResult"]
            ).PreflightResult(ok=True, message="OK", gpu=gpu),
        )
        monkeypatch.setattr(
            "caption_helper.web.routes.projects.build_reference_quality_report",
            lambda project_dir, **kw: {"unavailable": [], "cues": [], "speakers": {}},
        )

        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        sentences = [
            Sentence("a", 0, 0, 1000),
            Sentence("b", 1, 1000, 2000),
        ]
        initialize_subtitle_files(project_dir, sentences)
        (project_dir / "segments" / "0001_spk0_0-1000.wav").write_bytes(b"x")
        (project_dir / "segments" / "0002_spk1_1000-2000.wav").write_bytes(b"x")
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        cues[0].text_edited = "changed one"
        cues[1].text_edited = "changed two"
        client.put(
            f"/api/projects/{meta.id}/subtitles",
            json={"cues": [c.__dict__ for c in cues]},
        )

        def fake_synthesize(project_dir, *, engine=None, on_progress=None, **kwargs):
            tts_dir = project_dir / "tts_segments"
            tts_dir.mkdir(exist_ok=True)
            (tts_dir / "0001_spk0_0-1000.wav").write_bytes(b"tts1")
            (tts_dir / "0002_spk1_1000-2000.wav").write_bytes(b"tts2")
            from caption_helper.tts.synthesizer import CueSynthesisRecord, SynthesisResult

            records = [
                CueSynthesisRecord(
                    index=1,
                    spk=0,
                    text_edited="changed one",
                    reference_segment="segments/0001_spk0_0-1000.wav",
                    target_duration_ms=1000,
                    tokens=25,
                    output_path="tts_segments/0001_spk0_0-1000.wav",
                    status="success",
                ),
                CueSynthesisRecord(
                    index=2,
                    spk=1,
                    text_edited="changed two",
                    reference_segment="segments/0002_spk1_1000-2000.wav",
                    target_duration_ms=1000,
                    tokens=25,
                    output_path="tts_segments/0002_spk1_1000-2000.wav",
                    status="success",
                ),
            ]
            result = SynthesisResult(
                model="test-model",
                cues=records,
                completed=2,
                total=2,
            )
            (project_dir / "synthesis_manifest.json").write_text(
                json.dumps(result.to_manifest(), ensure_ascii=False),
                encoding="utf-8",
            )
            store.update_status(meta.id, "synthesis_ready")
            if on_progress:
                on_progress(2, 2)
            return result

        monkeypatch.setattr(
            "caption_helper.web.jobs.synthesize_modified_segments",
            fake_synthesize,
        )
        monkeypatch.setattr(
            "caption_helper.web.jobs.check_tts_compatibility",
            lambda model_id, provider="moss-tts": PreflightResult(ok=True, message="OK", gpu=gpu),
        )
        monkeypatch.setattr(
            "caption_helper.web.jobs.log_gpu_info",
            lambda model_id: PreflightResult(ok=True, message="OK", gpu=gpu),
        )

        res = client.post(
            f"/api/projects/{meta.id}/synthesize",
            json={"skip_unavailable": False},
        )
        assert res.status_code == 202

        for _ in range(20):
            status = client.get(f"/api/projects/{meta.id}/synthesis-status").json()
            if status["status"] != "synthesizing":
                break
            time.sleep(0.05)

        assert len(list((project_dir / "tts_segments").glob("*.wav"))) == 2
        manifest = client.get(f"/api/projects/{meta.id}/synthesis-manifest").json()
        assert manifest["completed"] == 2
        assert manifest["cues"][0]["tokens"] == 25

    def test_synthesize_blocks_8b_on_16gb(self, client, monkeypatch) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        sentences = [Sentence("a", 0, 0, 1000)]
        initialize_subtitle_files(project_dir, sentences)
        (project_dir / "segments" / "0001_spk0_0-1000.wav").write_bytes(b"x")
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        cues[0].text_edited = "changed"
        client.put(
            f"/api/projects/{meta.id}/subtitles",
            json={"cues": [c.__dict__ for c in cues]},
        )

        client.app.state.jobs.set_tts_options(model=MODEL_V15_8B)
        gpu = GPUInfo(available=True, name="Tesla T4", total_vram_gb=16.0, cuda_version="12.8")
        monkeypatch.setattr(
            "caption_helper.web.routes.projects.check_tts_compatibility",
            lambda model_id, provider="moss-tts": PreflightResult(
                ok=False,
                message="Use local-1.7b",
                gpu=gpu,
            ),
        )

        res = client.post(
            f"/api/projects/{meta.id}/synthesize",
            json={"skip_unavailable": False},
        )
        assert res.status_code == 400
        assert "local-1.7b" in res.json()["detail"]

    def test_tts_provider_default(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project = client.get(f"/api/projects/{meta.id}").json()
        assert project["tts_provider"] == "moss-tts"

    def test_tts_provider_set_and_persist(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        res = client.put(
            f"/api/projects/{meta.id}/tts-provider",
            json={"tts_provider": "glm-tts"},
        )
        assert res.status_code == 200
        assert res.json()["tts_provider"] == "glm-tts"
        reloaded = client.get(f"/api/projects/{meta.id}").json()
        assert reloaded["tts_provider"] == "glm-tts"

    def test_tts_provider_rejects_invalid(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        res = client.put(
            f"/api/projects/{meta.id}/tts-provider",
            json={"tts_provider": "other-tts"},
        )
        assert res.status_code == 422

    def test_tts_provider_legacy_meta_defaults(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        meta_path = store.project_path(meta.id) / "meta.json"
        import json

        data = json.loads(meta_path.read_text(encoding="utf-8"))
        del data["tts_provider"]
        meta_path.write_text(json.dumps(data), encoding="utf-8")
        project = client.get(f"/api/projects/{meta.id}").json()
        assert project["tts_provider"] == "moss-tts"

    def test_synthesize_blocks_glm_when_not_installed(self, client, monkeypatch) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        store.update_tts_provider(meta.id, "glm-tts")
        project_dir = store.project_path(meta.id)
        sentences = [Sentence("a", 0, 0, 1000)]
        initialize_subtitle_files(project_dir, sentences)
        (project_dir / "segments" / "0001_spk0_0-1000.wav").write_bytes(b"x")
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        cues[0].text_edited = "changed"
        client.put(
            f"/api/projects/{meta.id}/subtitles",
            json={"cues": [c.__dict__ for c in cues]},
        )

        gpu = GPUInfo(available=True, name="Tesla T4", total_vram_gb=16.0, cuda_version="12.8")
        monkeypatch.setattr(
            "caption_helper.web.routes.projects.build_reference_quality_report",
            lambda project_dir, **kw: {"unavailable": [], "cues": [], "speakers": {}},
        )
        monkeypatch.setattr(
            "caption_helper.web.routes.projects.check_tts_compatibility",
            lambda model_id, provider="moss-tts": PreflightResult(
                ok=False,
                message="GLM-TTS is not installed",
                gpu=gpu,
            ),
        )

        res = client.post(
            f"/api/projects/{meta.id}/synthesize",
            json={"skip_unavailable": False},
        )
        assert res.status_code == 400
        assert "GLM-TTS" in res.json()["detail"]

    def test_remux_project(self, client, monkeypatch) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        (project_dir / "source.mp4").write_bytes(b"video")
        sentences = [Sentence("a", 0, 0, 1000)]
        initialize_subtitle_files(project_dir, sentences)
        write_test_wav(project_dir / "audio.wav", duration_s=1.0)
        write_test_wav(project_dir / "segments" / "0001_spk0_0-1000.wav", duration_s=1.0)
        store.update_status(meta.id, "ready")

        def fake_remux(project_id: str) -> None:
            (project_dir / "output_audio.wav").write_bytes(b"wav")
            (project_dir / "output_video.mp4").write_bytes(b"mp4")
            store.update_status(meta.id, "remux_ready")

        async def fake_enqueue(project_id: str) -> None:
            fake_remux(project_id)

        monkeypatch.setattr(client.app.state.jobs, "enqueue_remux", fake_enqueue)

        res = client.post(f"/api/projects/{meta.id}/remux")
        assert res.status_code == 202

        status = client.get(f"/api/projects/{meta.id}/remux-status").json()
        assert status["status"] == "remux_ready"

        video = client.get(f"/api/projects/{meta.id}/output-video")
        assert video.status_code == 200
        assert "attachment" in video.headers.get("content-disposition", "")

        audio = client.get(f"/api/projects/{meta.id}/output-audio")
        assert audio.status_code == 200

    def test_remux_blocks_missing_tts(self, client) -> None:
        store: ProjectStore = client.app.state.store
        meta = store.create_project("x.mp4")
        project_dir = store.project_path(meta.id)
        sentences = [Sentence("a", 0, 0, 1000)]
        initialize_subtitle_files(project_dir, sentences)
        write_test_wav(project_dir / "audio.wav", duration_s=1.0)
        store.update_status(meta.id, "ready")

        cues = load_subtitles(project_dir / "subtitles.json")
        cues[0].text_edited = "changed"
        client.put(
            f"/api/projects/{meta.id}/subtitles",
            json={"cues": [c.__dict__ for c in cues]},
        )

        res = client.post(f"/api/projects/{meta.id}/remux")
        assert res.status_code == 400
        assert res.json()["detail"]["missing"] == [1]
