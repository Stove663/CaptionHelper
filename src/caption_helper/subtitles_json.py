from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from caption_helper.models import Sentence
from caption_helper.split import segment_filename
from caption_helper.srt import write_srt


@dataclass
class Cue:
    index: int
    spk: int
    start_ms: int
    end_ms: int
    text_original: str
    text_edited: str
    modified: bool = False

    def to_sentence(self) -> Sentence:
        return Sentence(text=self.text_edited, spk=self.spk, start=self.start_ms, end=self.end_ms)


def cues_from_sentences(sentences: list[Sentence]) -> list[Cue]:
    cues: list[Cue] = []
    for index, sentence in enumerate(sentences, start=1):
        cues.append(
            Cue(
                index=index,
                spk=sentence.spk,
                start_ms=sentence.start,
                end_ms=sentence.end,
                text_original=sentence.text,
                text_edited=sentence.text,
                modified=False,
            )
        )
    return cues


def compute_modified(cue: Cue) -> bool:
    return cue.text_edited.strip() != cue.text_original.strip()


def load_subtitles(path: Path) -> list[Cue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Cue(**item) for item in data["cues"]]


def save_subtitles(path: Path, cues: list[Cue]) -> None:
    for cue in cues:
        cue.modified = compute_modified(cue)
    payload = {"cues": [asdict(c) for c in cues]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_srt_from_cues(cues: list[Cue], output_path: Path) -> None:
    write_srt([c.to_sentence() for c in cues], output_path)


def validate_save_request(existing: list[Cue], submitted: list[dict[str, Any]]) -> list[Cue]:
    by_index = {c.index: c for c in existing}
    updated: list[Cue] = []
    for item in submitted:
        index = int(item["index"])
        if index not in by_index:
            raise ValueError(f"Unknown cue index: {index}")
        orig = by_index[index]
        start_ms = int(item.get("start_ms", orig.start_ms))
        end_ms = int(item.get("end_ms", orig.end_ms))
        spk = int(item.get("spk", orig.spk))
        if start_ms != orig.start_ms or end_ms != orig.end_ms:
            raise ValueError("Timestamps are immutable")
        if spk != orig.spk:
            raise ValueError("Speaker is immutable")
        if end_ms < start_ms:
            raise ValueError(f"Cue {index}: end_ms must be >= start_ms")
        text_edited = str(item.get("text_edited", item.get("text", orig.text_edited)))
        updated.append(
            Cue(
                index=index,
                spk=spk,
                start_ms=start_ms,
                end_ms=end_ms,
                text_original=orig.text_original,
                text_edited=text_edited,
            )
        )
    updated.sort(key=lambda c: c.index)
    return updated


def generate_modified_segments(project_dir: Path, cues: list[Cue]) -> list[dict[str, Any]]:
    segments_dir = project_dir / "segments"
    modified: list[dict[str, Any]] = []
    for cue in cues:
        if not cue.modified:
            continue
        segment_path = segments_dir / segment_filename(cue.index, cue.to_sentence())
        modified.append(
            {
                "index": cue.index,
                "spk": cue.spk,
                "text_original": cue.text_original,
                "text_edited": cue.text_edited,
                "start_ms": cue.start_ms,
                "end_ms": cue.end_ms,
                "segment_path": str(segment_path.relative_to(project_dir)),
            }
        )
    out = project_dir / "modified_segments.json"
    out.write_text(json.dumps(modified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return modified


def initialize_subtitle_files(project_dir: Path, sentences: list[Sentence]) -> None:
    cues = cues_from_sentences(sentences)
    original_srt = project_dir / "subtitles_original.srt"
    edited_srt = project_dir / "subtitles_edited.srt"
    json_path = project_dir / "subtitles.json"

    write_srt_from_cues(cues, original_srt)
    shutil.copy2(original_srt, edited_srt)
    save_subtitles(json_path, cues)
    generate_modified_segments(project_dir, cues)
