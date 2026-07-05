## Context

CaptionHelper re-synthesizes edited subtitle cues with MOSS-TTS voice cloning. The `tts-zh-en-code-mix-t4` change optimized for single T4 16 GB by defaulting to **MOSS-TTS-Local-Transformer 1.7B** and adding zh-en code-mix detection (`language_mode=auto`). **MOSS-TTS-Local-Transformer-v1.5 (4B)** was left as an optional `--tts-model local-v1.5-4b` preset.

The user now has **two T4 16 GB GPUs** and wants **quality first** (throughput / parallel synthesis deferred). v1.5 4B improves code-switching, cloning similarity, and prosody per MOSS-TTS benchmarks, but introduces integration gaps:

- v1.5 outputs **48 kHz stereo**; pipeline is **16 kHz mono** end-to-end
- `MossTTSEngine` saves at model native rate with no resample (unlike `GLMTTSEngine`)
- `get_gpu_info()` always inspects `cuda:0`; TTS may run on `cuda:1` in dual-GPU setups
- `tokens_per_second` defaults to **25.0** while MOSS-TTS docs state **~12.5 audio tokens per second**, causing over-generation and aggressive ffmpeg trim in fixed-slot mode

## Goals / Non-Goals

**Goals:**

- Default to **4B v1.5** when the configured TTS GPU meets VRAM requirements
- Normalize MOSS output to **16 kHz mono** before duration fitting and remux
- **Model-aware token mapping** for fixed-slot duration control
- **Device-aware preflight** for `--tts-device`
- Stronger UX guidance for **code-mixed + compression-risk** cues toward natural-pace
- Document **dual-T4** role split (ASR `cuda:0`, TTS `cuda:1`)

**Non-Goals:**

- Parallel cue synthesis across two GPUs
- Model sharding / tensor parallelism across GPUs
- MOSS-TTS 8B support
- Pinyin/IPA pronunciation UI
- Replacing or changing GLM-TTS behavior
- Auto-switching project `sync_mode` without user action

## Decisions

### 1. Default model selection

**Choice:** Change `DEFAULT_MODEL` and CLI/web default preset to `local-v1.5-4b`. At startup, if the configured TTS device has &lt; 12 GB VRAM, log a warning and fall back to `local-1.7b` (or block synthesis with a clear message — prefer **warn + fallback at startup**, hard block only if user explicitly requests 4B on insufficient VRAM).

**Rationale:** User explicitly targets 4B v1.5 for quality; dual T4 makes dedicated TTS GPU practical. Keeping 1.7b preset preserves rollback.

**Alternatives:**

| Approach | Verdict |
|----------|---------|
| Always 4B, no fallback | Reject — breaks single 8 GB GPU dev machines |
| Auto-pick 4B only when ≥ 14 GB free | Reject — total VRAM on device is sufficient signal for T4 |
| Leave 1.7B default, document manual upgrade | Reject — user asked to optimize defaults |

### 2. Output resampling in MossTTSEngine

**Choice:** After `processor.decode`, resample to `PIPELINE_SAMPLE_RATE = 16000` and downmix stereo → mono before `torchaudio.save`, mirroring `GLMTTSEngine._resample_and_save`.

```python
PIPELINE_SAMPLE_RATE = 16_000

# After decode:
# 1. float32 tensor [channels, samples]
# 2. mean(dim=0) if stereo
# 3. Resample if model sampling_rate != 16000
# 4. save at 16000 Hz
```

**Rationale:** `fit_duration` and `wav_duration_ms` operate on saved files; correct sample rate avoids duration skew and remux quality loss from linear interpolation downstream.

### 3. Model-specific tokens_per_second

**Choice:** Introduce preset defaults:

| Preset | `tokens_per_second` |
|--------|---------------------|
| `local-v1.5-4b` | `12.5` |
| `local-1.7b` | `25.0` (unchanged until empirically re-tuned) |

Store resolved value in `MossTTSConfig` and `synthesis_manifest.json` as `tokens_per_second`.

**Rationale:** MOSS model card documents 1 s ≈ 12.5 tokens for v1.5 family. Mismatch causes over-generation → trim → rushed speech, especially harmful for code-mixed English words.

**Alternatives:** Global CLI `--tokens-per-second` override remains; single global default of 12.5 rejected because 1.7B mapping was validated at 25 in existing tests.

### 4. Device-aware preflight

**Choice:** Extend `get_gpu_info(device: str | None = None)` to accept `"cuda:1"` etc. `check_tts_compatibility(model_id, *, provider, device)` uses the TTS device from config. `log_gpu_info` logs the target device.

**Rationale:** Dual-T4 deployment puts TTS on `cuda:1`; checking only device 0 gives false negatives/positives.

### 5. Code-mixed compression warnings

**Choice:** Extend compression-risk API response with `code_mixed: bool` and `recommend_natural_pace: bool` when `at_risk and code_mixed`. Editor shows an explicit message: *"中英混合且时长可能不足，建议使用自然语速模式"* with link/action to switch sync mode. Do **not** auto-change `sync_mode`.

**Rationale:** Quality improvement without breaking users who prefer fixed-slot timeline lock.

### 6. Dual-T4 deployment documentation

**Choice:** README section:

```bash
uv run caption-helper web \
  --device cuda:0 \
  --tts-device cuda:1 \
  --tts-model local-v1.5-4b
```

**Rationale:** Zero code for GPU assignment beyond existing flags; avoids ASR/TTS VRAM contention on one card.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 4B OOM on long cues (single T4) | `max_new_tokens` cap; `empty_cache()` between cues; document dual-GPU split |
| 4B slower than 1.7B | Accept for quality phase; parallel synthesis is follow-up change |
| 1.7B token rate still wrong | Defer re-calibration; keep 25.0 until measured |
| Resample adds CPU/GPU overhead | One-time per cue; negligible vs generation |
| Existing projects expect 1.7B voice | Re-synthesis required after upgrade; manifest records `model_id` |

## Migration Plan

1. Ship code changes; default preset becomes `local-v1.5-4b`
2. Existing deployments: add `--tts-model local-1.7b` to rollback
3. Re-run synthesis on projects with modified cues to regenerate `tts_segments/`
4. Dual-T4 users: update systemd/docker command with `--tts-device cuda:1`

## Open Questions

- Should startup auto-fallback from 4B to 1.7B be silent or require user acknowledgment in Web UI? _Prefer log warning + use 1.7b only when VRAM check fails at startup._
- Empirical token calibration for 1.7B on real lecture samples — defer to follow-up spike.
