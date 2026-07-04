## Why

After subtitle editing and TTS re-synthesis, users need a single playable output that reflects their corrections — not isolated segment files. The pipeline must assemble unmodified original segments and TTS-replaced segments into one continuous audio track, mux it with the source video and edited subtitles, and provide a Web UI preview to verify the result before export.

## What Changes

- **Audio timeline assembly**: Concatenate per-cue audio in timestamp order — `segments/` for unmodified cues, `tts_segments/` for modified cues — into `output_audio.wav`
- **Video remux**: Combine `source` video stream + `output_audio.wav` + `subtitles_edited.srt` into `output_video.mp4` (video copy, new audio, soft subtitle track)
- **Gap handling**: Fill silence between non-contiguous cue regions and before first / after last cue to match original video duration
- **Web UI preview page**: `/projects/{id}/preview` with video player showing remuxed output; trigger "Build output" action after TTS synthesis
- **API**: `POST /api/projects/{id}/remux`, `GET /api/projects/{id}/output-video`, remux job status polling
- **CLI**: `caption-helper remux <project-dir>` for headless rebuild

## Capabilities

### New Capabilities

- `audio-timeline-assembly`: Stitch original and TTS segments into a single timeline-aligned audio file
- `video-remux`: Mux source video, assembled audio, and edited subtitles into output video
- `output-preview`: Web UI page to preview and download the remuxed output video

### Modified Capabilities

_(none)_

## Impact

- **Dependencies**: ffmpeg (already required); no new Python ML deps
- **New code**: `src/caption_helper/remux/` (`assemble.py`, `mux.py`); web routes and preview page
- **New artifacts per project**: `output_audio.wav`, `output_video.mp4`, `remux_manifest.json`
- **Depends on**: `funasr-video-subtitles-audio-split` (segments), `add-subtitle-editor-ui` (subtitles_edited), `moss-tts-segment-synthesis` (tts_segments)
