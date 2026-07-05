## 1. Default model and token mapping

- [x] 1.1 Change `DEFAULT_MODEL` in `preflight.py` to `MODEL_LOCAL_V15_4B` and add `TOKENS_PER_SECOND_BY_PRESET` map (`local-v1.5-4b` → 12.5, `local-1.7b` → 25.0)
- [x] 1.2 Update `cli.py` default `--tts-model` to `local-v1.5-4b`; apply preset `tokens_per_second` in `JobRunner.set_tts_options` when model changes
- [x] 1.3 Add `resolve_tokens_per_second(model_id, override)` helper; use in `synthesizer.py` and record in `CueSynthesisRecord` / manifest
- [x] 1.4 Unit tests: 4B preset resolves 12.5 tokens/s; 1.7b preset resolves 25.0; CLI override wins

## 2. MOSS output resampling

- [x] 2.1 Add `PIPELINE_SAMPLE_RATE = 16000` constant (shared with GLM or in `tts/` module)
- [x] 2.2 Implement `_normalize_audio(audio, sample_rate) -> (tensor, 16000)` in `moss_tts.py`: downmix stereo → mono, resample if needed
- [x] 2.3 Call normalization before `torchaudio.save` in `MossTTSEngine.synthesize`
- [x] 2.4 Unit test: mock 48 kHz stereo decode → saved WAV is 16 kHz mono with correct duration

## 3. Device-aware preflight

- [x] 3.1 Extend `get_gpu_info(device: str | None = None)` to parse `cuda:N` and query that device index
- [x] 3.2 Pass TTS device from `MossTTSConfig.device` into `check_tts_compatibility` and `log_gpu_info`
- [x] 3.3 Update `jobs._run_synthesis` and `web/app.py` startup preflight to use configured TTS device
- [x] 3.4 Unit tests: preflight checks `cuda:1` VRAM; blocks 4B when device 1 &lt; 12 GB even if device 0 is 16 GB

## 4. Code-mixed compression guidance

- [x] 4.1 Add `code_mixed` and `recommend_natural_pace` fields to `CompressionRisk` dataclass (derive from `is_code_mixed`)
- [x] 4.2 Expose new fields in `GET /api/projects/{id}/compression-risk` response
- [x] 4.3 Update `EditorPage.tsx` compression banner to highlight code-mixed cues with specific natural-pace recommendation text
- [x] 4.4 Unit tests: mixed zh-en at-risk cue has `recommend_natural_pace: true`; pure Chinese at-risk has `false`

## 5. Manifest and synthesis metadata

- [x] 5.1 Add `tokens_per_second` to `CueSynthesisRecord` and `synthesis_manifest.json` output
- [x] 5.2 Ensure `gpu_name` in manifest reflects the TTS device used

## 6. Documentation and deployment

- [x] 6.1 Update README: 4B v1.5 as default; dual-T4 example (`--device cuda:0 --tts-device cuda:1`)
- [x] 6.2 Update README model table and troubleshooting (OOM → try dedicated TTS GPU or fall back to 1.7b)
- [x] 6.3 Update `.env.example` if TTS device/model env vars are documented

## 7. Integration verification

- [x] 7.1 Update existing preflight tests for new default model and device-aware checks
- [x] 7.2 Run full test suite (`uv run pytest`)
- [x] 7.3 Manual smoke: synthesize code-mixed cue with `local-v1.5-4b` on T4; verify 16 kHz mono output and manifest fields
