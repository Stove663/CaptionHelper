## 1. Project metadata and phoneme mode resolution

- [x] 1.1 Add `glm_phoneme_mode: auto | on | off` to `ProjectMeta` with `setdefault("auto")` on read
- [x] 1.2 Add `resolve_glm_use_phoneme(text, mode)` helper using `is_code_mixed`
- [x] 1.3 Expose `glm_phoneme_mode` in `GET /api/projects/{id}` (optional `PUT` if needed for future UI)

## 2. Mixed-text preprocessing

- [x] 2.1 Add `prepare_glm_mixed_text(text)` in `tts/glm_text_prep.py` — CJK↔Latin boundary spacing
- [x] 2.2 Unit tests: `打开terminal` → `打开 terminal`; pure Chinese unchanged; already-spaced unchanged

## 3. GLM-TTS phoneme-in integration

- [x] 3.1 Add `use_phoneme` parameter to `_GLMRuntime.ensure_loaded` and cache key `f"{home}:phoneme={flag}"`
- [x] 3.2 Pass resolved `use_phoneme` to `load_models` and `generate_long` (do not duplicate `g2p_infer` in CaptionHelper)
- [x] 3.3 Apply `prepare_glm_mixed_text` before `text_normalize` in `synthesize_utterance` when code-mixed
- [x] 3.4 Thread `glm_phoneme_mode` from project meta through `JobRunner` → `GLMTTSEngine` / synthesizer
- [x] 3.5 Unit test: mock `generate_long` asserts `use_phoneme=True` for mixed text with `mode=auto`

## 4. Synthesis manifest

- [x] 4.1 Add `phoneme_enabled`, `text_prep_applied`, `glm_phoneme_mode` to `CueSynthesisRecord`
- [x] 4.2 Populate fields in `synthesizer.py` when `tts_provider=glm-tts`
- [x] 4.3 Unit test: manifest JSON includes new fields for GLM synthesis records

## 5. Provider-aware natural-pace UX

- [x] 5.1 Extend compression-risk API with `provider_guidance` when `tts_provider=glm-tts` + fixed-slot + code-mixed modified cues
- [x] 5.2 Update `EditorPage.tsx` banner to show GLM-specific text when `tts_provider=glm-tts` and code-mixed cues exist
- [x] 5.3 Update `api.ts` types for `provider_guidance`
- [x] 5.4 Frontend/backend tests for GLM banner text and API field

## 6. Documentation

- [x] 6.1 README: GLM code-mix guidance (phoneme auto, natural-pace for fixed-slot, phoneme limits on English)
- [x] 6.2 README: document GLM-TTS phoneme-in call chain summary and pin recommendation

## 7. Verification

- [x] 7.1 Run full test suite (`uv run pytest`)
- [x] 7.2 Manual smoke: GLM project with mixed cue — verify manifest flags and banner text
