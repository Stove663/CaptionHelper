## Context

CaptionHelper's project directory contains:
- `segments/` — original per-cue WAV clips from ASR
- `tts_segments/` — MOSS-TTS replacements for modified cues only
- `subtitles.json` — per-cue timestamps, `modified` flags
- `subtitles_edited.srt` — user-corrected subtitle text
- `source.mp4` — original uploaded video

The final deliverable is a new video where edited speech is heard at the correct timestamps with updated subtitles visible during playback.

## Goals / Non-Goals

**Goals:**

- Build `output_audio.wav` covering the full video duration
- Per cue: use `tts_segments/` if `modified`, else `segments/`
- Place each clip at its `[start_ms, end_ms]` position on the timeline
- Fill gaps with silence; preserve regions outside subtitle cues from original `audio.wav` if needed
- Remux: `ffmpeg` copy video stream, encode new audio (AAC), attach `subtitles_edited.srt` as mov_text subtitle track
- Web UI preview with play/pause, subtitle toggle, download link
- Background remux job with progress status

**Non-Goals:**

- Hard-burned (hardsub) subtitles as default (soft sub track for preview flexibility; hardsub optional flag later)
- Re-encoding video (stream copy `-c:v copy`)
- Audio crossfade between segments (v1: direct splice; crossfade deferred)
- Multi-track audio output

## Decisions

### 1. Timeline assembly strategy: ffmpeg adelay + amix overlay

**Choice:** Build a silent base track of full video duration, then overlay each cue clip at its start offset.

```bash
# Conceptual: for each cue, adelay + amix onto silence base
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t {video_duration} base.wav
# overlay cue clips at start_ms positions → output_audio.wav
```

**Implementation:** Use `pydub` or ffmpeg `filter_complex` with `adelay` and `amix` inputs.

**Simpler alternative for v1:** Generate an ffmpeg filter_complex dynamically:
- Input 0: silence base (duration = source video length)
- Inputs 1..N: cue WAV files
- `adelay={start_ms}|{start_ms}` per clip + `amix=inputs=N+1:duration=longest`

**Rationale:** Cues may not be contiguous; overlay preserves timing without re-cutting the full original audio.

### 2. Segment source selection

```python
def resolve_clip(cue):
    if cue.modified and tts_path.exists():
        return tts_segments / filename
    return segments / filename
```

**Precondition:** TTS synthesis must complete for all modified cues before remux; otherwise remux fails with list of missing TTS files.

### 3. Regions without subtitle cues

**Choice:** For timeline regions not covered by any cue, use audio from original `audio.wav` (the full extracted track).

**Rationale:** VAD may miss non-speech or inter-cue content; preserves background music and un-transcribed audio.

**Implementation:** Start with full `audio.wav` as base, overlay cue clips (TTS or original segment) at their timestamps — segment clips replace the corresponding time ranges.

### 4. Video remux with ffmpeg

```bash
ffmpeg -i source.mp4 -i output_audio.wav -i subtitles_edited.srt \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -c:v copy -c:a aac -b:a 192k -c:s mov_text \
  -shortest output_video.mp4
```

**Subtitle format:** Convert SRT to mov_text for MP4 compatibility, or use `-c:s srt` in MKV; default MP4 with mov_text.

**Duration:** `-shortest` trims to shortest stream; use video duration as master (pad audio if shorter).

### 5. Project output layout

```
<project>/
├── output_audio.wav
├── output_video.mp4
├── remux_manifest.json    # cue→clip mapping, durations, timestamps
└── ...
```

### 6. Remux job flow

```
User clicks "Build & Preview"
  → validate: subtitles_edited exists, all modified cues have tts_segments
  → assemble output_audio.wav
  → remux output_video.mp4
  → status: remux_ready
  → preview page enabled
```

**Status machine extension:** `synthesis_ready` → `remuxing` → `remux_ready` | `remux_failed`

### 7. Web UI preview page

**Route:** `/projects/{id}/preview`

**Components:**
- HTML5 `<video>` playing `GET /api/projects/{id}/output-video`
- Subtitle track toggle (browser native text track if mov_text exposed, or side-by-side SRT display)
- "Rebuild output" button
- Download links for `output_video.mp4` and `output_audio.wav`
- Comparison note: "Original" vs "Output" tab switch (optional v1: link back to source video)

### 8. API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/projects/{id}/remux` | Start assembly + remux job |
| GET | `/api/projects/{id}/remux-status` | Job progress |
| GET | `/api/projects/{id}/output-video` | Stream `output_video.mp4` |
| GET | `/api/projects/{id}/output-audio` | Stream `output_audio.wav` |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Click/pop at segment boundaries | v1 direct splice; optional micro-crossfade in v2 |
| TTS duration mismatch causes overlap | Segments pre-trimmed to slot; overlay replaces exact range |
| MP4 soft subs not visible in all players | Document VLC/browser support; offer download with external SRT |
| Long videos slow to remux | Stream copy video (fast); audio assembly is main cost |
| Missing TTS for modified cue | Block remux; show clear error listing missing indices |

## Migration Plan

1. Apply after `moss-tts-segment-synthesis` (or allow remux with zero modified cues — all original segments)
2. Projects with no modifications: remux uses all `segments/` clips, still produces output

## Open Questions

- Default container: MP4 or MKV? _MP4 with mov_text for broad browser preview support._
- Allow remux before TTS if no cues modified? _Yes — skip TTS requirement when `modified_segments` is empty._
