from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


MANIFEST_SCHEMA_VERSION = 1


@dataclass
class ManifestBase:
    schema_version: int = MANIFEST_SCHEMA_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
        }


@dataclass
class StageArtifactManifest(ManifestBase):
    stage: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update({
            "stage": self.stage,
            "inputs": self.inputs,
            "outputs": self.outputs,
        })
        if self.notes is not None:
            data["notes"] = self.notes
        return data
