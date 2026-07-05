from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecyclePolicy:
    retention_days: int = 7
    cleanup_interval_seconds: int = 3600
    startup_delay_seconds: int = 5
    deletion_mode: str = "hard"
