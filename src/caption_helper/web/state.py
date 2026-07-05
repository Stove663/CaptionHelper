from __future__ import annotations

from caption_helper.web.domain import ProjectStatus

ASR_ACTIVE_STATUSES = frozenset(
    {
        ProjectStatus.EXTRACTING.value,
        ProjectStatus.TRANSCRIBING.value,
        ProjectStatus.SPLITTING.value,
    }
)

TERMINAL_STATUSES = frozenset(
    {
        ProjectStatus.FAILED.value,
        ProjectStatus.SYNTHESIS_FAILED.value,
        ProjectStatus.REMUX_FAILED.value,
        ProjectStatus.SYNTHESIS_READY.value,
        ProjectStatus.REMUX_READY.value,
    }
)

ACTIVE_STATUSES = frozenset(
    {
        ProjectStatus.UPLOADED.value,
        ProjectStatus.EXTRACTING.value,
        ProjectStatus.TRANSCRIBING.value,
        ProjectStatus.SPLITTING.value,
        ProjectStatus.BUILDING_REFERENCES.value,
        ProjectStatus.SYNTHESIZING.value,
        ProjectStatus.REMUXING.value,
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ProjectStatus.UPLOADED.value: frozenset(
        {ProjectStatus.EXTRACTING.value, ProjectStatus.BUILDING_REFERENCES.value, ProjectStatus.FAILED.value}
    ),
    ProjectStatus.EXTRACTING.value: frozenset({ProjectStatus.TRANSCRIBING.value, ProjectStatus.FAILED.value}),
    ProjectStatus.TRANSCRIBING.value: frozenset({ProjectStatus.SPLITTING.value, ProjectStatus.FAILED.value}),
    ProjectStatus.SPLITTING.value: frozenset({ProjectStatus.READY.value, ProjectStatus.FAILED.value}),
    ProjectStatus.READY.value: frozenset(
        {
            ProjectStatus.BUILDING_REFERENCES.value,
            ProjectStatus.SYNTHESIZING.value,
            ProjectStatus.REMUXING.value,
        }
    ),
    ProjectStatus.BUILDING_REFERENCES.value: frozenset({ProjectStatus.READY.value, ProjectStatus.FAILED.value}),
    ProjectStatus.SYNTHESIZING.value: frozenset({ProjectStatus.SYNTHESIS_READY.value, ProjectStatus.SYNTHESIS_FAILED.value}),
    ProjectStatus.SYNTHESIS_READY.value: frozenset({ProjectStatus.REMUXING.value, ProjectStatus.FAILED.value}),
    ProjectStatus.SYNTHESIS_FAILED.value: frozenset({ProjectStatus.SYNTHESIZING.value, ProjectStatus.FAILED.value}),
    ProjectStatus.REMUXING.value: frozenset({ProjectStatus.REMUX_READY.value, ProjectStatus.REMUX_FAILED.value}),
    ProjectStatus.REMUX_READY.value: frozenset(),
    ProjectStatus.REMUX_FAILED.value: frozenset({ProjectStatus.REMUXING.value}),
    ProjectStatus.FAILED.value: frozenset({ProjectStatus.UPLOADED.value}),
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, frozenset())


def is_project_busy(status: str) -> bool:
    return status in ACTIVE_STATUSES


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
