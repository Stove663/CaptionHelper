## 1. Install-time mirror configuration

- [x] 1.1 Add `[[tool.uv.index]]` Tsinghua PyPI mirror as default in `pyproject.toml`
- [x] 1.2 Regenerate `uv.lock` against the mirror index and verify `uv sync` succeeds
- [x] 1.3 Add `frontend/.npmrc` with `registry=https://registry.npmmirror.com`
- [x] 1.4 Add `.env.example` with commented mirror variables (`HF_ENDPOINT`, `UV_INDEX_URL`, etc.)

## 2. Runtime mirror bootstrap

- [x] 2.1 Create `src/caption_helper/network/mirrors.py` with `apply_china_mirror_defaults()` (idempotent, no overwrite of set vars)
- [x] 2.2 Call bootstrap from `cli.main()` before subcommand dispatch
- [x] 2.3 Call bootstrap from web app factory (`web/app.py`) before route registration
- [x] 2.4 Add unit tests for mirror bootstrap (unset vars get defaults, existing vars preserved, idempotent)

## 3. ASR hub default verification

- [x] 3.1 Confirm `TranscriberConfig` and web pipeline jobs omit `hub` by default (ModelScope)
- [x] 3.2 Add test or doc assertion that `--hub hf` is the only path to HuggingFace for ASR

## 4. Documentation

- [x] 4.1 Add README section "Mirrors & overseas users" listing PyPI, npm, HuggingFace defaults and opt-out steps
- [x] 4.2 Update GLM-TTS / MOSS-TTS install instructions to use `HF_ENDPOINT=https://hf-mirror.com` for checkpoint download
- [x] 4.3 Note ModelScope as default ASR hub in README Options table (clarify omit vs `--hub hf`)

## 5. Validation

- [x] 5.1 Run `uv run pytest` and ensure all tests pass
- [x] 5.2 Smoke-check that `apply_china_mirror_defaults()` runs without error when imported from CLI entry point
