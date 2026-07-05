from __future__ import annotations

import os

_DEFAULTS: dict[str, str] = {
    "HF_ENDPOINT": "https://hf-mirror.com",
    "HF_HUB_ENABLE_HF_TRANSFER": "0",
}


def _is_unset(name: str) -> bool:
    value = os.environ.get(name)
    return value is None or value == ""


def apply_china_mirror_defaults() -> None:
    """Set China mirror env vars when not already configured by the user."""
    for name, value in _DEFAULTS.items():
        if _is_unset(name):
            os.environ[name] = value
