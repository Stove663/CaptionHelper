from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from caption_helper.split import segment_filename
from caption_helper.subtitles_json import Cue, load_subtitles
from caption_helper.tts.code_mix import detect_language_mode, is_code_mixed
from caption_helper.tts.compression_risk import SYNC_MODE_FIXED, SYNC_MODE_NATURAL
from caption_helper.tts.duration import fit_duration, ms_to_tokens, wav_duration_ms
from caption_helper.tts.engine import TTSEngine
from caption_helper.tts.moss_tts import MossTTSConfig, MossTTSEngine
from caption_helper.tts.preflight import DEFAULT_MODEL, get_gpu_info
from caption_helper.tts.reference import (
    ReferenceConfig,
    ReferenceUnavailable,
    SEGMENT_RE,
    build_reference_quality_report,
    resolve_reference,
)

logger = logging.getLogger(__name__)


@dataclass
class CueSynthesisRecord:
    index: int
    spk: int
    text_edited: str
    reference_segment: str
    target_duration_ms: int
    tokens: int | None = None
    sync_mode: str = SYNC_MODE_FIXED
    slot_duration_ms: int = 0
    actual_duration_ms: int | None = None
    delta_ms: int = 0
    code_mixed: bool = False
    language_mode: str = "Chinese"
    reference_source: str | None = None
    reference_path: str | None = None
    reference_fallback_reason: str | None = None
    reference_duration_ms: int = 0
    reference_quality_score: float = 0.0
    output_path: str | None = None
    status: str = "pending"
    error: str | None = None


@dataclass
class SynthesisResult:
    model: str
    model_id: str = ""
    tts_provider: str = "moss-tts"
    sync_mode: str = SYNC_MODE_FIXED
    gpu_name: str | None = None
    peak_vram_mb: int = 0
    fallback_count: int = 0
    cues: list[CueSynthesisRecord] = field(default_factory=list)
    completed: int = 0
    total: int = 0
    failed: int = 0
    skipped: int = 0

    def to_manifest(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "model_id": self.model_id or self.model,
            "tts_provider": self.tts_provider,
            "sync_mode": self.sync_mode,
            "gpu_name": self.gpu_name,
            "peak_vram_mb": self.peak_vram_mb,
            "fallback_count": self.fallback_count,
            "completed": self.completed,
            "total": self.total,
            "failed": self.failed,
            "skipped": self.skipped,
            "cues": [asdict(c) for c in self.cues],
        }


