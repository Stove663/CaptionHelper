from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from caption_helper.web.jobs import JobRunner
    from caption_helper.web.store import ProjectStore

RerunStage = Literal["asr", "references", "synthesis", "remux"]

ASR_ACTIVE_STATUSES = frozenset({"extracting", "transcribing", "splitting"})
REFERENCES_ACTIVE_STATUS = "building_references"


class RerunConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def is_asr_busy(status: str) -> bool:
    return status in ASR_ACTIVE_STATUSES


def is_references_busy(status: str) -> bool:
    return status == REFERENCES_ACTIVE_STATUS


def is_synthesis_busy(status: str, jobs: JobRunner, project_id: str) -> bool:
    if status == "synthesizing":
        return True
    return jobs.get_synthesis_progress(project_id).status == "synthesizing"


def is_remux_busy(status: str) -> bool:
    return status == "remuxing"


def check_rerun_allowed(
    store: ProjectStore,
    jobs: JobRunner,
    project_id: str,
    stage: RerunStage,
) -> None:
    meta = store.get_project(project_id)
    status = meta.status

    asr_busy = is_asr_busy(status)
    refs_busy = is_references_busy(status)
    synth_busy = is_synthesis_busy(status, jobs, project_id)
    remux_busy = is_remux_busy(status)

    if stage != "asr" and asr_busy:
        raise RerunConflictError("ASR processing in progress")
    if stage != "references" and refs_busy:
        raise RerunConflictError("Reference bank build in progress")
    if stage != "synthesis" and synth_busy:
        raise RerunConflictError("Synthesis in progress")
    if stage != "remux" and remux_busy:
        raise RerunConflictError("Remux in progress")

    if stage == "asr" and asr_busy:
        raise RerunConflictError("ASR already in progress")
    if stage == "references" and refs_busy:
        raise RerunConflictError("Reference bank build already in progress")
    if stage == "synthesis" and synth_busy:
        raise RerunConflictError("Synthesis already in progress")
    if stage == "remux" and remux_busy:
        raise RerunConflictError("Remux already in progress")
