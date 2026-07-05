from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from caption_helper.models import Sentence
from caption_helper.srt import write_srt
from caption_helper.subtitles_json import Cue, load_subtitles
from caption_helper.tts.compression_risk import SYNC_MODE_NATURAL
from caption_helper.tts.synthesizer import load_synthesis_manifest


@dataclass
class TimelineCue:
    index: int
    spk: int
    modified: bool
    text_edited: str
    start_ms_orig: int
    end_ms_orig: int
    start_ms_adj: int
    end_ms_adj: int
    delta_ms: int = 0
    duration_adj_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RippleTimeline:
    sync_mode: str
    cues: list[TimelineCue]
    duration_delta_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_mode": self.sync_mode,
            "duration_delta_ms": self.duration_delta_ms,
            "cues": [c.to_dict() for c in self.cues],
        }


def _delta_by_index(manifest: dict[str, Any] | None) -> dict[int, int]:
    if not manifest:
        return {}
    out: dict[int, int] = {}
    for entry in manifest.get("cues", []):
        if entry.get("status") != "success":
            continue
        index = int(entry["index"])
        delta = int(entry.get("delta_ms", 0))
        out[index] = delta
    return out


def _actual_duration_by_index(manifest: dict[str, Any] | None) -> dict[int, int]:
    if not manifest:
        return {}
    out: dict[int, int] = {}
    for entry in manifest.get("cues", []):
        if entry.get("status") != "success":
            continue
        index = int(entry["index"])
        actual = entry.get("actual_duration_ms")
        if actual is not None:
            out[index] = int(actual)
    return out


def compute_ripple_timeline(
    cues: list[Cue],
    *,
    sync_mode: str,
    synthesis_manifest: dict[str, Any] | None = None,
) -> RippleTimeline:
    """Compute adjusted cue timestamps for natural-pace ripple."""
    deltas = _delta_by_index(synthesis_manifest)
    actual_durations = _actual_duration_by_index(synthesis_manifest)
    cumulative_shift = 0
    timeline_cues: list[TimelineCue] = []

    for cue in sorted(cues, key=lambda c: c.index):
        start_adj = cue.start_ms + cumulative_shift
        slot_ms = cue.end_ms - cue.start_ms

        if sync_mode == SYNC_MODE_NATURAL and cue.modified and cue.index in actual_durations:
            duration_adj = actual_durations[cue.index]
            delta = deltas.get(cue.index, duration_adj - slot_ms)
            cumulative_shift += delta
        else:
            duration_adj = slot_ms
            delta = 0

        end_adj = start_adj + duration_adj
        timeline_cues.append(
            TimelineCue(
                index=cue.index,
                spk=cue.spk,
                modified=cue.modified,
                text_edited=cue.text_edited,
                start_ms_orig=cue.start_ms,
                end_ms_orig=cue.end_ms,
                start_ms_adj=start_adj,
                end_ms_adj=end_adj,
                delta_ms=delta,
                duration_adj_ms=duration_adj,
            )
        )

    duration_delta = 0
    if timeline_cues:
        last = timeline_cues[-1]
        duration_delta = last.end_ms_adj - last.end_ms_orig

    return RippleTimeline(
        sync_mode=sync_mode,
        cues=timeline_cues,
        duration_delta_ms=duration_delta,
    )


def build_ripple_timeline(project_dir: Path, *, sync_mode: str) -> RippleTimeline:
    project_dir = Path(project_dir)
    cues = load_subtitles(project_dir / "subtitles.json")
    manifest = load_synthesis_manifest(project_dir)
    return compute_ripple_timeline(cues, sync_mode=sync_mode, synthesis_manifest=manifest)


def write_timeline(project_dir: Path, timeline: RippleTimeline) -> Path:
    path = Path(project_dir) / "timeline.json"
    path.write_text(json.dumps(timeline.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_timeline(project_dir: Path) -> RippleTimeline | None:
    path = Path(project_dir) / "timeline.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cues = [TimelineCue(**item) for item in data.get("cues", [])]
    return RippleTimeline(
        sync_mode=data.get("sync_mode", "fixed-slot"),
        cues=cues,
        duration_delta_ms=int(data.get("duration_delta_ms", 0)),
    )


def write_ripple_srt(project_dir: Path, timeline: RippleTimeline) -> Path:
    sentences = [
        Sentence(
            text=cue.text_edited,
            spk=cue.spk,
            start=cue.start_ms_adj,
            end=cue.end_ms_adj,
        )
        for cue in timeline.cues
    ]
    path = Path(project_dir) / "subtitles_ripple.srt"
    write_srt(sentences, path)
    return path


def apply_ripple_artifacts(project_dir: Path, *, sync_mode: str) -> RippleTimeline:
    timeline = build_ripple_timeline(project_dir, sync_mode=sync_mode)
    write_timeline(project_dir, timeline)
    if sync_mode == SYNC_MODE_NATURAL:
        write_ripple_srt(project_dir, timeline)
    return timeline
