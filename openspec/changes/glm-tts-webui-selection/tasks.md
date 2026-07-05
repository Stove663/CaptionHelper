## 1. Project metadata and API

- [x] 1.1 Add `tts_provider` field to `ProjectMeta` with default `moss-tts` and `setdefault` on read in `store.py`
- [x] 1.2 Add `PUT /api/projects/{id}/tts-provider` validating `moss-tts` | `glm-tts`
- [x] 1.3 Return `tts_provider` in `GET /api/projects/{id}` and project list responses
- [x] 1.4 Add `store.update_tts_provider()` helper (replace direct `_write_meta` in route)
- [x] 1.5 Add API unit tests for provider validation, persistence, and default fallback

## 2. Web UI provider selector

- [x] 2.1 Add MOSS-TTS / GLM-TTS toggle group in `EditorPage` toolbar
- [x] 2.2 Load saved `tts_provider` on project fetch; persist via `setTtsProvider` API
- [x] 2.3 Disable provider toggle while synthesis is in progress
- [x] 2.4 Show active provider in synthesis status or manifest panel after job completes

## 3. Synthesis routing

- [x] 3.1 Add `JobRunner._get_tts_engine(provider)` dispatching to `MossTTSEngine` or `GLMTTSEngine`
- [x] 3.2 Pass `project.tts_provider` into `synthesize_modified_segments` from `_run_synthesis`
- [x] 3.3 Use provider-aware `tts_model_id` in `POST /synthesize` preflight
- [x] 3.4 Fix `_run_synthesis` background preflight to check the selected provider's model, not always MOSS config
- [x] 3.5 Record `tts_provider` in `SynthesisResult` and `synthesis_manifest.json`
- [x] 3.6 Loosen `synthesizer.py` engine type hints to accept both engines (protocol or union)

## 4. GLM-TTS engine integration

- [x] 4.1 Scaffold `tts/glm_tts.py` with `GLMTTSConfig` and `GLMTTSEngine` stub
- [x] 4.2 Add optional `[glm-tts]` extra in `pyproject.toml` with GLM-TTS dependencies documented
- [x] 4.3 Implement lazy model load from HuggingFace `zai-org/GLM-TTS` checkpoint cache
- [x] 4.4 Implement `GLMTTSEngine.synthesize(text, reference_wav, tokens, output_path)` using GLM-TTS zero-shot cloning API
- [x] 4.5 Match engine surface: `reset_vram_stats`, `clear_cuda_cache`, `peak_vram_mb`
- [x] 4.6 Resample output WAV to pipeline sample rate if GLM-TTS native rate differs
- [x] 4.7 Add unit test with mocked GLM-TTS inference verifying call shape and output path

## 5. Provider-aware preflight

- [x] 5.1 Extend preflight with GLM-TTS VRAM and CUDA requirements
- [x] 5.2 Return clear error when GLM-TTS extra not installed but provider is `glm-tts`
- [x] 5.3 Block or warn on unsupported GPU before `POST /synthesize` and at job start

## 6. Documentation and verification

- [x] 6.1 Document GLM-TTS install, checkpoint download, and provider selection in README
- [x] 6.2 Manual test: select GLM-TTS, synthesize modified cues, verify `tts_segments/` and remux
- [x] 6.3 Manual test: existing projects without `tts_provider` default to MOSS-TTS unchanged
