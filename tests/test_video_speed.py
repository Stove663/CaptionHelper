from __future__ import annotations

from caption_helper.remux.ripple import RippleTimeline, TimelineCue, compute_ripple_timeline
from caption_helper.remux.video_speed import (
    MIN_SPEED_FACTOR,
    build_video_segment_specs,
    detect_slowdown_warnings,
)
from caption_helper.subtitles_json import Cue


class TestVideoSpeedSpecs:
    def _timeline(self) -> RippleTimeline:
        cues = [
            Cue(1, 0, 0, 1000, "a", "a1", modified=True),
            Cue(2, 0, 1000, 2000, "b", "b", modified=False),
        ]
        manifest = {
            "cues": [
                {"index": 1, "status": "success", "actual_duration_ms": 2000, "delta_ms": 1000},
            ]
        }
        return compute_ripple_timeline(cues, sync_mode="natural-pace", synthesis_manifest=manifest)

    def test_build_segment_specs_includes_head_and_cues(self) -> None:
        timeline = self._timeline()
        specs = build_video_segment_specs(timeline, video_duration_ms=2500)
        names = [s.name for s in specs]
        assert "cue_0001" in names
        assert "cue_0002" in names

    def test_detect_slowdown_below_threshold(self) -> None:
        timeline = RippleTimeline(
            sync_mode="natural-pace",
            cues=[
                TimelineCue(
                    index=1,
                    spk=0,
                    modified=True,
                    text_edited="x",
                    start_ms_orig=0,
                    end_ms_orig=1000,
                    start_ms_adj=0,
                    end_ms_adj=2000,
                    delta_ms=1000,
                    duration_adj_ms=2000,
                )
            ],
            duration_delta_ms=1000,
        )
        specs = build_video_segment_specs(timeline, video_duration_ms=1000)
        warnings = detect_slowdown_warnings(specs)
        assert any(str(MIN_SPEED_FACTOR) in w for w in warnings)
