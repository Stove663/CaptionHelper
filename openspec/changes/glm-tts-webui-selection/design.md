## Context

CaptionHelper re-synthesizes edited subtitle cues using zero-shot voice cloning. The existing pipeline (`moss-tts-segment-synthesis` and follow-on changes) routes all synthesis through [MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS): per-cue reference resolution, token-based duration control, `tts_segments/` output, and downstream remux are all built around a single engine.

Users now want an alternative backend — [GLM-TTS](https://github.com/zai-org/GLM-TTS) — selectable per project from the Web UI. GLM-TTS uses a different architecture (LLM token generation + Flow Matching vocoder, CosyVoice-style frontend) but supports the same core capability: zero-shot cloning from 3–10 s prompt audio with Chinese and English-mixed text.

Partial scaffolding already exists: `tts_provider` in `meta.json`, `PUT /api/projects/{id}/tts-provider`, editor toggle buttons, and `JobRunner._get_tts_engine(provider)`. `GLMTTSEngine` is a stub; synthesis preflight in `_run_synthesis` still checks only the MOSS model id.

## Goals / Non-Goals

**Goals:**

- Per-project TTS provider selection (`moss-tts` | `glm-tts`) persisted in `meta.json` and exposed via project APIs
- Web UI toggle in the editor toolbar; selection survives reload
- Synthesis jobs route to the selected engine; output lands in the same `tts_segments/` layout for remux compatibility
- Provider-aware preflight before job submission and at job start
- Implement `GLMTTSEngine` with voice cloning from resolved reference WAVs
- Record active provider in `synthesis_manifest.json`
- Keep `moss-tts` as default for existing projects

**Non-Goals:**

- Running MOSS-TTS and GLM-TTS concurrently on the same GPU (jobs remain serialized)
- Per-cue provider mixing within one project
- GLM-TTS phoneme-in / RL variant selection in the UI
- Replacing MOSS-TTS as the CLI default
- Bundling GLM-TTS weights in the repo (download on first use, same as MOSS-TTS)

## Decisions

### 1. Provider identifier and storage

**Choice:** Store `tts_provider: "moss-tts" | "glm-tts"` in `meta.json` via `ProjectMeta.tts_provider`, default `"moss-tts"`.

**Rationale:** Matches existing `sync_mode` pattern; backward compatible via `setdefault` on read.

**Alternatives considered:**

| Approach | Verdict |
|----------|---------|
| Server-global default only | Reject — users need per-project choice |
| Store in `synthesis_manifest.json` only | Reject — selection must exist before first synthesis |

### 2. Shared engine contract

**Choice:** Both engines implement the same method surface used by `synthesizer.py`:

```python
def synthesize(self, text, reference_wav, tokens, *, output_path) -> Path
def reset_vram_stats(self) -> None
def clear_cuda_cache(self) -> None
@property peak_vram_mb -> int
```

Post-processing (`fit_duration`, natural-pace ripple) stays in `synthesizer.py`. GLM-TTS does not use MOSS `tokens`; when `tokens is None` (natural-pace) GLM-TTS generates at natural length; when `tokens` is set (fixed-slot) GLM-TTS generates freely then `fit_duration` trims/pads to the slot.

**Rationale:** Minimizes changes to the synthesizer loop and remux path. Duration mapping via ffmpeg is engine-agnostic.

**Alternatives considered:**

| Approach | Verdict |
|----------|---------|
| Fork `synthesizer.py` per provider | Reject — duplicates reference resolution and manifest logic |
| Protocol/ABC `TTSEngine` | Accept if typing clarity helps; not required for first ship |

### 3. GLM-TTS integration strategy

**Choice:** Vendor GLM-TTS as an optional `[glm-tts]` extra (or extend `[tts]`) with lazy import inside `GLMTTSEngine`. Load checkpoints from HuggingFace `zai-org/GLM-TTS` into a configurable cache dir. Wrap the repo's inference entry points (`glmtts_inference.py` / `frontend.py`) rather than reimplementing the two-stage pipeline.

**Rationale:** GLM-TTS has heavyweight deps (CosyVoice frontend, Flow, custom LLM) and its own `requirements.txt`. Isolating imports avoids breaking MOSS-only installs.

**Config:** `GLMTTSConfig` extends `MossTTSConfig` with `provider="glm-tts"` and `model="zai-org/GLM-TTS"` (checkpoint path). Reuse `device` resolution from MOSS.

### 4. Web UI and API

**Choice:** Toggle group in `EditorPage` toolbar (MOSS-TTS / GLM-TTS), disabled during synthesis. `PUT /api/projects/{id}/tts-provider` validates enum and writes meta. `GET /api/projects/{id}` returns `tts_provider`. `POST /synthesize` preflight uses `jobs.tts_model_id(provider=project.tts_provider)`.

**Rationale:** Mirrors existing sync-mode UX; no modal or per-job override needed.

### 5. Preflight per provider

**Choice:** Extend `check_tts_compatibility(model_id, *, provider="moss-tts")` (or separate `check_glm_tts_compatibility`) with GLM-TTS VRAM floor (~8 GB CUDA minimum, document T4 16 GB as target). `_run_synthesis` must use the project's provider when calling preflight, not always `self._tts_config.model`.

**Rationale:** Current bug: background job preflight ignores GLM-TTS selection.

### 6. Manifest metadata

**Choice:** Add `tts_provider` to `SynthesisResult` / `synthesis_manifest.json`.

**Rationale:** Aids debugging when users switch providers between runs; remux does not need it but support does.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| GLM-TTS deps conflict with MOSS-TTS torch/transformers pins | Separate optional extra; document install order; lazy import |
| GLM-TTS lacks MOSS-style `tokens` duration hint | Rely on existing `fit_duration` post-process for fixed-slot mode |
| Larger combined disk footprint (two model families) | Document HF cache size; only download selected provider's weights |
| Switching provider mid-project leaves stale `tts_segments/` | Document that re-synthesis overwrites; optional future warning in UI |
| GLM-TTS sample rate ≠ pipeline expectation | Resample in engine wrapper to match project audio rate (e.g. 16 kHz) if needed |

## Migration Plan

1. Ship metadata + API + UI (already scaffolded) — existing projects default to `moss-tts`, no migration script needed.
2. Implement `GLMTTSEngine` and provider-aware preflight.
3. Document `[glm-tts]` install and HF checkpoint download in README.
4. Rollback: set `tts_provider` back to `moss-tts` in meta or via UI; no schema migration.

## Open Questions

- Exact minimum VRAM for `zai-org/GLM-TTS` on T4 — validate empirically and tune preflight threshold.
- Whether GLM-TTS output sample rate matches `segments/` (16 kHz); resampling may be required in the wrapper.
- Pin GLM-TTS git tag vs. track `main` for reproducibility.
