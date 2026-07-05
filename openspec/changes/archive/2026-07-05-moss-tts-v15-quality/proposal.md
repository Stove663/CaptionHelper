## Why

CaptionHelper's default MOSS-TTS model (Local-Transformer 1.7B) is a VRAM-safe choice for single T4 16 GB GPUs, but it under-delivers on the project's primary TTS workload: **voice-cloned re-synthesis of edited subtitles with Chinese–English code-mixed text**. The deployment target now includes **two T4 GPUs**, making **MOSS-TTS-Local-Transformer-v1.5 (4B)** viable as the default. Quality gaps also remain in the pipeline layer: MOSS v1.5 outputs 48 kHz stereo while the pipeline expects 16 kHz mono, `tokens_per_second` may not match MOSS's documented token rate, and fixed-slot mode still compresses code-mixed cues that need more time.

## What Changes

- Set default MOSS-TTS model to **`local-v1.5-4b`** (`OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5`) when the configured TTS GPU has ≥ 12 GB VRAM; retain `local-1.7b` as fallback via `--tts-model`
- Resample and downmix MOSS-TTS output to **16 kHz mono** before `fit_duration` and remux (matching GLM-TTS and pipeline specs)
- Calibrate **model-specific `tokens_per_second`** defaults (v1.5 4B uses MOSS-documented ~12.5 tokens/s; 1.7B keeps existing mapping until re-validated)
- Update **preflight** to validate VRAM on the **configured TTS device** (`--tts-device`), not always `cuda:0`
- When a modified cue is **code-mixed and compression-at-risk**, surface a **stronger pre-synthesis recommendation** to use `natural-pace` mode (warn before synthesis; do not silently change project mode)
- Document **dual-T4 deployment**: ASR on `cuda:0`, MOSS-TTS on `cuda:1` to avoid VRAM contention
- Keep **1.7b preset** and CLI backward compatibility; no dual-GPU parallel cue synthesis in this change (throughput deferred)

## Capabilities

### New Capabilities

_None — quality improvements extend existing TTS capabilities._

### Modified Capabilities

- `moss-tts-synthesis`: Default model becomes 4B v1.5; MOSS output normalized to 16 kHz mono; model-specific token duration mapping
- `tts-hardware-preflight`: Preflight and logging target the configured TTS CUDA device
- `timeline-sync-modes`: Stronger compression warning for code-mixed high-risk cues recommending natural-pace

## Impact

- **Default model**: `DEFAULT_MODEL` and CLI default shift to `local-v1.5-4b` on capable hardware
- **VRAM**: ~10–12 GB peak on TTS GPU; dual-T4 split recommended in README
- **Code**: `moss_tts.py`, `preflight.py`, `duration.py`, `synthesizer.py`, `cli.py`, `web/app.py`, `compression_risk` API/UI, tests, README
- **Artifacts**: `synthesis_manifest.json` may record `output_sample_rate` / resampling applied
- **Non-goals this change**: parallel multi-GPU synthesis, Pinyin/IPA editor, 8B model, replacing GLM-TTS
