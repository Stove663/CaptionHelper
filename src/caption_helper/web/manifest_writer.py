from __future__ import annotations

import json
from pathlib import Path

from caption_helper.web.manifests import StageArtifactManifest


def write_stage_manifest(path: Path, manifest: StageArtifactManifest) -> None:
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
