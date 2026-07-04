from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from caption_helper.extract import check_ffmpeg
from caption_helper.remux.mux import get_media_duration_s
from caption_helper.remux.ripple import RippleTimeline, TimelineCue

MIN_SPEED_FACTOR = 0.75


@dataclass
class VideoSegmentSpec:
    name: str
    orig_start_ms: int
    orig_end_ms: int
    new_duration_ms: int

    @property
    def orig_duration_ms(self) -> int:
        return max(0, self.orig_end_ms - self.orig_start_ms)

    @property
    def speed_factor(self) -> float:
        if self.new_duration_ms <= 0:
            return 1.0
        return self.orig_duration_ms / self.new_duration_ms


@dataclass
class SpeedAdjustResult:
    video_path: Path
    warnings: list[str]


def build_video_segment_specs(
    timeline: RippleTimeline,
    video_duration_ms: int,
) -> list[VideoSegmentSpec]:
    cues = timeline.cues
    if not cues:
        return []

    specs: list[VideoSegmentSpec] = []

    if cues[0].start_ms_orig > 0:
        specs.append(
            VideoSegmentSpec(
                "head",
                0,
                cues[0].start_ms_orig,
                cues[0].start_ms_adj,
            )
        )

    for idx, cue in enumerate(cues):
        specs.append(
            VideoSegmentSpec(
                f"cue_{cue.index:04d}",
                cue.start_ms_orig,
                cue.end_ms_orig,
                cue.duration_adj_ms,
            )
        )
        if idx + 1 < len(cues):
            next_cue = cues[idx + 1]
            gap_orig = next_cue.start_ms_orig - cue.end_ms_orig
            gap_adj = next_cue.start_ms_adj - cue.end_ms_adj
            if gap_orig > 0:
                specs.append(
                    VideoSegmentSpec(
                        f"gap_{cue.index:04d}",
                        cue.end_ms_orig,
                        next_cue.start_ms_orig,
                        gap_adj,
                    )
                )

    last = cues[-1]
    if video_duration_ms > last.end_ms_orig:
        orig_tail = video_duration_ms - last.end_ms_orig
        specs.append(
            VideoSegmentSpec(
                "tail",
                last.end_ms_orig,
                video_duration_ms,
                orig_tail + timeline.duration_delta_ms,
            )
        )

    return [s for s in specs if s.orig_duration_ms > 0 and s.new_duration_ms > 0]


def detect_slowdown_warnings(specs: list[VideoSegmentSpec]) -> list[str]:
    warnings: list[str] = []
    for spec in specs:
        if spec.speed_factor < MIN_SPEED_FACTOR:
            pct = int((1 - spec.speed_factor) * 100)
            warnings.append(
                f"Segment {spec.name} requires {pct}% slow-down "
                f"(factor {spec.speed_factor:.2f}, min {MIN_SPEED_FACTOR})"
            )
    return warnings


def _extract_and_speed_segment(
    source_video: Path,
    spec: VideoSegmentSpec,
    output_path: Path,
) -> None:
    ffmpeg = check_ffmpeg()
    start_s = spec.orig_start_ms / 1000.0
    end_s = spec.orig_end_ms / 1000.0
    factor = spec.speed_factor
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        f"{start_s:.3f}",
        "-to",
        f"{end_s:.3f}",
        "-i",
        str(source_video),
        "-an",
        "-filter:v",
        f"setpts=PTS/{factor:.6f}",
        "-t",
        f"{spec.new_duration_ms / 1000.0:.3f}",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on segment {spec.name}:\n{result.stderr}")


def _concat_video_segments(segment_paths: list[Path], output_path: Path) -> None:
    ffmpeg = check_ffmpeg()
    list_file = output_path.parent / ".concat_list.txt"
    lines = [f"file '{p.resolve()}'" for p in segment_paths]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr}")


def build_speed_adjusted_video(
    source_video: Path,
    timeline: RippleTimeline,
    output_path: Path,
    *,
    segments_dir: Path | None = None,
) -> SpeedAdjustResult:
    source_video = Path(source_video)
    output_path = Path(output_path)
    segments_dir = Path(segments_dir or output_path.parent / "video_segments")
    segments_dir.mkdir(parents=True, exist_ok=True)

    video_duration_ms = int(get_media_duration_s(source_video) * 1000)
    specs = build_video_segment_specs(timeline, video_duration_ms)
    warnings = detect_slowdown_warnings(specs)

    segment_paths: list[Path] = []
    for spec in specs:
        seg_path = segments_dir / f"{spec.name}.mp4"
        _extract_and_speed_segment(source_video, spec, seg_path)
        segment_paths.append(seg_path)

    _concat_video_segments(segment_paths, output_path)
    return SpeedAdjustResult(video_path=output_path, warnings=warnings)
