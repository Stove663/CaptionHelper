import os
import sys
import types

import pytest

from caption_helper.network.mirrors import apply_china_mirror_defaults


class TestApplyChinaMirrorDefaults:
    def test_sets_defaults_when_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("HF_ENDPOINT", raising=False)
        monkeypatch.delenv("HF_HUB_ENABLE_HF_TRANSFER", raising=False)

        apply_china_mirror_defaults()

        assert os.environ["HF_ENDPOINT"] == "https://hf-mirror.com"
        assert os.environ["HF_HUB_ENABLE_HF_TRANSFER"] == "0"

    def test_preserves_existing_values(self, monkeypatch) -> None:
        monkeypatch.setenv("HF_ENDPOINT", "https://huggingface.co")
        monkeypatch.setenv("HF_HUB_ENABLE_HF_TRANSFER", "1")

        apply_china_mirror_defaults()

        assert os.environ["HF_ENDPOINT"] == "https://huggingface.co"
        assert os.environ["HF_HUB_ENABLE_HF_TRANSFER"] == "1"

    def test_idempotent(self, monkeypatch) -> None:
        monkeypatch.delenv("HF_ENDPOINT", raising=False)
        monkeypatch.delenv("HF_HUB_ENABLE_HF_TRANSFER", raising=False)

        apply_china_mirror_defaults()
        apply_china_mirror_defaults()

        assert os.environ["HF_ENDPOINT"] == "https://hf-mirror.com"
        assert os.environ["HF_HUB_ENABLE_HF_TRANSFER"] == "0"

    def test_cli_entry_applies_defaults(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("HF_ENDPOINT", raising=False)
        monkeypatch.setattr("caption_helper.cli.process", lambda *args, **kwargs: tmp_path)

        from caption_helper.cli import main

        video = tmp_path / "test.mp4"
        video.write_bytes(b"x")
        assert main(["process", str(video)]) == 0
        assert os.environ["HF_ENDPOINT"] == "https://hf-mirror.com"


class TestTranscriberHub:
    def test_load_model_omits_hub_by_default(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        def fake_auto_model(**kwargs: object) -> str:
            captured.update(kwargs)
            return "model"

        fake_funasr = types.SimpleNamespace(AutoModel=fake_auto_model)
        monkeypatch.setitem(sys.modules, "funasr", fake_funasr)

        from caption_helper.transcribe import Transcriber, TranscriberConfig

        transcriber = Transcriber(TranscriberConfig())
        assert transcriber.config.hub is None
        transcriber._load_model()
        assert "hub" not in captured

    def test_load_model_passes_hub_hf_when_set(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        def fake_auto_model(**kwargs: object) -> str:
            captured.update(kwargs)
            return "model"

        fake_funasr = types.SimpleNamespace(AutoModel=fake_auto_model)
        monkeypatch.setitem(sys.modules, "funasr", fake_funasr)

        from caption_helper.transcribe import Transcriber, TranscriberConfig

        transcriber = Transcriber(TranscriberConfig(hub="hf"))
        transcriber._load_model()
        assert captured["hub"] == "hf"

    def test_job_runner_pipeline_options_default_hub_none(self) -> None:
        from caption_helper.web.jobs import JobRunner
        from caption_helper.web.store import ProjectStore

        runner = JobRunner(ProjectStore("/tmp/unused"))
        assert runner._pipeline_options.get("hub") is None
