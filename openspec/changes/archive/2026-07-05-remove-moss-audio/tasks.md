## 1. Python backend — remove MOSS-Audio ASR

- [x] 1.1 Delete `src/caption_helper/moss_audio_transcribe.py`
- [x] 1.2 Simplify `transcribe.py`: remove `AsrProvider`, MOSS branch in `get_transcriber()`, and `asr_provider` from `TranscriberConfig`
- [x] 1.3 Simplify `asr_preflight.py`: remove MOSS-Audio constants, `resolve_moss_audio_model()`, and moss-audio preflight branch; keep FunASR-only check
- [x] 1.4 Remove `--asr-provider` from `cli.py` and always use `FunASRTranscriber` in pipeline paths
- [x] 1.5 Remove `asr_provider` from `web/store.py` `ProjectMeta` (load/save/API serialization); ignore legacy field on read
- [x] 1.6 Remove `PUT /api/projects/{id}/asr-provider` route and upload `asr_provider` handling from `web/routes/projects.py`
- [x] 1.7 Update `web/jobs.py` and `pipeline.py` to call FunASR directly without provider dispatch

## 2. Dependencies and tests

- [x] 2.1 Remove `[moss-audio]` optional dependency group from `pyproject.toml` and run `uv lock`
- [x] 2.2 Delete `tests/test_moss_audio_transcribe.py`
- [x] 2.3 Update `tests/test_web.py`: remove MOSS-Audio / asr-provider API tests; add test that legacy `meta.json` with `asr_provider: moss-audio` still loads
- [x] 2.4 Update any remaining tests referencing `asr_provider` or `moss-audio` (grep and fix)
- [x] 2.5 Run `uv run pytest` and confirm all tests pass

## 3. Frontend

- [x] 3.1 Remove ASR provider toggle and state from `HomePage.tsx`
- [x] 3.2 Remove ASR provider toggle and state from `EditorPage.tsx`
- [x] 3.3 Remove `setAsrProvider` and `asr_provider` types from `api.ts`
- [x] 3.4 Rebuild frontend (`npm run build`) if required by CI

## 4. Documentation

- [x] 4.1 Update `README.md`: remove MOSS-Audio ASR install/usage/mirror rows; clarify FunASR-only transcription; keep MOSS-TTS sections intact
- [x] 4.2 Remove MOSS-Audio references from `.env.example` if present

## 5. Verification

- [x] 5.1 Grep codebase for `moss-audio`, `moss_audio`, `MOSS-Audio` (ASR context) and confirm only MOSS-TTS references remain
- [x] 5.2 Smoke test: `uv run caption-helper process` and web upload → ASR → ready flow
