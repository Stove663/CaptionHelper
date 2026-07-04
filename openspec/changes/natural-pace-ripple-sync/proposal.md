## Why

The target content is **lecture/meeting speech** where users typically replace only one or two words per subtitle cue (e.g., swapping a Chinese term for English). The existing **fixed-slot** TTS mode compresses speech to fit immutable ASR timestamps, which degrades quality when the edited text is longer. Users need an alternative **natural-pace** mode: TTS at normal speed, subsequent cues ripple forward on the timeline, and the video is time-adjusted to stay in sync.

## What Changes

- Introduce two timeline sync modes per project: `fixed-slot` (default) and `natural-pace`
- **fixed-slot**: existing behavior — TTS forced into original `[start_ms, end_ms]` via tokens + trim/pad
- **natural-pace**: TTS at natural speech rate; record actual duration; ripple all subsequent cues forward; rebuild timeline
- **Compression warning**: when fixed-slot would over-compress (heuristic on text length vs slot duration), warn user and offer natural-pace
- **Ripple timeline**: recalculate `start_ms`/`end_ms` for cues after each extended modified segment; write `subtitles_ripple.srt` and update assembly positions
- **Video speed sync**: per inter-cue video segment, apply ffmpeg `setpts` speed adjustment so video duration matches new audio timeline
- **Lecture/meeting default**: remux assembly uses `audio.wav` as base track (speech regions replaced, gaps preserved)
- User selects sync mode in Web UI before synthesis/remux; no glossary/terminology table

## Capabilities

### New Capabilities

- `timeline-sync-modes`: Fixed-slot vs natural-pace mode selection, compression detection, and user-facing warnings
- `ripple-timeline`: Recalculate cue timestamps when natural-pace TTS extends segment duration
- `video-speed-sync`: Adjust video playback speed per segment to match rippled audio timeline

### Modified Capabilities

- `moss-tts-synthesis`: Add natural-pace synthesis path without forced duration compression
- `audio-timeline-assembly`: Support ripple-adjusted timestamps; lecture/meeting base-track strategy
- `video-remux`: Mux speed-adjusted video with rippled audio and updated subtitles
- `output-preview`: Mode selector, compression warning UI, ripple timeline preview

## Impact

- **New artifacts**: `timeline.json` (original vs adjusted timestamps per cue), `subtitles_ripple.srt`, `video_segments/`
- **Video processing**: Per-segment ffmpeg `setpts`/`atempo` — more CPU time than stream-copy remux
- **Subtitle timestamps**: In natural-pace mode, `subtitles_ripple.srt` replaces `subtitles_edited.srt` for output; original timestamps preserved in `subtitles.json`
- **Depends on**: `moss-tts-segment-synthesis`, `remux-output-preview`, `add-subtitle-editor-ui`
