## 1. Timeline sync mode infrastructure

- [x] 1.1 Add `sync_mode` field to `meta.json` (`fixed-slot` | `natural-pace`, default `fixed-slot`)
- [x] 1.2 Implement `compression_risk.py`: estimate speech duration from `text_edited`, compute ratio vs slot, flag cues > 1.3
- [x] 1.3 Add zh-en mixed character counting (CJK vs Latin per-char heuristics)
- [x] 1.4 Unit tests for compression detection with pure Chinese, pure English, and mixed cues

## 2. Natural-pace TTS synthesis

- [x] 2.1 Update `tts/moss_tts.py`: branch on `sync_mode` — with/without `tokens` parameter
- [x] 2.2 Record `actual_duration_ms`, `slot_duration_ms`, `delta_ms` in `synthesis_manifest.json`
- [x] 2.3 Skip ffmpeg trim/pad in natural-pace mode
- [x] 2.4 Add unit tests for both synthesis paths

## 3. Ripple timeline engine

- [x] 3.1 Implement `remux/ripple.py`: `compute_ripple_timeline(cues, synthesis_manifest)` → adjusted timestamps
- [x] 3.2 Write `timeline.json` with orig/adj timestamps and deltas per cue
- [x] 3.3 Generate `subtitles_ripple.srt` from adjusted timestamps + `text_edited`
- [x] 3.4 Report total duration change (`final_end_adj - final_end_orig`)
- [x] 3.5 Unit tests: single extension, cumulative multi-cue ripple, unmodified cue shifting

## 4. Video speed sync

- [x] 4.1 Implement `remux/video_speed.py`: split source video at original cue boundaries
- [x] 4.2 Apply ffmpeg `setpts` per segment: `speed_factor = orig_duration / new_duration`
- [x] 4.3 Write adjusted clips to `video_segments/`, concatenate to temp video track
- [x] 4.4 Detect segments requiring slow-down below 0.75x; return warnings
- [x] 4.5 Skip video speed adjust entirely in `fixed-slot` mode

## 5. Audio assembly and remux integration

- [x] 5.1 Update `assemble_timeline()`: use `start_ms_adj` in natural-pace, `start_ms_orig` in fixed-slot
- [x] 5.2 Confirm `audio.wav` base track strategy for both modes
- [x] 5.3 Update `remux_video()`: fixed-slot uses `-c:v copy`; natural-pace uses speed-adjusted video
- [x] 5.4 Mux with `subtitles_edited.srt` (fixed) or `subtitles_ripple.srt` (natural-pace)
- [x] 5.5 Verify audio-video duration match within ±100 ms

## 6. Web UI

- [x] 6.1 Add sync mode toggle (fixed-slot / natural-pace) on editor page
- [x] 6.2 Show compression risk banner on modified cues with mode switch CTA
- [x] 6.3 After natural-pace synthesis: show ripple duration delta preview
- [x] 6.4 Show slow-down warning dialog before natural-pace remux if needed
- [x] 6.5 Display active sync mode on preview page

## 7. Verification

- [x] 7.1 Fixed-slot: 1-2 word swap that fits slot — no warning, no ripple, video copy
- [x] 7.2 Natural-pace: Chinese→longer English swap — TTS natural rate, cues ripple, video slows
- [x] 7.3 Verify `subtitles_ripple.srt` timestamps match adjusted audio positions
- [x] 7.4 Verify cumulative ripple across 3+ modified cues
- [x] 7.5 Document sync modes and lecture/meeting workflow in README
