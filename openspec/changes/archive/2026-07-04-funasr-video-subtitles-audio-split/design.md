## Context

CaptionHelper is a greenfield Python project. The user wants a pipeline that takes a video file and produces diarized subtitles (SRT) plus per-segment audio clips. FunASR provides the required stack: Fun-ASR-Nano for multilingual ASR with built-in punctuation, fsmn-vad for long-audio segmentation, and cam++ for speaker diarization — all composable via a single `AutoModel` call per the [FunASR tutorial](https://modelscope.github.io/FunASR/zh/tutorial.html).

Video demuxing and audio cutting are outside FunASR's scope; ffmpeg handles both reliably.

## Goals / Non-Goals

**Goals:**

- Single CLI command: `caption-helper process <video>` → SRT + full WAV + segment WAVs
- Speaker-labeled SRT entries using cam++ `spk` IDs (e.g., `[说话人 0]`)
- Timestamps derived from FunASR `sentence_info` (`start`/`end` in milliseconds)
- Mono 16 kHz WAV extraction (FunASR's expected input format)
- Sensible defaults for model hub (ModelScope for China, configurable `hub` flag)
- Reusable Python modules so pipeline steps can be composed or tested independently

**Non-Goals:**

- Real-time / streaming transcription (use paraformer-zh-streaming separately)
- Video re-encoding or hard-subtitle burning
- Speaker name enrollment / voice-print matching (numeric speaker IDs only)
- Web UI or API server (CLI only for v1)
- Multi-file batch queue with parallelism (single file per invocation)

## Decisions

### 1. ASR stack: Fun-ASR-Nano + fsmn-vad + cam++

**Choice:** `AutoModel(model="FunAudioLLM/Fun-ASR-Nano-2512", vad_model="fsmn-vad", spk_model="cam++")`

**Rationale:** Fun-ASR-Nano outputs punctuation natively (no separate `punc_model`), supports 31 languages, and returns `sentence_info` with per-sentence `spk`, `start`, `end`, and `text`. cam++ integrates without extra punctuation model — simpler than Paraformer + ct-punc + cam++.

**Alternatives considered:**
- Paraformer-zh + ct-punc + cam++: Chinese-only, requires punctuation model; rejected for narrower language support.
- SenseVoice + cam++: Faster but emotion/event tags add post-processing overhead; rejected unless user needs emotion.

### 2. Audio extraction: ffmpeg subprocess

**Choice:** `ffmpeg -i <video> -vn -ac 1 -ar 16000 -f wav <output.wav>`

**Rationale:** Universal codec support, no extra Python deps, industry standard.

**Alternatives considered:**
- moviepy / pydub: Heavier deps, ffmpeg still required underneath.

### 3. SRT generation from `sentence_info`

**Choice:** Map each `sentence_info` entry to one SRT cue. Cue text format: `[说话人 {spk}] {text}`. Timestamps: convert ms → `HH:MM:SS,mmm` SRT format.

**Rationale:** One cue per diarized sentence matches user expectation; speaker prefix is human-readable and matches FunASR tutorial examples.

### 4. Audio segment splitting: ffmpeg per segment

**Choice:** For each SRT entry, run `ffmpeg -i <full.wav> -ss <start> -to <end> -c copy <segment.wav>` (or re-encode if copy fails on WAV).

**Rationale:** Precise time-based cutting without loading full audio into memory. Segment filenames: `{index:04d}_spk{spk}_{start_ms}-{end_ms}.wav`.

**Alternatives considered:**
- soundfile/numpy slicing: Loads full audio; acceptable for short files but ffmpeg scales better.

### 5. Output layout

```
<video_stem>_output/
├── audio.wav          # extracted full audio
├── subtitles.srt      # diarized SRT
└── segments/
    ├── 0001_spk0_880-5195.wav
    ├── 0002_spk1_5200-8100.wav
    └── ...
```

**Rationale:** Colocated artifacts, predictable naming, easy to inspect.

### 6. Project structure

```
src/caption_helper/
├── __init__.py
├── cli.py              # argparse / click entry
├── extract.py          # ffmpeg video → wav
├── transcribe.py       # FunASR AutoModel wrapper
├── srt.py              # sentence_info → SRT writer
├── split.py            # wav + timestamps → segment files
└── pipeline.py         # orchestrates full flow
```

**Rationale:** Thin modules per concern; `pipeline.py` wires them for CLI.

### 7. Package management: uv + pyproject.toml

**Choice:** Use `uv` with `pyproject.toml`; declare `funasr`, `torch`, `soundfile` as dependencies; document ffmpeg as system prerequisite.

### 8. Device selection

**Choice:** Default `device="cuda:0"` if CUDA available, else `cpu`. Expose `--device` CLI flag.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large model download on first run (~GB) | Document expected download; support `hub="hf"` for overseas users |
| GPU OOM on long videos | Set `vad_kwargs={"max_single_segment_time": 30000}`; expose `--max-segment-s` |
| ffmpeg not installed | Check at startup; print install instructions |
| Speaker IDs are anonymous numbers | Document limitation; future: optional speaker rename map |
| Fun-ASR-Nano requires `trust_remote_code=True` | Pin model version; document security implication |
| Segment boundary clicks/pops | Use small padding or ffmpeg `afade` if reported; defer to v2 |

## Migration Plan

N/A — greenfield project. First release is initial install:

1. `uv sync`
2. Ensure ffmpeg on PATH
3. `caption-helper process meeting.mp4`

## Open Questions

- Default language parameter for Fun-ASR-Nano: auto-detect vs explicit `--language 中文`?
- Should segment audio be re-encoded to 16 kHz mono or preserve source format?
- Minimum segment duration filter (skip sub-200ms segments)?

_Resolved defaults for v1: `--language` defaults to `中文`; segments output as 16 kHz mono WAV; no minimum duration filter._
