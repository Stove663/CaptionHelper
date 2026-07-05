from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from caption_helper.web.deletion import ProjectDeletionService
from caption_helper.web.lifecycle_policy import LifecyclePolicy
from caption_helper.web.rerun import is_synthesis_busy
from caption_helper.web.state import is_project_busy

if TYPE_CHECKING:
    from caption_helper.web.jobs import JobRunner
    from caption_helper.web.store import ProjectStore

logger = logging.getLogger(__name__)

DEFAULT_POLICY = LifecyclePolicy()
CLEANUP_INTERVAL_SECONDS = DEFAULT_POLICY.cleanup_interval_seconds
STARTUP_DELAY_SECONDS = DEFAULT_POLICY.startup_delay_seconds


def is_project_busy_for_cleanup(status: str, jobs: JobRunner, project_id: str) -> bool:
    return is_project_busy(status) or is_synthesis_busy(status, jobs, project_id)


def purge_expired_projects(
    store: ProjectStore,
    jobs: JobRunner,
    *,
    retention_days: int = DEFAULT_POLICY.retention_days,
) -> list[str]:
    deletion_service = ProjectDeletionService(store, DEFAULT_POLICY)
    deleted = deletion_service.purge_expired_projects(jobs, retention_days=retention_days)
    for project_id in deleted:
        logger.info("Purged expired project %s", project_id)
    return deleted
