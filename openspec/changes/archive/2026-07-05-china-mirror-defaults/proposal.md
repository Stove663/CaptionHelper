## Why

CaptionHelper pulls Python packages, npm dependencies, and large ML model weights from overseas hosts (PyPI, HuggingFace, npm registry) on first install and first run. Users in mainland China often face blocked or very slow downloads, which blocks setup and prevents ASR/TTS from working. The project should default to well-known China mirror endpoints so a fresh clone installs and runs without manual proxy or mirror configuration.

## What Changes

- Add project-level defaults for China mirrors covering Python package indexes (uv/pip), npm registry, HuggingFace Hub, and ModelScope
- Apply mirror-related environment variables early in CLI, web server, and TTS/ASR model-load paths before any network fetch
- Document mirror defaults in README with override instructions for users outside China
- Provide optional `.env.example` or setup notes listing all mirror-related variables
- Keep existing `--hub hf` escape hatch for overseas HuggingFace; default remains ModelScope for FunASR models

## Capabilities

### New Capabilities

- `china-mirror-defaults`: Central requirements for default China mirror endpoints, env bootstrap, and user override behavior across Python, npm, HuggingFace, and ModelScope downloads

### Modified Capabilities

- `video-to-subtitles`: Clarify that FunASR model downloads SHALL use ModelScope (China-accessible hub) by default unless `--hub hf` is set

## Impact

- **Build / install**: `pyproject.toml` or `uv.toml` index configuration; optional `frontend/.npmrc`
- **Runtime**: New `caption_helper.network` (or similar) bootstrap module imported at process start
- **TTS**: `moss_tts.py`, `glm_tts.py`, `preflight.py` — HuggingFace mirror env before `from_pretrained` / CLI download hints
- **ASR**: `transcribe.py` — ModelScope mirror env before `AutoModel` load
- **Docs**: `README.md` install and GLM-TTS/MOSS-TTS sections
- **Tests**: Unit tests for mirror env application and idempotent bootstrap
