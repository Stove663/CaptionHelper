from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def write_test_wav(path: Path, duration_s: float = 2.0, *, amplitude: float = 0.3) -> None:
    sr = 16000
    n = int(duration_s * sr)
    t = np.arange(n, dtype=np.float32)
    audio = amplitude * np.sin(2 * np.pi * 440 * t / sr)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr)
