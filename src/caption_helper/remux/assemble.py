from __future__ import annotations

import json
from pathlib import Path

from caption_helper.remux.manifest import RemuxCueRecord, RemuxManifest, write_remux_manifest
from caption_helper.remux.ripple import RippleTimeline, load_timeline
from caption_helper.split import segment_filename
from caption_helper.subtitles_json import Cue, load_subtitles
from caption_helper.tts.compression_risk import SYNC_MODE_NATURAL


class MissingTTSClipsError(RuntimeError):
    def __init__(self, missing: list[int]) -> None:
        self.missing = missing
        super().__init__(f"Missing TTS clips for modified cues: {missing}")


def resolve_clip(cue: Cue, project_dir: Path) -> tuple[Path, str]:
    """Return clip path and source label (`tts` or `original`)."""
    project_dir = Path(project_dir)
    name = segment_filename(cue.index, cue.to_sentence())
    segment_path = project_dir / "segments" / name
    tts_path = project_dir / "tts_segments" / name
    if cue.modified and tts_path.is_file():
        return tts_path, "tts"
    return segment_path, "original"


def validate_clips(cues: list[Cue], project_dir: Path) -> None:
    """Fail if any modified cue lacks a TTS file."""
    missing: list[int] = []
    for cue in cues:
        if not cue.modified:
            continue
        tts_path = project_dir / "tts_segments" / segment_filename(cue.index, cue.to_sentence())
        if not tts_path.is_file():
            missing.append(cue.index)
    if missing:
        raise MissingTTSClipsError(missing)


def _to_mono(data):
    import numpy as np

    if data.ndim == 1:
        return data.astype(np.float32)
    return data.mean(axis=1).astype(np.float32)


def _fit_clip_to_slot(clip, slot_samples: int):
    import numpy as np

    if slot_samples <= 0:
        return np.zeros(0, dtype=np.float32)
    if len(clip) == slot_samples:
        return clip
    if len(clip) > slot_samples:
        return clip[:slot_samples]
    out = np.zeros(slot_samples, dtype=np.float32)
    out[: len(clip)] = clip
    return out


def _resample_linear(clip, src_sr: int, dst_sr: int):
    import numpy as np

    if src_sr == dst_sr or len(clip) == 0:
        return clip
    duration = len(clip) / src_sr
    dst_len = max(1, int(duration * dst_sr))
    src_x = np.linspace(0.0, 1.0, num=len(clip), endpoint=False)
    dst_x = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
    return np.interp(dst_x, src_x, clip).astype(np.float32)


def _timeline_map(timeline: RippleTimeline | None) -> dict[int, object]:
    if timeline is None:
        return {}
    return {c.index: c for c in timeline.cues}


def assemble_timeline(
    project_dir: Path,
    *,
    sync_mode: str = "fixed-slot",
    timeline: RippleTimeline | None = None,
) -> RemuxManifest:
    """Build output_audio.wav by replacing cue ranges on the full extracted track."""
    import numpy as np
    import soundfile as sf

    project_dir = Path(project_dir)
    audio_path = project_dir / "audio.wav"
    if not audio_path.is_file():
        raise FileNotFoundError(f"Base audio not found: {audio_path}")

    natural_pace = sync_mode == SYNC_MODE_NATURAL
    if natural_pace and timeline is None:
        timeline = load_timeline(project_dir)
    timeline_by_index = _timeline_map(timeline)

    cues = load_subtitles(project_dir / "subtitles.json")
    modified = [c for c in cues if c.modified]
    if modified:
        validate_clips(cues, project_dir)

    base, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
    base = _to_mono(base)

    records: list[RemuxCueRecord] = []
    for cue in cues:
        clip_path, source = resolve_clip(cue, project_dir)
        if not clip_path.is_file():
            raise FileNotFoundError(f"Clip not found for cue {cue.index}: {clip_path}")

        clip, clip_sr = sf.read(str(clip_path), dtype="float32", always_2d=True)
        clip = _to_mono(clip)
        if clip_sr != sr:
            clip = _resample_linear(clip, clip_sr, sr)

        tl = timeline_by_index.get(cue.index)
        start_ms = tl.start_ms_adj if tl else cue.start_ms
        end_ms = tl.end_ms_adj if tl else cue.end_ms

        start = int(start_ms / 1000.0 * sr)
        if natural_pace:
            end = start + len(clip)
            if end > len(base):
                base = np.pad(base, (0, end - len(base)))
            base[start:end] = clip
        else:
            end = int(end_ms / 1000.0 * sr)
            slot_len = max(0, end - start)
            base[start:end] = _fit_clip_to_slot(clip, slot_len)

        records.append(
            RemuxCueRecord(
                index=cue.index,
                modified=cue.modified,
                source=source,
                clip_path=str(clip_path.relative_to(project_dir)),
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )

    if natural_pace and timeline and timeline.cues:
        target_len = int(timeline.cues[-1].end_ms_adj / 1000.0 * sr)
        if len(base) < target_len:
            base = np.pad(base, (0, target_len - len(base)))

    output_audio = project_dir / "output_audio.wav"
    sf.write(str(output_audio), base, sr)

    manifest = RemuxManifest(
        output_audio=str(output_audio.relative_to(project_dir)),
        output_video="output_video.mp4",
        cues=records,
    )
    write_remux_manifest(project_dir, manifest)
    return manifest


def load_modified_segments(project_dir: Path) -> list[dict]:
    path = Path(project_dir) / "modified_segments.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
