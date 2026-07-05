from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from caption_helper.web.domain import GLMPhonemeMode, ProjectStatus, SyncMode, TTSProvider
from caption_helper.web.state import can_transition


@dataclass
class ProjectMeta:
    id: str
    filename: str
    status: str
    created_at: str
    error: str | None = None
    sync_mode: str = SyncMode.FIXED_SLOT.value
    tts_provider: str = TTSProvider.MOSS_TTS.value
    glm_phoneme_mode: str = GLMPhonemeMode.AUTO.value
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "meta.json"

    def create_project(self, filename: str) -> ProjectMeta:
        project_id = str(uuid.uuid4())
        project_dir = self._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "segments").mkdir(exist_ok=True)
        meta = ProjectMeta(
            id=project_id,
            filename=filename,
            status=ProjectStatus.UPLOADED.value,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write_meta(project_id, meta)
        return meta

    def list_projects(self) -> list[ProjectMeta]:
        projects: list[ProjectMeta] = []
        for path in sorted(self.projects_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_dir() and (path / "meta.json").is_file():
                projects.append(self.get_project(path.name))
        return projects

    def get_project(self, project_id: str) -> ProjectMeta:
        meta_path = self._meta_path(project_id)
        if not meta_path.is_file():
            raise FileNotFoundError(f"Project not found: {project_id}")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data.setdefault("schema_version", 1)
        data.setdefault("status", ProjectStatus.UPLOADED.value)
        data.setdefault("sync_mode", SyncMode.FIXED_SLOT.value)
        data.setdefault("tts_provider", TTSProvider.MOSS_TTS.value)
        data.setdefault("glm_phoneme_mode", GLMPhonemeMode.AUTO.value)
        data.pop("asr_provider", None)
        return ProjectMeta(**data)

    def update_sync_mode(self, project_id: str, sync_mode: str) -> ProjectMeta:
        if sync_mode not in {m.value for m in SyncMode}:
            raise ValueError(f"Invalid sync_mode: {sync_mode}")
        meta = self.get_project(project_id)
        meta.sync_mode = sync_mode
        self._write_meta(project_id, meta)
        return meta

    def update_tts_provider(self, project_id: str, provider: str) -> ProjectMeta:
        if provider not in {p.value for p in TTSProvider}:
            raise ValueError(f"Invalid tts_provider: {provider}")
        meta = self.get_project(project_id)
        meta.tts_provider = provider
        self._write_meta(project_id, meta)
        return meta

    def update_status(
        self,
        project_id: str,
        status: str,
        error: str | None = None,
        *,
        allow_recovery_from_failed: bool = False,
    ) -> ProjectMeta:
        meta = self.get_project(project_id)
        if meta.status != status and not can_transition(meta.status, status):
            if not (allow_recovery_from_failed and meta.status == ProjectStatus.FAILED.value and status == ProjectStatus.UPLOADED.value):
                raise ValueError(f"Invalid status transition: {meta.status} -> {status}")
        meta.status = status
        meta.error = error
        self._write_meta(project_id, meta)
        return meta

    def save_upload(self, project_id: str, filename: str, content: bytes) -> Path:
        suffix = Path(filename).suffix or ".mp4"
        dest = self._project_dir(project_id) / f"source{suffix}"
        dest.write_bytes(content)
        return dest

    def project_path(self, project_id: str) -> Path:
        path = self._project_dir(project_id)
        if not path.is_dir():
            raise FileNotFoundError(f"Project not found: {project_id}")
        return path

    def find_source_video(self, project_id: str) -> Path:
        project_dir = self.project_path(project_id)
        matches = list(project_dir.glob("source.*"))
        if not matches:
            raise FileNotFoundError(f"No source video for project {project_id}")
        return matches[0]

    def delete_project(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.is_dir():
            raise FileNotFoundError(f"Project not found: {project_id}")
        shutil.rmtree(project_dir)

    def clear_downstream_artifacts(
        self,
        project_id: str,
        *,
        through: Literal["asr", "tts", "remux"],
    ) -> None:
        project_dir = self.project_path(project_id)

        def unlink_if_exists(name: str) -> None:
            path = project_dir / name
            if path.is_file():
                path.unlink()

        def clear_wavs_in_dir(dirname: str) -> None:
            seg_dir = project_dir / dirname
            if seg_dir.is_dir():
                for wav in seg_dir.glob("*.wav"):
                    wav.unlink()

        def clear_dir(dirname: str, *, recreate: bool = False) -> None:
            dir_path = project_dir / dirname
            if dir_path.is_dir():
                shutil.rmtree(dir_path)
            if recreate:
                dir_path.mkdir(parents=True, exist_ok=True)

        if through == "asr":
            for filename in (
                "audio.wav",
                "subtitles.json",
                "subtitles.srt",
                "subtitles_original.srt",
                "subtitles_edited.srt",
                "subtitles_ripple.srt",
                "modified_segments.json",
                "synthesis_manifest.json",
                "remux_manifest.json",
                "timeline.json",
                "reference_quality.json",
                "reference_overrides.json",
                "output_audio.wav",
                "output_video.mp4",
            ):
                unlink_if_exists(filename)
            clear_wavs_in_dir("segments")
            clear_dir("speaker_refs", recreate=True)
            clear_dir("tts_segments", recreate=True)
        elif through == "tts":
            unlink_if_exists("synthesis_manifest.json")
            unlink_if_exists("timeline.json")
            unlink_if_exists("subtitles_ripple.srt")
            unlink_if_exists("output_audio.wav")
            unlink_if_exists("output_video.mp4")
            unlink_if_exists("remux_manifest.json")
            clear_dir("tts_segments", recreate=True)
        elif through == "remux":
            unlink_if_exists("output_audio.wav")
            unlink_if_exists("output_video.mp4")
            unlink_if_exists("remux_manifest.json")

    def _write_meta(self, project_id: str, meta: ProjectMeta) -> None:
        self._meta_path(project_id).write_text(
            json.dumps(meta.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
