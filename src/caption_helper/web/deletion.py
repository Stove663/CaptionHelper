from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from caption_helper.web.lifecycle_policy import LifecyclePolicy
from caption_helper.web.state import is_project_busy
from caption_helper.web.store import ProjectStore


@dataclass(frozen=True)
class DeletionResult:
    project_id: str
    mode: str


@dataclass(frozen=True)
class RestoreResult:
    project_id: str
    restored: bool


class ProjectDeletionService:
    def __init__(self, store: ProjectStore, policy: LifecyclePolicy | None = None) -> None:
        self.store = store
        self.policy = policy or LifecyclePolicy()

    def delete_project(self, project_id: str) -> DeletionResult:
        if self.policy.deletion_mode == "soft":
            self._soft_delete(project_id)
        else:
            self.store.delete_project(project_id)
        return DeletionResult(project_id=project_id, mode=self.policy.deletion_mode)

    def restore_project(self, project_id: str) -> RestoreResult:
        trash_dir = self.store.data_dir / "trash" / project_id
        target_dir = self.store._project_dir(project_id)
        if not trash_dir.is_dir():
            return RestoreResult(project_id=project_id, restored=False)
        if target_dir.exists():
            raise FileExistsError(f"Project already exists: {project_id}")
        shutil.move(str(trash_dir), str(target_dir))
        return RestoreResult(project_id=project_id, restored=True)

    def purge_expired_projects(self, jobs, *, retention_days: int | None = None) -> list[str]:
        cutoff_days = retention_days if retention_days is not None else self.policy.retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
        deleted: list[str] = []
        for meta in self.store.list_projects():
            if is_project_busy(meta.status):
                continue
            created = datetime.fromisoformat(meta.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < cutoff:
                if self.policy.deletion_mode == "soft":
                    self._soft_delete(meta.id)
                else:
                    self.store.delete_project(meta.id)
                deleted.append(meta.id)
        return deleted

    def _soft_delete(self, project_id: str) -> None:
        project_dir = self.store.project_path(project_id)
        trash_dir = self.store.data_dir / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        target = trash_dir / project_id
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(project_dir), str(target))
