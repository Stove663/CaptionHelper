from __future__ import annotations

import json
import logging
from pathlib import Path

from caption_helper.remux.assemble import assemble_timeline
from caption_helper.remux.manifest import RemuxManifest
from caption_helper.remux.mux import get_media_duration_s, remux_video
from caption_helper.remux.ripple import apply_ripple_artifacts, load_timeline
from caption_helper.tts.compression_risk import SYNC_MODE_NATURAL, SYNC_MODE_FIXED
from caption_helper.tts.compression_risk import VALID_SYNC_MODES

logger = logging.getLogger(__name__)


def find_source_video(project_dir: Path) -> Path:
    project_dir = Path(project_dir)
    matches = list(project_dir.glob("source.*"))
    if not matches:
        raise FileNotFoundError(f"No source video in {project_dir}")
    return matches[0]


def _read_sync_mode(project_dir: Path) -> str:
    meta_path = project_dir / "meta.json"
    if meta_path.is_file():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        mode = data.get("sync_mode", SYNC_MODE_FIXED)
        if mode in VALID_SYNC_MODES:
            return mode
    manifest_path = project_dir / "synthesis_manifest.json"
    if manifest_path.is_file():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        mode = data.get("sync_mode", SYNC_MODE_FIXED)
        if mode in VALID_SYNC_MODES:
            return mode
    return SYNC_MODE_FIXED


def remux_pipeline(
    project_dir: Path,
    *,
    source_video: Path | None = None,
    sync_mode: str | None = None,
) -> RemuxManifest:
    """Assemble output audio and remux final video."""
    from caption_helper.remux.video_speed import build_speed_adjusted_video

    project_dir = Path(project_dir)
    mode = sync_mode or _read_sync_mode(project_dir)
    video = source_video or find_source_video(project_dir)

    timeline = None
    if mode == SYNC_MODE_NATURAL:
        timeline = load_timeline(project_dir)
        if timeline is None:
            timeline = apply_ripple_artifacts(project_dir, sync_mode=mode)
        subtitles = project_dir / "subtitles_ripple.srt"
    else:
        subtitles = project_dir / "subtitles_edited.srt"

    if not subtitles.is_file():
        subtitles = project_dir / "subtitles_original.srt"
    if not subtitles.is_file():
        raise FileNotFoundError("No subtitles found for remux")

    logger.info("Assembling output audio (mode=%s)", mode)
    manifest = assemble_timeline(project_dir, sync_mode=mode, timeline=timeline)

    output_video = project_dir / manifest.output_video
    output_audio_path = project_dir / manifest.output_audio

    if mode == SYNC_MODE_NATURAL and timeline is not None:
        logger.info("Building speed-adjusted video track")
        adjusted = project_dir / ".speed_adjusted_video.mp4"
        build_speed_adjusted_video(video, timeline, adjusted)
        remux_video(
            adjusted,
            output_audio_path,
            subtitles,
            output_video,
            video_copy=False,
        )
        adjusted.unlink(missing_ok=True)
    else:
        logger.info("Remuxing output video (stream copy)")
        remux_video(
            video,
            output_audio_path,
            subtitles,
            output_video,
            video_copy=True,
        )

    video_dur = get_media_duration_s(output_video)
    audio_dur = get_media_duration_s(output_audio_path)
    if abs(video_dur - audio_dur) > 0.15:
        logger.warning(
            "Output A/V duration mismatch: video=%.3fs audio=%.3fs",
            video_dur,
            audio_dur,
        )

    return manifest


def remux_warnings(project_dir: Path, *, sync_mode: str | None = None) -> list[str]:
    from caption_helper.remux.video_speed import build_video_segment_specs, detect_slowdown_warnings

    project_dir = Path(project_dir)
    mode = sync_mode or _read_sync_mode(project_dir)
    if mode != SYNC_MODE_NATURAL:
        return []

    timeline = load_timeline(project_dir)
    if timeline is None:
        timeline = apply_ripple_artifacts(project_dir, sync_mode=mode)

    video = find_source_video(project_dir)
    video_duration_ms = int(get_media_duration_s(video) * 1000)
    specs = build_video_segment_specs(timeline, video_duration_ms)
    return detect_slowdown_warnings(specs)
