## Why

MOSS-Audio was added as an optional second ASR backend, but it increases maintenance surface (optional extra, GPU preflight, prompt-based diarization parsing, separate model download path) without clear ongoing benefit now that FunASR remains the default and better-supported path. Removing it simplifies the codebase, dependencies, UI, and documentation to a single ASR stack.

## What Changes

- **BREAKING**: Remove `moss-audio` as a valid `asr_provider`; FunASR becomes the only ASR backend.
- Delete `moss_audio_transcribe.py`, MOSS-Audio preflight logic, and the `[moss-audio]` optional dependency group in `pyproject.toml`.
- Remove ASR provider selection from Web UI (upload form and editor toggle); projects always use FunASR.
- Remove `PUT /api/projects/{id}/asr-provider` and `asr_provider` upload field validation for multiple providers; drop or simplify related API fields.
- Migrate existing projects with `asr_provider: moss-audio` in `meta.json` to `funasr` on read (or ignore the stale value).
- Delete `openspec/specs/moss-audio-asr/spec.md` and retire the `asr-provider-selection` capability (no multi-provider ASR choice).
- Update `video-to-subtitles`, `web-ui-server`, and `pipeline-stage-rerun` specs to reference FunASR only.
- Remove MOSS-Audio tests, README sections, and CLI `--asr-provider` flag (or restrict it to `funasr` only and deprecate the flag).
- **Note**: MOSS-TTS (speech synthesis) is **not** in scope; only MOSS-Audio ASR is removed.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `video-to-subtitles`: Transcription requirement references FunASR only; remove MOSS-Audio provider branch and model download scenarios.
- `web-ui-server`: Remove ASR provider upload/selection endpoints and UI-related requirements; background ASR always uses FunASR.
- `pipeline-stage-rerun`: Remove MOSS-Audio rerun scenarios; ASR rerun always uses FunASR.
- `asr-provider-selection`: **Removed** — capability deleted because ASR backend selection is no longer a product feature.

### Removed Capabilities

- `moss-audio-asr`: Entire capability deleted.

## Impact

- **Python**: `transcribe.py`, `asr_preflight.py`, `cli.py`, `pipeline.py`, `web/jobs.py`, `web/routes/projects.py`, `web/store.py`
- **Frontend**: `HomePage.tsx`, `EditorPage.tsx`, `api.ts`
- **Tests**: `test_moss_audio_transcribe.py` (delete), `test_web.py` MOSS-Audio cases
- **Dependencies**: Remove `[moss-audio]` extra from `pyproject.toml` and lockfile refresh
- **Docs**: `README.md` mirror/ASR sections
- **OpenSpec**: Delete `openspec/specs/moss-audio-asr/spec.md`; archive sync removes `asr-provider-selection`
