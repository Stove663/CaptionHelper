## 1. Subtitle editor constraints (delta)

- [x] 1.1 Update frontend cue editor: render `start_ms`, `end_ms`, `spk` as read-only labels (remove input fields)
- [x] 1.2 Update `PUT /api/projects/{id}/subtitles` validation: reject changes to `start_ms`, `end_ms`, `spk`
- [x] 1.3 Update `compute_modified()` to set `modified` only when `text_edited.strip() != text_original.strip()`
- [x] 1.4 Add unit tests for immutable field rejection and text-only modification detection

## 2. MOSS-TTS dependency setup

- [x] 2.1 Add optional `[tts]` extra in `pyproject.toml` documenting MOSS-TTS install (`transformers>=5.0`, `torchaudio`)
- [x] 2.2 Document MOSS-TTS-v1.5 model download, GPU requirements, and ffmpeg prerequisite in README
- [x] 2.3 Add `caption-helper` config for `--tts-model`, `--tts-device`, `--tokens-per-second`

## 3. MOSS-TTS wrapper module

- [x] 3.1 Implement `tts/moss_tts.py`: lazy-load `AutoModel` + `AutoProcessor` for `OpenMOSS-Team/MOSS-TTS-v1.5`
- [x] 3.2 Implement `synthesize(text, reference_wav, tokens, language)` returning audio tensor/path
- [x] 3.3 Implement `tts/duration.py`: `ms_to_tokens(duration_ms)` and `fit_duration(wav_path, target_ms)` via ffmpeg trim/pad
- [x] 3.4 Add unit test with mocked model generate for synthesis call shape

## 4. Segment synthesizer

- [x] 4.1 Implement `tts/synthesizer.py`: read `modified_segments.json`, iterate modified cues only
- [x] 4.2 For each cue: resolve reference `segments/` WAV, compute target duration and tokens, call MOSS-TTS, post-process, write `tts_segments/`
- [x] 4.3 Write `synthesis_manifest.json` with per-cue status, tokens, paths, errors
- [x] 4.4 Handle per-cue failures gracefully; continue remaining cues

## 5. API and background job

- [x] 5.1 `POST /api/projects/{id}/synthesize` — validate modified segments exist, enqueue TTS job, return 202
- [x] 5.2 `GET /api/projects/{id}/synthesis-status` — return `status`, `completed`, `total`, `errors`
- [x] 5.3 Integrate TTS job into web job runner with `synthesizing` → `synthesis_ready` | `synthesis_failed` states
- [x] 5.4 Add synthesis job mutex (one TTS job at a time per server instance)

## 6. Web UI synthesis controls

- [x] 6.1 Add "Synthesize modified segments" button in editor (enabled when `modified_segments` count > 0)
- [x] 6.2 Show synthesis progress bar polling `/synthesis-status`
- [x] 6.3 After synthesis: show per-cue play button for `tts_segments/` output alongside original segment
- [x] 6.4 Display synthesis errors from manifest for failed cues

## 7. Verification

- [x] 7.1 Verify editor rejects timestamp/speaker edits via API
- [x] 7.2 End-to-end: edit 2 cues → synthesize → confirm only 2 files in `tts_segments/`
- [x] 7.3 Verify synthesized WAV durations match cue time slots within ±50 ms
- [x] 7.4 Verify `synthesis_manifest.json` records correct reference paths and tokens
- [x] 7.5 Document full workflow in README: upload → edit text → synthesize → preview TTS segments
