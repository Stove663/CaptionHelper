from dataclasses import dataclass


@dataclass(frozen=True)
class Sentence:
    """One diarized subtitle sentence from FunASR sentence_info."""

    text: str
    spk: int
    start: int  # milliseconds
    end: int  # milliseconds

    @property
    def duration_ms(self) -> int:
        return self.end - self.start
