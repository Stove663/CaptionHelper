## Context

CaptionHelper depends on network fetches at three layers:

1. **Install time** — `uv sync` (PyPI), `npm install` (npm registry), optional `[tts]` / `[glm-tts]` extras with large wheels (torch, transformers)
2. **First ASR run** — FunASR downloads Fun-ASR-Nano, fsmn-vad, cam++ via ModelScope (default) or HuggingFace (`--hub hf`)
3. **First TTS run** — MOSS-TTS loads weights via `transformers` / HuggingFace Hub; GLM-TTS expects `huggingface-cli download`

Today there is no project-level mirror configuration. `uv.lock` resolves against `pypi.org`; HuggingFace clients use the global endpoint; npm uses the default registry. FunASR already defaults to ModelScope when `hub` is omitted, but HuggingFace-backed TTS and package installs remain slow or unreachable in China.

## Goals / Non-Goals

**Goals:**

- One coherent mirror story: clone → `uv sync` → `npm install` → first pipeline run works in China without manual proxy setup
- Configure mirrors in repo files where possible (uv index, `.npmrc`) so install-time fetches are covered
- Bootstrap runtime env vars (`HF_ENDPOINT`, etc.) at process entry before any model load
- Never override env vars the user has already set
- Document all mirror endpoints and how to disable them for overseas users

**Non-Goals:**

- Automatic geo-detection or switching mirrors by IP
- Mirroring git clone URLs (GLM-TTS repo) — document manual alternatives only
- Hosting private mirror infrastructure
- Changing model IDs or hub semantics beyond documenting ModelScope as ASR default
- Patching third-party libraries (FunASR, transformers) internals

## Decisions

### 1. Central bootstrap module: `caption_helper.network.mirrors`

**Choice:** Add `apply_china_mirror_defaults()` that sets env vars only when unset:

| Variable | Default (China mirror) | Covers |
|----------|----------------------|--------|
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace Hub (MOSS-TTS, GLM-TTS checkpoints) |
| `HF_HUB_ENABLE_HF_TRANSFER` | `0` | Avoid hf_transfer issues on some mirrors |
| `MODELSCOPE_CACHE` | unchanged | ModelScope is already China-hosted; no endpoint override needed |

Call from `cli.main()` and `web.app` factory before any lazy imports that trigger downloads.

**Rationale:** Single entry point, testable, idempotent, respects user overrides.

**Alternatives considered:**
- Per-module env setup in `moss_tts.py` / `transcribe.py` only — rejected; easy to miss a code path (web jobs, tests).
- Shell wrapper script — rejected; `uv run` should work without extra steps.

### 2. Python package index: uv default index in `pyproject.toml`

**Choice:** Add Tsinghua PyPI mirror as the default uv index:

```toml
[[tool.uv.index]]
name = "tsinghua"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

Regenerate `uv.lock` against the mirror (URLs in lockfile will point to mirror-hosted wheels where available).

**Rationale:** `uv sync` is the documented install path; index config is the supported uv mechanism.

**Alternatives considered:**
- Aliyun mirror — equally valid; Tsinghua is widely documented and stable.
- Document-only (no pyproject change) — rejected; does not meet "default" requirement.

### 3. npm registry: `frontend/.npmrc`

**Choice:** Commit `frontend/.npmrc`:

```
registry=https://registry.npmmirror.com
```

**Rationale:** Covers `npm install` for the Web UI build without per-user `npm config`.

### 4. ASR hub default: ModelScope (no code change)

**Choice:** Keep `TranscriberConfig.hub = None` (FunASR ModelScope). Document in README and spec. `--hub hf` remains for overseas HuggingFace.

**Rationale:** Already implemented; ModelScope (`modelscope.cn`) is China-accessible.

### 5. Opt-out for overseas users

**Choice:** README section "Mirrors & overseas users" listing:
- How to remove or override uv index (comment out `[[tool.uv.index]]` or set `UV_INDEX_URL`)
- Delete or override `frontend/.npmrc`
- Set `HF_ENDPOINT=https://huggingface.co` before running

No `CAPTION_HELPER_USE_MIRRORS=0` flag in v1 — env and config file overrides are sufficient.

**Rationale:** Minimal API surface; mirrors are the project default per user request.

### 6. Documentation and `.env.example`

**Choice:** Add `.env.example` at repo root with commented mirror variables; expand README install/TTS sections to reference mirrors and hf-mirror.com for GLM-TTS checkpoint download.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Mirror outage or lag behind PyPI | Document fallback to official index; user can unset default index |
| Lockfile wheel URLs differ from pypi.org | Regenerate lock with mirror; hashes must remain valid |
| hf-mirror.com missing or stale models | User can set `HF_ENDPOINT` to official hub; README notes risk |
| npm mirror missing scoped packages | npmmirror is comprehensive; document `npm config` override |
| torch CUDA wheels not on PyPI mirror | May still need PyTorch official index; document `UV_EXTRA_INDEX_URL` if needed |

## Migration Plan

1. Land config files (`pyproject.toml`, `.npmrc`, bootstrap module) in one PR
2. Regenerate `uv.lock` with mirror index
3. No data migration; existing cached models unaffected
4. Rollback: revert index config and bootstrap import

## Open Questions

- Whether torch/torchaudio wheels require an additional Tsinghua PyTorch index for CUDA builds — validate during implementation on a China-network or mirror test
- Whether `funasr` model download needs explicit `MODELSCOPE_ENDPOINT` — verify against current modelscope SDK; likely unnecessary since ModelScope is domestic
