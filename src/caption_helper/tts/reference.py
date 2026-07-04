from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from caption_helper.extract import check_ffmpeg
from caption_helper.split import segment_filename
from caption_helper.subtitles_json import Cue, load_subtitles

logger = logging.getLogger(__name__)

SEGMENT_RE = re.compile(r"^(\d{4})_spk(\d+)_(\d+)-(\d+)\.wav$")

DEFAULT_MIN_REF_DURATION_MS = 1500
DEFAULT_MIN_QUALITY_SCORE = 0.5


class ReferenceUnavailable(Exception):
    def __init__(self, spk: int, cue_index: int, reason: str) -> None:
        self.spk = spk
        self.cue_index = cue_index
        self.reason = reason
        super().__init__(f"No adequate reference for cue {cue_index} (spk {spk}): {reason}")


@dataclass
class ReferenceConfig:
    min_ref_duration_ms: int = DEFAULT_MIN_REF_DURATION_MS
    min_quality_score: float = DEFAULT_MIN_QUALITY_SCORE


@dataclass
class ReferenceValidation:
    path: str
    duration_ms: int
    quality_score: float
    issues: list[str] = field(default_factory=list)
    adequate: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResolvedReference:
    path: Path
    rel_path: str
    source: str
    fallback_reason: str | None = None
    duration_ms: int = 0
    quality_score: float = 0.0


