from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ProjectMeta:
    id: str
    filename: str
    status: str
    created_at: str
    error: str | None = None
    sync_mode: str = "fixed-slot"

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
            status="uploaded",
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
        data.setdefault("sync_mode", "fixed-slot")
        return ProjectMeta(**data)

    def update_sync_mode(self, project_id: str, sync_mode: str) -> ProjectMeta:
        from caption_helper.tts.compression_risk import VALID_SYNC_MODES

        if sync_mode not in VALID_SYNC_MODES:
            raise ValueError(f"Invalid sync_mode: {sync_mode}")
        meta = self.get_project(project_id)
        meta.sync_mode = sync_mode
        self._write_meta(project_id, meta)
        return meta

    def update_status(self, project_id: str, status: str, error: str | None = None) -> ProjectMeta:
        meta = self.get_project(project_id)
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

    def _write_meta(self, project_id: str, meta: ProjectMeta) -> None:
        self._meta_path(project_id).write_text(
            json.dumps(meta.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
