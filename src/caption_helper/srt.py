from pathlib import Path

from caption_helper.models import Sentence


def ms_to_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp HH:MM:SS,mmm."""
    if ms < 0:
        raise ValueError(f"timestamp must be non-negative, got {ms}")
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_cue_text(sentence: Sentence) -> str:
    return f"[说话人 {sentence.spk}] {sentence.text}"


def write_srt(sentences: list[Sentence], output_path: Path) -> None:
    """Write diarized sentences to an SRT file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = []
    for index, sentence in enumerate(sentences, start=1):
        start = ms_to_srt_timestamp(sentence.start)
        end = ms_to_srt_timestamp(sentence.end)
        text = format_cue_text(sentence)
        blocks.append(f"{index}\n{start} --> {end}\n{text}")

    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
