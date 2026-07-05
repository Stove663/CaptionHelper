# china-mirror-defaults Specification

## Purpose

Default China-hosted mirrors for Python packages, npm dependencies, HuggingFace model downloads, and documented opt-out for overseas users.

## Requirements

### Requirement: Python package index defaults to China mirror

The project SHALL configure `uv` to use a China-hosted PyPI mirror (Tsinghua `pypi.tuna.tsinghua.edu.cn`) as the default package index in `pyproject.toml`, so `uv sync` and `uv add` fetch wheels and sdists from the mirror without per-user configuration.

#### Scenario: Fresh install via uv sync

- **WHEN** a developer clones the repository and runs `uv sync` without setting `UV_INDEX_URL`
- **THEN** Python dependencies are resolved and downloaded from the configured China PyPI mirror

#### Scenario: Overseas user overrides index

- **WHEN** a user sets `UV_INDEX_URL` to the official PyPI index or removes the default mirror from project config
- **THEN** `uv sync` uses the user-specified index instead of the China mirror

### Requirement: npm registry defaults to China mirror

The frontend SHALL ship a committed `.npmrc` that sets `registry=https://registry.npmmirror.com`, so `npm install` in `frontend/` uses the China npm mirror by default.

#### Scenario: Frontend dependency install

- **WHEN** a developer runs `npm install` inside `frontend/` without a personal npm registry override
- **THEN** packages are fetched from the npmmirror registry

### Requirement: Runtime HuggingFace mirror bootstrap

The system SHALL call a shared mirror-bootstrap function at CLI and web-server startup that sets `HF_ENDPOINT` to `https://hf-mirror.com` when the variable is not already set in the environment, before any HuggingFace Hub download or `from_pretrained` call.

#### Scenario: MOSS-TTS first load in China

- **WHEN** the user runs TTS synthesis and `HF_ENDPOINT` is unset
- **THEN** the process environment uses the hf-mirror endpoint before MOSS-TTS model weights are downloaded

#### Scenario: User-provided HF endpoint preserved

- **WHEN** the user has already set `HF_ENDPOINT` (including to the official `https://huggingface.co`)
- **THEN** the bootstrap function does not overwrite the existing value

### Requirement: Documented mirror configuration

The README SHALL document all default mirror endpoints (PyPI, npm, HuggingFace), the `.env.example` mirror variables, and instructions for overseas users to opt out or override mirrors.

#### Scenario: New user setup

- **WHEN** a user reads the Install section of README
- **THEN** they find mirror defaults explained and GLM-TTS checkpoint download instructions referencing the HuggingFace mirror

### Requirement: Idempotent mirror bootstrap

The mirror-bootstrap function SHALL be safe to call multiple times and SHALL only set default values for variables that are unset or empty.

#### Scenario: Repeated bootstrap calls

- **WHEN** `apply_china_mirror_defaults()` is invoked more than once in the same process
- **THEN** environment variables retain their first effective values without error
