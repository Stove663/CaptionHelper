## Context

CaptionHelper's transcription layer is a single `Transcriber` class in `transcribe.py` wrapping FunASR (`Fun-ASR-Nano-2512` + `fsmn-vad` + `cam++`). It produces `Sentence` records (`text`, `spk`, `start`, `end`) consumed by SRT generation, audio splitting, and the speaker reference bank. The Web UI and CLI both call `pipeline.process()` / background ASR jobs with no provider choice.

[MOSS-Audio](https://github.com/OpenMOSS/MOSS-Audio) is an audio understanding model family (4B/8B, Instruct/Thinking) with strong ASR and timestamp ASR benchmarks. It is invoked via prompt-based inference (`infer.py`) rather than FunASR's `sentence_info` API. Models are available on [ModelScope](https://modelscope.cn/models/openmoss/MOSS-Audio-4B-Instruct) and HuggingFace, aligning with the project's `china-mirror-defaults` policy.

The TTS provider selection change (`glm-tts-webui-selection`) established the pattern: `meta.json` field, `PUT` API, editor toggle, job dispatch. ASR selection should mirror that shape (`asr_provider: "funasr" | "moss-audio"`).

## Goals / Non-Goals

**Goals:**

- Per-project ASR provider selection (`funasr` | `moss-audio`) persisted in `meta.json` and exposed via project APIs
- Web UI toggle at upload and in editor; selection survives reload
- ASR jobs (initial upload and `rerun/asr`) route to the stored provider
- `MossAudioTranscriber` producing `list[Sentence]` compatible with existing downstream steps
- Default model `MOSS-Audio-4B-Instruct`; weights from ModelScope by default
- Optional `[moss-audio]` extra with lazy import so FunASR-only installs keep working
- CLI `--asr-provider` flag on `caption-helper process`
- Record active provider in project metadata / transcription manifest for debugging

**Non-Goals:**

- Running FunASR and MOSS-Audio concurrently on the same GPU (jobs remain serialized)
- Per-segment provider mixing within one project
- Exposing all four MOSS-Audio variants (4B/8B × Instruct/Thinking) in the UI — ship one default, allow env/config override
- Replacing FunASR as the CLI default
- Bundling MOSS-Audio weights in the repo
- MOSS-Audio general audio QA, music analysis, or non-ASR features

## Decisions

### 1. Provider identifier and storage

**Choice:** Store `asr_provider: "funasr" | "moss-audio"` in `meta.json` via `ProjectMeta.asr_provider`, default `"funasr"`.

**Rationale:** Matches `tts_provider` / `sync_mode` patterns; backward compatible via `setdefault` on read.

**Alternatives considered:**

| Approach | Verdict |
|----------|---------|
| Server-global default only | Reject — users need per-project choice |
| Store in transcription artifact only | Reject — selection must exist before first ASR run |

### 2. Shared transcriber contract

**Choice:** Introduce a small protocol / ABC `BaseTranscriber` with `transcribe(audio_path: str) -> list[Sentence]`. Existing `Transcriber` becomes `FunASRTranscriber`; new `MossAudioTranscriber` implements the same surface. Factory `get_transcriber(provider, config)` used by `pipeline.py`, CLI, and `JobRunner`.

**Rationale:** Downstream code (`write_srt`, `split_segments`, reference bank) stays unchanged.

### 3. MOSS-Audio integration strategy

**Choice:** Vendor MOSS-Audio as optional `[moss-audio]` extra. Lazy-import inside `MossAudioTranscriber`. Load `openmoss/MOSS-Audio-4B-Instruct` from ModelScope when `hub` is unset; respect `HF_ENDPOINT` / hf-mirror bootstrap and `--hub hf` for HuggingFace.

Inference flow:

1. Load model once per process (same caching pattern as FunASR `Transcriber._load_model`)
2. Send audio with a fixed timestamp-ASR prompt (e.g. Chinese: transcribe with sentence-level timestamps and speaker labels)
3. Parse model text output into `Sentence` records via `sentences_from_moss_audio_output()`

**Speaker diarization:** MOSS-Audio does not expose FunASR-style `sentence_info`. Use a structured-output prompt requesting JSON lines `{spk, start_ms, end_ms, text}`. On parse failure, fall back to a single-speaker transcript (`spk=0`) with timestamps from MOSS-Audio timestamp ASR mode if available, and surface a warning in logs. Document that FunASR remains preferable when native diarization is critical.

**Rationale:** Keeps MOSS-Audio path self-contained without pulling cam++ as a hybrid dependency in v1.

**Alternatives considered:**

| Approach | Verdict |
|----------|---------|
| Hybrid: MOSS-Audio text + cam++ diarization only | Defer — adds coupling; revisit if prompt diarization is insufficient |
| Fork pipeline per provider | Reject — duplicates extract/split/SRT logic |
| SGLang serving for MOSS-Audio | Defer — in-process load matches current FunASR deployment model |

### 4. Web UI and API

**Choice:**

- Toggle group on `HomePage` upload form and `EditorPage` toolbar: FunASR / MOSS-Audio
- `PUT /api/projects/{id}/asr-provider` validates enum and writes meta
- `GET /api/projects/{id}` returns `asr_provider`
- `POST /api/projects` (upload) accepts optional `asr_provider` in multipart metadata
- Disable toggle while ASR is in progress (`extracting`, `transcribing`, `splitting`)

**Rationale:** Mirrors TTS provider UX; no per-job override needed.

### 5. CLI

**Choice:** Add `--asr-provider {funasr,moss-audio}` to `caption-helper process`, default `funasr`. Reuse existing `--hub` for model source.

### 6. Preflight and resource requirements

**Choice:** Before MOSS-Audio ASR (web upload and CLI), check CUDA availability and minimum VRAM (~10 GB for 4B-Instruct with bf16). Return clear error when `[moss-audio]` extra is not installed. FunASR preflight unchanged.

**Rationale:** MOSS-Audio 4B is heavier than Fun-ASR-Nano; fail fast with actionable messages.

### 7. Long audio handling

**Choice:** Chunk audio longer than a configurable max duration (default 5 minutes) with ffmpeg, run MOSS-Audio per chunk, offset timestamps when merging `Sentence` lists. FunASR continues using VAD segmentation.

**Rationale:** MOSS-Audio context limits differ from FunASR VAD; chunking is a well-understood pattern.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| MOSS-Audio prompt diarization less reliable than FunASR cam++ | Document trade-off; keep FunASR default; log warnings on parse fallback |
| MOSS-Audio deps conflict with FunASR torch pins | Separate optional extra; lazy import; document install |
| Large model download (~9 GB for 4B) | ModelScope + hf-mirror defaults; download on first use only |
| Structured JSON parse fragility from LLM output | Robust parser with regex/JSONL fallback; unit tests on sample outputs |
| Switching provider on rerun discards downstream work | Existing ASR rerun confirmation already covers this |
| CPU-only inference impractically slow | Preflight requires CUDA for `moss-audio`; allow override via env for dev only |

## Migration Plan

1. Ship metadata + API + UI — existing projects default to `funasr`, no migration script.
2. Implement `MossAudioTranscriber` and factory dispatch in pipeline / jobs.
3. Document `[moss-audio]` install and ModelScope checkpoint download in README.
4. Rollback: set `asr_provider` back to `funasr` via UI or meta edit.

## Open Questions

- Whether prompt-based speaker diarization quality is acceptable for multi-speaker meeting video — validate on real project samples and consider cam++ hybrid in a follow-up.
- Exact minimum VRAM for `MOSS-Audio-4B-Instruct` on T4 — tune preflight after empirical testing.
- Optimal timestamp ASR prompt wording and output format from upstream MOSS-Audio examples — align with `infer.py` defaults when implementing.
- Pin MOSS-Audio git tag vs. PyPI/git dependency for reproducibility.
