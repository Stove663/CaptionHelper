## 1. Audio assembly module

- [x] 1.1 Create `src/caption_helper/remux/` package (`assemble.py`, `mux.py`, `manifest.py`)
- [x] 1.2 Implement `resolve_clip(cue)` — select `tts_segments/` or `segments/` based on `modified` flag
- [x] 1.3 Implement `validate_clips(cues)` — fail fast if modified cues lack TTS files
- [x] 1.4 Implement `assemble_timeline(project_dir)` — overlay cue clips at `start_ms` onto base `audio.wav`, write `output_audio.wav`
- [x] 1.5 Write `remux_manifest.json` with per-cue clip source and paths
- [x] 1.6 Add unit tests for clip resolution and missing-TTS validation

## 2. Video remux module

- [x] 2.1 Implement `remux_video(source_video, output_audio, subtitles_srt, output_path)` using ffmpeg
- [x] 2.2 Video stream copy (`-c:v copy`), audio AAC 192k, subtitle mov_text track
- [x] 2.3 Handle duration alignment: pad audio or use video duration as master
- [x] 2.4 Add integration test with short sample video + 2 segment clips

## 3. Remux job and CLI

- [x] 3.1 Implement `remux_pipeline(project_dir)` orchestrating assemble → mux
- [x] 3.2 Add background remux job to web job runner with stages `assembling` → `muxing` → `remux_ready`
- [x] 3.3 `POST /api/projects/{id}/remux` and `GET /api/projects/{id}/remux-status`
- [x] 3.4 Add `caption-helper remux <project-dir>` CLI subcommand
- [x] 3.5 Extend `meta.json` status with `remuxing`, `remux_ready`, `remux_failed`

## 4. Output streaming API

- [x] 4.1 `GET /api/projects/{id}/output-video` — stream `output_video.mp4` with range support
- [x] 4.2 `GET /api/projects/{id}/output-audio` — stream `output_audio.wav`

## 5. Web UI preview page

- [x] 5.1 Add route `/projects/:id/preview` in frontend
- [x] 5.2 Build preview page: video player, "Build output" / "Rebuild" button, progress indicator
- [x] 5.3 Implement original vs output video toggle
- [x] 5.4 Add subtitle visibility during playback (native text track or synchronized overlay)
- [x] 5.5 Add download links for `output_video.mp4` and `output_audio.wav`
- [x] 5.6 Link to preview from editor page after synthesis completes

## 6. Verification

- [x] 6.1 End-to-end: edit 2 cues → TTS → remux → preview plays output with correct audio at timestamps
- [x] 6.2 Verify unmodified cues play original segment audio in output
- [x] 6.3 Verify modified cues play TTS audio in output
- [x] 6.4 Verify edited subtitles visible during preview playback
- [x] 6.5 Verify remux with zero modifications (all original segments) succeeds
- [x] 6.6 Document preview workflow in README
