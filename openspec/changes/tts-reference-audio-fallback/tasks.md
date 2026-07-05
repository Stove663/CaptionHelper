## 1. Reference validation module

- [x] 1.1 Create `tts/reference.py` with `validate_reference(wav_path)` → duration, quality_score, issues, adequate bool
- [x] 1.2 Implement clipping, RMS, and silence ratio heuristics
- [x] 1.3 Add configurable `--min-ref-duration-ms` (default 1500) and `--min-quality-score` (default 0.5)
- [x] 1.4 Unit tests: short clip, clipped clip, quiet clip, good clip

## 2. Speaker reference bank

- [x] 2.1 Implement `build_speaker_reference_bank(project_dir)` — score all segments per spk, pick best
- [x] 2.2 Write `speaker_refs/spk{N}.wav` and `reference_quality.json`
- [x] 2.3 Hook into `pipeline.process()` after segment split
- [x] 2.4 Add `caption-helper build-refs <project-dir>` CLI for rebuilding bank on existing projects
- [x] 2.5 Unit tests: multi-speaker project, single-speaker, all-short segments edge case

## 3. Fallback resolution

- [x] 3.1 Implement `resolve_reference(cue, project_dir)` with 4-level hierarchy
- [x] 3.2 Implement `concatenate_adjacent_same_speaker(cue, max_ms=10000)`
- [x] 3.3 Integrate into `tts/synthesizer.py` before MOSS-TTS call
- [x] 3.4 Record `reference_source`, `reference_fallback_reason` in `synthesis_manifest.json`
- [x] 3.5 Unit tests for each fallback level and no-reference failure

## 4. API and Web UI

- [x] 4.1 `GET /api/projects/{id}/reference-quality` — per-cue and per-speaker report
- [x] 4.2 `PUT /api/projects/{id}/cues/{index}/reference` — manual override with spk validation
- [x] 4.3 Editor UI: quality badges (adequate / fallback / unavailable) on modified cues
- [x] 4.4 Fallback detail popover: show which reference will be used and why
- [x] 4.5 Manual reference picker: dropdown of same-speaker segments with duration/quality

## 5. Synthesis integration

- [x] 5.1 Pre-synthesis scan: block UI "Synthesize" if any cue has `no_adequate_reference` (show list)
- [x] 5.2 Allow "Synthesize available" to skip failed-reference cues (optional) or require all resolved
- [x] 5.3 Display reference fallback summary after synthesis completes

## 6. Verification

- [x] 6.1 Short cue (0.4 s) automatically uses speaker bank reference
- [x] 6.2 Verify manifest records fallback reason correctly
- [x] 6.3 Manual override: user picks different same-speaker segment, synthesis uses it
- [x] 6.4 Speaker with no segment ≥ 1.5 s: cue marked failed with clear error
- [x] 6.5 Document reference fallback behavior in README
