## Context

CaptionHelper currently supports two ASR backends: FunASR (default) and MOSS-Audio (optional `[moss-audio]` extra). MOSS-Audio integration added `moss_audio_transcribe.py`, ASR provider selection in UI/API/CLI, preflight checks, and OpenSpec capabilities `moss-audio-asr` and `asr-provider-selection`. MOSS-TTS (speech synthesis) is a separate concern and remains in the project.

## Goals / Non-Goals

**Goals:**

- Remove all MOSS-Audio ASR code, dependencies, tests, and documentation
- Simplify transcription to FunASR-only via existing `FunASRTranscriber`
- Remove ASR provider selection UX and API surface area
- Migrate legacy `meta.json` projects with `asr_provider: moss-audio` transparently to FunASR
- Delete obsolete OpenSpec capabilities on archive

**Non-Goals:**

- Removing MOSS-TTS or GLM-TTS synthesis providers
- Changing FunASR model defaults (still Fun-ASR-Nano-2512 + fsmn-vad + cam++)
- Adding a replacement second ASR backend
- Migrating or re-transcribing existing project audio automatically

## Decisions

### 1. Remove ASR provider selection entirely (not FunASR-only enum)

**Choice:** Delete `asr_provider` from user-facing API, UI, and CLI rather than keeping a frozen `funasr`-only field.

**Rationale:** A single-backend system does not need metadata, toggles, or validation for provider choice. Less surface area than retaining a dead field.

**Alternatives considered:**

| Approach | Verdict |
|----------|---------|
| Keep `asr_provider: funasr` in meta for future extensibility | Reject — YAGNI; can reintroduce when a second backend returns |
| Keep CLI `--asr-provider funasr` as no-op | Reject — confusing for users |

### 2. Legacy meta migration on read

**Choice:** When loading `ProjectMeta`, map `asr_provider: moss-audio` (or any unknown value) to FunASR behavior without failing; optionally rewrite `meta.json` to drop the field.

**Rationale:** Existing projects on disk should not break; users can manually rerun ASR if they want FunASR output.

### 3. Delete files rather than stub

**Choice:** Remove `moss_audio_transcribe.py`, `tests/test_moss_audio_transcribe.py`, and `[moss-audio]` extra completely.

**Rationale:** "彻底移除" — no dead code paths or lazy imports.

### 4. Simplify `transcribe.py` and `asr_preflight.py`

**Choice:** Remove `AsrProvider` literal union, `get_transcriber()` moss branch, and MOSS preflight. `get_transcriber()` may become a thin alias to `FunASRTranscriber` or be inlined at call sites.

**Rationale:** Matches single-backend reality.

### 5. Frontend cleanup

**Choice:** Remove ASR toggle from `HomePage.tsx` and `EditorPage.tsx`; remove `setAsrProvider` / related API types from `api.ts`.

**Rationale:** No selection means no UI controls.

### 6. OpenSpec archive outcome

**Choice:** On archive, delete `openspec/specs/moss-audio-asr/spec.md` and `openspec/specs/asr-provider-selection/spec.md`; merge deltas into `video-to-subtitles`, `web-ui-server`, `pipeline-stage-rerun`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Users relying on MOSS-Audio transcription quality | Document removal in README; they can stay on an older release or rerun with FunASR |
| Scripts using `--asr-provider moss-audio` break | **BREAKING** — noted in proposal; remove flag |
| Stale `asr_provider` in meta confuses debugging | Strip field on read/write after migration |
| Accidentally removing MOSS-TTS code | Scope review: only `moss_audio_*` and ASR provider paths |

## Migration Plan

1. Implement code removal and tests update
2. Run `uv lock` after removing `[moss-audio]` extra
3. Update README (remove MOSS-Audio install/ASR sections; keep MOSS-TTS docs)
4. Archive OpenSpec change to sync main specs
5. Rollback: revert commit; no data migration required beyond meta field

## Open Questions

- Whether to remove `asr_provider` from `ProjectMeta` dataclass entirely or keep internal default for one release — prefer full removal.
- Whether `GET /api/projects/{id}` should omit `asr_provider` immediately (**yes**) or return deprecated field — prefer omit.