def _load_modified_segments(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "modified_segments.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _output_path(project_dir: Path, entry: dict[str, Any]) -> Path:
    cue = Cue(
        index=int(entry["index"]),
        spk=int(entry["spk"]),
        start_ms=int(entry["start_ms"]),
        end_ms=int(entry["end_ms"]),
        text_original=str(entry.get("text_original", "")),
        text_edited=str(entry["text_edited"]),
    )
    name = segment_filename(cue.index, cue.to_sentence())
    return project_dir / "tts_segments" / name


def _entry_to_cue(entry: dict[str, Any]) -> Cue:
    return Cue(
        index=int(entry["index"]),
        spk=int(entry["spk"]),
        start_ms=int(entry["start_ms"]),
        end_ms=int(entry["end_ms"]),
        text_original=str(entry.get("text_original", "")),
        text_edited=str(entry["text_edited"]),
    )


def _reference_transcript(project_dir: Path, cue: Cue, resolved_rel_path: str) -> str:
    """Best-effort transcript for the resolved reference clip (GLM-TTS prompt text)."""
    if resolved_rel_path.endswith(segment_filename(cue.index, cue.to_sentence())):
        return cue.text_original
    name = Path(resolved_rel_path).name
    match = SEGMENT_RE.match(name)
    if match:
        ref_index = int(match.group(1))
        for loaded in load_subtitles(project_dir / "subtitles.json"):
            if loaded.index == ref_index:
                return loaded.text_original
    return cue.text_original


def synthesize_modified_segments(
    project_dir: Path,
    *,
    engine: TTSEngine | None = None,
    config: MossTTSConfig | None = None,
    ref_config: ReferenceConfig | None = None,
    sync_mode: str = SYNC_MODE_FIXED,
    tts_provider: str = "moss-tts",
    on_progress: Callable[[int, int], None] | None = None,
    skip_unavailable: bool = False,
) -> SynthesisResult:
    """Synthesize TTS for all modified cues in a project directory."""
    project_dir = Path(project_dir)
    cfg = config or (engine.config if engine else MossTTSConfig())
    ref_cfg = ref_config or ReferenceConfig()
    tts_engine = engine or MossTTSEngine(cfg)
    modified = _load_modified_segments(project_dir)
    tts_dir = project_dir / "tts_segments"
    tts_dir.mkdir(parents=True, exist_ok=True)
    natural_pace = sync_mode == SYNC_MODE_NATURAL

    gpu = get_gpu_info()
    result = SynthesisResult(
        model=cfg.model or DEFAULT_MODEL,
        model_id=cfg.model or DEFAULT_MODEL,
        tts_provider=tts_provider,
        sync_mode=sync_mode,
        gpu_name=gpu.name,
        total=len(modified),
    )
    if not modified:
        _write_manifest(project_dir, result)
        return result

    tts_engine.reset_vram_stats()

    for idx, entry in enumerate(modified):
        cue = _entry_to_cue(entry)
        target_ms = cue.end_ms - cue.start_ms
        tokens = None if natural_pace else ms_to_tokens(target_ms, tokens_per_second=cfg.tokens_per_second)
        out_path = _output_path(project_dir, entry)
        text = cue.text_edited
        lang_mode = detect_language_mode(text)
        record = CueSynthesisRecord(
            index=cue.index,
            spk=cue.spk,
            text_edited=text,
            reference_segment=str(entry.get("segment_path", "")),
            target_duration_ms=target_ms,
            tokens=tokens,
            sync_mode=sync_mode,
            slot_duration_ms=target_ms,
            code_mixed=is_code_mixed(text),
            language_mode=lang_mode,
            output_path=str(out_path.relative_to(project_dir)),
        )

        try:
            resolved = resolve_reference(cue, project_dir, config=ref_cfg)
            record.reference_source = resolved.source
            record.reference_path = resolved.rel_path
            record.reference_fallback_reason = resolved.fallback_reason
            record.reference_duration_ms = resolved.duration_ms
            record.reference_quality_score = resolved.quality_score
            if resolved.source != "cue":
                result.fallback_count += 1

            raw_path = tts_dir / f".raw_{out_path.name}"
            reference_text = _reference_transcript(project_dir, cue, resolved.rel_path)
            tts_engine.synthesize(
                text,
                resolved.path,
                tokens,
                output_path=raw_path,
                reference_text=reference_text,
            )
            if natural_pace:
                actual_ms = wav_duration_ms(raw_path)
                record.actual_duration_ms = actual_ms
                record.delta_ms = actual_ms - target_ms
                raw_path.replace(out_path)
            else:
                fit_duration(raw_path, target_ms, output_path=out_path)
                record.actual_duration_ms = target_ms
                record.delta_ms = 0
                raw_path.unlink(missing_ok=True)
            record.status = "success"
            result.completed += 1
        except ReferenceUnavailable as exc:
            if skip_unavailable:
                record.status = "skipped"
                record.error = str(exc)
                result.skipped += 1
            else:
                record.status = "failed"
                record.error = str(exc)
                result.failed += 1
        except Exception as exc:
            logger.exception("TTS failed for cue %s", entry.get("index"))
            record.status = "failed"
            record.error = str(exc)
            result.failed += 1
        finally:
            tts_engine.clear_cuda_cache()

        result.cues.append(record)
        result.peak_vram_mb = tts_engine.peak_vram_mb
        if on_progress:
            on_progress(idx + 1, len(modified))

    _write_manifest(project_dir, result)
    return result


def pre_synthesis_reference_scan(project_dir: Path, *, ref_config: ReferenceConfig | None = None) -> dict[str, Any]:
    return build_reference_quality_report(project_dir, config=ref_config)


def _write_manifest(project_dir: Path, result: SynthesisResult) -> None:
    path = project_dir / "synthesis_manifest.json"
    path.write_text(
        json.dumps(result.to_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_synthesis_manifest(project_dir: Path) -> dict[str, Any] | None:
    path = Path(project_dir) / "synthesis_manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
