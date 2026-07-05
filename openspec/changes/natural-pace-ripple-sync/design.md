## Context

CaptionHelper targets **lecture and meeting speech** videos. Users edit subtitle text at sentence granularity, usually replacing one or two words (often Chinese → English). The current pipeline locks ASR timestamps and compresses TTS into the original time slot — acceptable for minor edits but harsh when English replacements are longer.

The user wants a second path: synthesize at **natural pace**, let the timeline **ripple** (shift later cues), and **speed-adjust the video** to match the new audio durations.

Typical edit pattern:

```
原句: "今天我们学习 Docker 的基本概念"     (3.2s 槽)
改后: "今天我们学习 Docker container 的基本概念"  (1-2 词替换，但英文更长)
```

## Goals / Non-Goals

**Goals:**

- Two modes: `fixed-slot` (default) and `natural-pace` (user opt-in)
- Detect when fixed-slot compression would be excessive; warn and suggest natural-pace
- Natural-pace: TTS without `tokens` forcing; store `actual_duration_ms`
- Ripple: cumulative shift of all cues after an extended segment
- Video: per-segment speed adjustment (`setpts`) so picture duration matches new audio segment duration
- Lecture/meeting remux: `audio.wav` as base, overlay speech clips at (possibly rippled) positions
- Output subtitles reflect rippled timestamps in natural-pace mode
- Web UI: mode toggle, compression warnings, before/after duration preview

**Non-Goals:**

- Word-level acoustic replacement (still sentence-level TTS)
- Terminology glossary / bulk find-replace
- Lip-sync correction
- BGM-heavy content optimization (lecture/meeting assumed speech-dominant)
- Real-time preview during ripple recalculation

## Decisions

### 1. Two timeline sync modes

| Mode | TTS duration | Timestamps | Video |
|------|-------------|------------|-------|
| `fixed-slot` | Forced to `end_ms - start_ms` | Immutable (original ASR) | Stream copy (`-c:v copy`) |
| `natural-pace` | Natural speech rate | Rippled forward from first extension | Per-segment speed adjust |

**Default:** `fixed-slot` — no change for minor 1-2 word swaps that still fit.

**User selects** `natural-pace` per project or per synthesis run when warned.

### 2. Compression detection heuristic

**Choice:** Flag a modified cue as `compression_risk: true` when:

```
estimated_speech_ms = len(text_edited) * MS_PER_CHAR  # default 120ms/char Chinese, 80ms/char Latin
slot_ms = end_ms - start_ms
compression_ratio = estimated_speech_ms / slot_ms
```

If `compression_ratio > 1.3` (30% over slot), show warning before synthesis.

For mixed zh-en: count CJK chars at 120 ms, Latin chars at 60 ms per char.

**Rationale:** Lecture edits are usually 1-2 words; a ratio > 1.3 means forced compression will sound rushed. User can proceed with fixed-slot or switch to natural-pace.

### 3. Natural-pace TTS synthesis

**Choice:** Call MOSS-TTS without `tokens` parameter; measure output WAV duration.

```python
processor.build_user_message(text=text_edited, reference=[seg_wav])  # no tokens
actual_duration_ms = measure_wav_duration(output)
```

Store in `synthesis_manifest.json`: `mode: natural-pace`, `actual_duration_ms`, `slot_duration_ms`, `delta_ms = actual - slot`.

**No trim/pad** in natural-pace mode.

### 4. Ripple timeline algorithm

**Input:** cues sorted by `index`, each with `start_ms_orig`, `end_ms_orig`, optional `delta_ms` for modified natural-pace cues.

```
cumulative_shift = 0
for cue in cues:
    cue.start_ms_adj = cue.start_ms_orig + cumulative_shift
    if cue.modified and mode == natural-pace:
        cue.duration_adj = actual_duration_ms  # from TTS
        cumulative_shift += delta_ms
    else:
        cue.duration_adj = cue.end_ms_orig - cue.start_ms_orig
    cue.end_ms_adj = cue.start_ms_adj + cue.duration_adj
```

**Unmodified cues** between modified ones also shift forward (ripple), preserving their original audio content but at new positions.

**Output:** `timeline.json` with `start_ms_orig`, `end_ms_orig`, `start_ms_adj`, `end_ms_adj`, `delta_ms` per cue; `subtitles_ripple.srt` generated from adjusted timestamps + `text_edited`.

### 5. Video speed sync (natural-pace only)

Split the video into segments aligned to original cue boundaries. For each segment `i`:

```
orig_duration = end_ms_orig[i] - start_ms_orig[i]   (or gap segment duration)
new_duration  = end_ms_adj[i] - start_ms_adj[i]
speed_factor  = orig_duration / new_duration
```

Apply ffmpeg per video segment:

```bash
ffmpeg -ss {orig_start} -to {orig_end} -i source.mp4 \
  -filter:v "setpts=PTS/{speed_factor}" -an segment_i.mp4
```

- `speed_factor < 1` → video slows down (TTS took longer)
- `speed_factor > 1` → video speeds up (TTS was shorter; rare in natural-pace)

Concatenate video segments + rippled audio → `output_video.mp4`.

**Gap segments** (between cues, no speech): speed-adjust to match gap duration change from ripple.

### 6. Audio assembly per mode

**fixed-slot** (unchanged): overlay clips at original timestamps on `audio.wav` base.

**natural-pace:**
1. Start with `audio.wav` full track
2. Place each cue clip (TTS or original segment) at `start_ms_adj`
3. For extended modified cues, the TTS clip is longer — overwrites a wider window
4. Total `output_audio.wav` duration = `end_ms_adj[last_cue]` + tail padding (may exceed original video length)
5. Video tail: hold last frame or speed-adjust final gap

### 7. Lecture/meeting base track (both modes)

**Choice:** Always use `audio.wav` as assembly base (resolves ambiguity in `remux-output-preview` design).

**Rationale:** Lecture/meeting content is speech-dominant; gaps between cues retain room tone and breaths from original recording.

### 8. Web UI flow

```
Editor → Save edits
  → System scans modified cues for compression_risk
  → If any flagged: show banner "N cues may sound rushed in fixed-slot mode"
      [Use fixed-slot anyway]  [Switch to natural-pace]
  → Synthesize TTS
  → If natural-pace: compute ripple timeline, show duration delta preview
  → Remux (with or without video speed adjust)
  → Preview
```

**Per-project setting:** `meta.json` → `sync_mode: "fixed-slot" | "natural-pace"`

### 9. Project artifacts extension

```
<project>/
├── timeline.json           # orig vs adj timestamps, deltas
├── subtitles_ripple.srt    # natural-pace output subs (adj timestamps)
├── video_segments/         # speed-adjusted video clips (natural-pace)
└── ...
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Video slow-motion looks unnatural if delta is large | Warn when cumulative shift > 5s; show preview before remux |
| Many modified cues compound ripple | Show total duration change; user confirms |
| setpts quality on fast motion | Limit max slow-down factor (e.g., min speed 0.7x); warn beyond |
| Subtitle editor still shows original timestamps | Add "adjusted timeline" view in preview after ripple |
| fixed-slot and natural-pace cues mixed in one project | v1: mode is project-wide, not per-cue |

## Migration Plan

1. Apply after `moss-tts-segment-synthesis` and `remux-output-preview`
2. `fixed-slot` remains default — existing change behavior unchanged
3. `natural-pace` is opt-in additive path

## Open Questions

- Max allowed slow-down factor? _Default min 0.75x (25% slower); warn below._
- Per-cue mode in v2? _v1 project-wide only._
