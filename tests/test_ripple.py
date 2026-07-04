from __future__ import annotations

from caption_helper.remux.ripple import compute_ripple_timeline, write_ripple_srt
from caption_helper.subtitles_json import Cue


def _manifest(cue_data: list[dict]) -> dict:
    return {"sync_mode": "natural-pace", "cues": cue_data}


class TestRippleTimeline:
    def test_single_extension_ripples_later_cues(self) -> None:
        cues = [
            Cue(1, 0, 0, 1000, "a", "a1", modified=True),
            Cue(2, 0, 1000, 2000, "b", "b", modified=False),
            Cue(3, 0, 2000, 3000, "c", "c", modified=False),
        ]
        manifest = _manifest(
            [
                {
                    "index": 1,
                    "status": "success",
                    "actual_duration_ms": 1500,
                    "delta_ms": 500,
                    "slot_duration_ms": 1000,
                }
            ]
        )
        timeline = compute_ripple_timeline(cues, sync_mode="natural-pace", synthesis_manifest=manifest)
        assert timeline.cues[0].start_ms_adj == 0
        assert timeline.cues[0].end_ms_adj == 1500
        assert timeline.cues[1].start_ms_adj == 1500
        assert timeline.cues[1].end_ms_adj == 2500
        assert timeline.cues[2].start_ms_adj == 2500
        assert timeline.duration_delta_ms == 500

    def test_cumulative_multi_cue_ripple(self) -> None:
        cues = [
            Cue(1, 0, 0, 1000, "a", "a1", modified=True),
            Cue(2, 0, 1000, 2000, "b", "b2", modified=True),
            Cue(3, 0, 2000, 3000, "c", "c3", modified=True),
        ]
        manifest = _manifest(
            [
                {"index": 1, "status": "success", "actual_duration_ms": 1200, "delta_ms": 200},
                {"index": 2, "status": "success", "actual_duration_ms": 1300, "delta_ms": 300},
                {"index": 3, "status": "success", "actual_duration_ms": 1400, "delta_ms": 400},
            ]
        )
        timeline = compute_ripple_timeline(cues, sync_mode="natural-pace", synthesis_manifest=manifest)
        assert timeline.cues[0].end_ms_adj == 1200
        assert timeline.cues[1].start_ms_adj == 1200
        assert timeline.cues[1].end_ms_adj == 2500
        assert timeline.cues[2].start_ms_adj == 2500
        assert timeline.cues[2].end_ms_adj == 3900
        assert timeline.duration_delta_ms == 900

    def test_fixed_slot_no_ripple(self) -> None:
        cues = [Cue(1, 0, 0, 1000, "a", "a1", modified=True)]
        manifest = _manifest(
            [{"index": 1, "status": "success", "actual_duration_ms": 1500, "delta_ms": 500}]
        )
        timeline = compute_ripple_timeline(cues, sync_mode="fixed-slot", synthesis_manifest=manifest)
        assert timeline.cues[0].start_ms_adj == 0
        assert timeline.cues[0].end_ms_adj == 1000
        assert timeline.duration_delta_ms == 0

    def test_ripple_srt_matches_adjusted_timestamps(self, tmp_path) -> None:
        cues = [
            Cue(1, 0, 0, 1000, "hello", "hi there", modified=True),
            Cue(2, 0, 1000, 2000, "world", "world", modified=False),
        ]
        manifest = _manifest(
            [{"index": 1, "status": "success", "actual_duration_ms": 1500, "delta_ms": 500}]
        )
        timeline = compute_ripple_timeline(cues, sync_mode="natural-pace", synthesis_manifest=manifest)
        srt_path = write_ripple_srt(tmp_path, timeline)
        content = srt_path.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:01,500" in content
        assert "00:00:01,500 --> 00:00:02,500" in content