def validate_reference(
    wav_path: Path,
    *,
    config: ReferenceConfig | None = None,
) -> ReferenceValidation:
    """Score a WAV for use as MOSS-TTS voice-cloning reference."""
    cfg = config or ReferenceConfig()
    wav_path = Path(wav_path)
    rel = str(wav_path)

    if not wav_path.is_file():
        return ReferenceValidation(
            path=rel,
            duration_ms=0,
            quality_score=0.0,
            issues=["file_not_found"],
            adequate=False,
        )

    data, _sr = sf.read(str(wav_path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    duration_ms = int(len(mono) / _sr * 1000)

    issues: list[str] = []
    quality = 1.0

    peak = float(np.max(np.abs(mono))) if len(mono) else 0.0
    if peak > 0.99:
        quality *= 0.5
        issues.append("clipping")

    rms = float(np.sqrt(np.mean(mono**2))) if len(mono) else 0.0
    if rms < 0.01:
        quality *= 0.6
        issues.append("quiet")

    silence_thresh = 0.01
    nonsilent = np.abs(mono) > silence_thresh
    if len(mono) > 0:
        silence_ratio = 1.0 - (np.count_nonzero(nonsilent) / len(mono))
        if silence_ratio > 0.6:
            quality *= 0.7
            issues.append("mostly_silent")

    if duration_ms < cfg.min_ref_duration_ms:
        issues.append(f"too_short:{duration_ms}ms")

    adequate = duration_ms >= cfg.min_ref_duration_ms and quality >= cfg.min_quality_score
    return ReferenceValidation(
        path=rel,
        duration_ms=duration_ms,
        quality_score=round(quality, 3),
        issues=issues,
        adequate=adequate,
    )


def _parse_segment(path: Path) -> tuple[int, int, int, int] | None:
    m = SEGMENT_RE.match(path.name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def _load_cues(project_dir: Path) -> list[Cue]:
    json_path = project_dir / "subtitles.json"
    if json_path.is_file():
        return load_subtitles(json_path)
    return []


def _segments_by_spk(project_dir: Path) -> dict[int, list[tuple[Path, int, int, int]]]:
    segments_dir = project_dir / "segments"
    by_spk: dict[int, list[tuple[Path, int, int, int]]] = {}
    if not segments_dir.is_dir():
        return by_spk
    for path in sorted(segments_dir.glob("*.wav")):
        parsed = _parse_segment(path)
        if not parsed:
            continue
        index, spk, start_ms, end_ms = parsed
        by_spk.setdefault(spk, []).append((path, index, start_ms, end_ms))
    return by_spk


def build_speaker_reference_bank(
    project_dir: Path,
    *,
    config: ReferenceConfig | None = None,
) -> dict[str, Any]:
    """Pick best segment per speaker and write speaker_refs/ + reference_quality.json."""
    cfg = config or ReferenceConfig()
    project_dir = Path(project_dir)
    refs_dir = project_dir / "speaker_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)

    by_spk = _segments_by_spk(project_dir)
    speakers: dict[str, dict[str, Any]] = {}

    for spk, segments in sorted(by_spk.items()):
        best: tuple[float, Path, ReferenceValidation, int] | None = None
        for path, index, _start, _end in segments:
            validation = validate_reference(path, config=cfg)
            score = validation.duration_ms * validation.quality_score
            if best is None or score > best[0]:
                best = (score, path, validation, index)

        if best is None:
            continue

        _score, src_path, validation, source_index = best
        dest = refs_dir / f"spk{spk}.wav"
        shutil.copy2(src_path, dest)
        speakers[str(spk)] = {
            "bank_path": str(dest.relative_to(project_dir)),
            "source_cue_index": source_index,
            "duration_ms": validation.duration_ms,
            "quality_score": validation.quality_score,
            "adequate": validation.adequate,
        }

    payload = {"speakers": speakers}
    out = project_dir / "reference_quality.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def load_reference_overrides(project_dir: Path) -> dict[int, str]:
    path = project_dir / "reference_overrides.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): str(v) for k, v in data.items()}


def save_reference_override(project_dir: Path, cue_index: int, segment_path: str) -> None:
    overrides = load_reference_overrides(project_dir)
    overrides[cue_index] = segment_path
    payload = {str(k): v for k, v in overrides.items()}
    (project_dir / "reference_overrides.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def concatenate_adjacent_same_speaker(
    cue: Cue,
    cues: list[Cue],
    project_dir: Path,
    *,
    max_ms: int = 10_000,
    config: ReferenceConfig | None = None,
) -> Path | None:
    """Merge adjacent same-speaker segment WAVs up to max_ms for reference audio."""
    cfg = config or ReferenceConfig()
    project_dir = Path(project_dir)
    segments_dir = project_dir / "segments"
    by_index = {c.index: c for c in cues}
    if cue.index not in by_index:
        return None

    ordered = sorted(cues, key=lambda c: c.start_ms)
    pos = next(i for i, c in enumerate(ordered) if c.index == cue.index)

    selected: list[Cue] = [ordered[pos]]
    total_ms = cue.end_ms - cue.start_ms
    lo, hi = pos - 1, pos + 1

    while total_ms < cfg.min_ref_duration_ms and total_ms < max_ms:
        expanded = False
        if lo >= 0 and ordered[lo].spk == cue.spk:
            selected.insert(0, ordered[lo])
            total_ms += ordered[lo].end_ms - ordered[lo].start_ms
            lo -= 1
            expanded = True
        if hi < len(ordered) and ordered[hi].spk == cue.spk and total_ms < max_ms:
            selected.append(ordered[hi])
            total_ms += ordered[hi].end_ms - ordered[hi].start_ms
            hi += 1
            expanded = True
        if not expanded:
            break

    if total_ms < cfg.min_ref_duration_ms:
        return None

    paths = [segments_dir / segment_filename(c.index, c.to_sentence()) for c in selected]
    if not all(p.is_file() for p in paths):
        return None

    out_dir = project_dir / "speaker_refs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f".concat_{cue.index:04d}_spk{cue.spk}.wav"

    if len(paths) == 1:
        shutil.copy2(paths[0], out_path)
        return out_path

    ffmpeg = check_ffmpeg()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as list_file:
        for p in paths:
            list_file.write(f"file '{p.resolve()}'\n")
        list_path = list_file.name

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-c",
        "copy",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(list_path).unlink(missing_ok=True)
    if result.returncode != 0:
        logger.warning("ffmpeg concat failed: %s", result.stderr)
        return None
    return out_path


def resolve_reference(
    cue: Cue,
    project_dir: Path,
    *,
    config: ReferenceConfig | None = None,
    overrides: dict[int, str] | None = None,
) -> ResolvedReference:
    """Resolve voice-cloning reference with 4-level fallback hierarchy."""
    cfg = config or ReferenceConfig()
    project_dir = Path(project_dir)
    cues = _load_cues(project_dir)
    overrides = overrides if overrides is not None else load_reference_overrides(project_dir)

    if cue.index in overrides:
        override_path = project_dir / overrides[cue.index]
        validation = validate_reference(override_path, config=cfg)
        if validation.adequate:
            return ResolvedReference(
                path=override_path,
                rel_path=overrides[cue.index],
                source="manual_override",
                duration_ms=validation.duration_ms,
                quality_score=validation.quality_score,
            )
        raise ReferenceUnavailable(
            cue.spk,
            cue.index,
            f"manual_override_inadequate: {', '.join(validation.issues)}",
        )

    cue_segment = project_dir / "segments" / segment_filename(cue.index, cue.to_sentence())
    validation = validate_reference(cue_segment, config=cfg)
    if validation.adequate:
        return ResolvedReference(
            path=cue_segment,
            rel_path=str(cue_segment.relative_to(project_dir)),
            source="cue",
            duration_ms=validation.duration_ms,
            quality_score=validation.quality_score,
        )
    fallback_reason = (
        f"cue_segment_inadequate: {validation.duration_ms}ms, "
        f"issues={','.join(validation.issues)}"
    )

    bank = project_dir / "speaker_refs" / f"spk{cue.spk}.wav"
    if bank.is_file():
        bank_val = validate_reference(bank, config=cfg)
        if bank_val.adequate:
            return ResolvedReference(
                path=bank,
                rel_path=str(bank.relative_to(project_dir)),
                source="speaker_bank",
                fallback_reason=fallback_reason,
                duration_ms=bank_val.duration_ms,
                quality_score=bank_val.quality_score,
            )

    by_spk = _segments_by_spk(project_dir)
    longest: Path | None = None
    longest_ms = 0
    for path, _idx, start_ms, end_ms in by_spk.get(cue.spk, []):
        dur = end_ms - start_ms
        if dur > longest_ms:
            longest_ms = dur
            longest = path
    if longest is not None:
        long_val = validate_reference(longest, config=cfg)
        if long_val.adequate:
            return ResolvedReference(
                path=longest,
                rel_path=str(longest.relative_to(project_dir)),
                source="longest_same_speaker",
                fallback_reason=fallback_reason,
                duration_ms=long_val.duration_ms,
                quality_score=long_val.quality_score,
            )

    concat_path = concatenate_adjacent_same_speaker(cue, cues, project_dir, config=cfg)
    if concat_path is not None:
        concat_val = validate_reference(concat_path, config=cfg)
        if concat_val.adequate:
            return ResolvedReference(
                path=concat_path,
                rel_path=str(concat_path.relative_to(project_dir)),
                source="adjacent_concat",
                fallback_reason=fallback_reason,
                duration_ms=concat_val.duration_ms,
                quality_score=concat_val.quality_score,
            )

    raise ReferenceUnavailable(
        cue.spk,
        cue.index,
        f"no_adequate_reference for speaker {cue.spk}",
    )


def scan_cue_reference_status(
    cue: Cue,
    project_dir: Path,
    *,
    config: ReferenceConfig | None = None,
) -> dict[str, Any]:
    """Return reference resolution preview for a cue (for API/UI)."""
    cfg = config or ReferenceConfig()
    project_dir = Path(project_dir)
    cue_seg = project_dir / "segments" / segment_filename(cue.index, cue.to_sentence())
    cue_val = validate_reference(cue_seg, config=cfg)

    try:
        resolved = resolve_reference(cue, project_dir, config=cfg)
        if resolved.source == "cue":
            status = "adequate"
        else:
            status = "fallback"
        return {
            "index": cue.index,
            "spk": cue.spk,
            "status": status,
            "reference_source": resolved.source,
            "reference_path": resolved.rel_path,
            "fallback_reason": resolved.fallback_reason,
            "cue_segment_quality": cue_val.to_dict(),
            "reference_duration_ms": resolved.duration_ms,
            "reference_quality_score": resolved.quality_score,
        }
    except ReferenceUnavailable as exc:
        return {
            "index": cue.index,
            "spk": cue.spk,
            "status": "unavailable",
            "reference_source": None,
            "reference_path": None,
            "fallback_reason": exc.reason,
            "cue_segment_quality": cue_val.to_dict(),
            "reference_duration_ms": 0,
            "reference_quality_score": 0.0,
        }


def build_reference_quality_report(project_dir: Path, *, config: ReferenceConfig | None = None) -> dict[str, Any]:
    """Build per-cue and per-speaker reference quality report for modified cues."""
    project_dir = Path(project_dir)
    cfg = config or ReferenceConfig()

    bank_path = project_dir / "reference_quality.json"
    speakers: dict[str, Any] = {}
    if bank_path.is_file():
        speakers = json.loads(bank_path.read_text(encoding="utf-8")).get("speakers", {})

    cues_report: list[dict[str, Any]] = []
    unavailable: list[int] = []
    json_path = project_dir / "subtitles.json"
    if json_path.is_file():
        for cue in load_subtitles(json_path):
            if not cue.modified:
                continue
            entry = scan_cue_reference_status(cue, project_dir, config=cfg)
            cues_report.append(entry)
            if entry["status"] == "unavailable":
                unavailable.append(cue.index)

    same_spk_options: dict[str, list[dict[str, Any]]] = {}
    for spk, segments in _segments_by_spk(project_dir).items():
        options = []
        for path, index, start_ms, end_ms in segments:
            val = validate_reference(path, config=cfg)
            options.append(
                {
                    "cue_index": index,
                    "path": str(path.relative_to(project_dir)),
                    "duration_ms": end_ms - start_ms,
                    "quality_score": val.quality_score,
                    "adequate": val.adequate,
                }
            )
        same_spk_options[str(spk)] = sorted(options, key=lambda o: o["duration_ms"], reverse=True)

    return {
        "speakers": speakers,
        "cues": cues_report,
        "unavailable": unavailable,
        "same_speaker_segments": same_spk_options,
    }


from typing import Any