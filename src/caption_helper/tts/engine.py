from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TTSEngine(Protocol):
    config: Any
    peak_vram_mb: int

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        tokens: int | None,
        *,
        output_path: Path,
        reference_text: str | None = None,
    ) -> Path: ...

    def clear_cuda_cache(self) -> None: ...

    def reset_vram_stats(self) -> None: ...
