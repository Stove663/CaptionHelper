from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RemuxCueRecord:
    index: int
    modified: bool
    source: str
    clip_path: str
    start_ms: int
    end_ms: int


@dataclass
class RemuxManifest:
    output_audio: str
    output_video: str
    cues: list[RemuxCueRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_audio": self.output_audio,
            "output_video": self.output_video,
            "cues": [asdict(c) for c in self.cues],
        }


def write_remux_manifest(project_dir: Path, manifest: RemuxManifest) -> Path:
    path = Path(project_dir) / "remux_manifest.json"
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_remux_manifest(project_dir: Path) -> dict[str, Any] | None:
    path = Path(project_dir) / "remux_manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
