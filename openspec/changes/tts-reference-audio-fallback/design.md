## Context

MOSS-TTS clones voice from a **reference WAV**. The current design uses each cue's own `segments/*.wav`. MOSS-TTS v1.5 explicitly improves **long-reference, short-text cloning** — a longer reference with shorter target text works better than a short reference.

Problems in lecture/meeting content:

| Issue | Example | Effect on cloning |
|-------|---------|-------------------|
| Too short | "好的" 0.4 s | Insufficient timbre capture |
| Low volume / noisy | distant mic, room echo | Unstable clone |
| Clipping | speaker too loud | Distorted reference |
| Cross-talk | two speakers in one cue | Wrong voice extracted |

Users typically replace 1–2 words in a sentence; the **cue segment** is usually adequate, but edge cases need automatic recovery.

## Goals / Non-Goals

**Goals:**

- Minimum reference duration default: **1.5 s** (configurable `--min-ref-duration-ms`)
- Per-speaker reference bank built automatically after ASR
- Automatic fallback before TTS; transparent logging in manifest
- UI warning on weak-reference cues before synthesis
- Manual override: user picks alternate same-speaker segment as reference
- Synthesis proceeds for cues with resolved fallback; fails only when speaker has zero adequate audio

**Non-Goals:**

- Manual audio recording for reference upload (future)
- Noise reduction / dereverb preprocessing (defer)
- Cross-speaker reference (never — always same `spk`)
- Re-segmenting ASR boundaries to fix short cues

## Decisions

### 1. Per-speaker reference bank

**Choice:** After ASR segment split, for each unique `spk`:

```
candidates = all segments where spk == N
score each: duration_ms * quality_score
pick highest → speaker_refs/spk{N}.wav
```

Also write `reference_quality.json`:

```json
{
  "speakers": {
    "0": {
      "bank_path": "speaker_refs/spk0.wav",
      "source_cue_index": 12,
      "duration_ms": 4200,
      "quality_score": 0.85
    }
  }
}
```

**Rationale:** One reliable long sample per speaker covers most short-cue fallbacks. MOSS-TTS handles long-ref/short-text well.

### 2. Reference quality scoring

**Choice:** Lightweight heuristics (no ML):

| Check | Threshold | Penalty |
|-------|-----------|---------|
| Duration | < 1500 ms | `inadequate` if no fallback |
| Peak amplitude | > 0.99 (clipping) | quality × 0.5 |
| RMS too low | < 0.01 | quality × 0.6 (quiet/noise) |
| Leading/trailing silence | > 60% of clip | quality × 0.7 |

`quality_score` ∈ [0, 1]. `adequate = duration_ms >= MIN_REF_MS AND quality_score >= 0.5`.

### 3. Fallback hierarchy

```
resolve_reference(cue):
  1. cue_segment = segments/{cue}.wav
     if adequate(cue_segment): return (cue_segment, "cue")

  2. bank = speaker_refs/spk{spk}.wav
     if exists and adequate(bank): return (bank, "speaker_bank")

  3. longest = max(segments where spk == cue.spk, key=duration)
     if adequate(longest): return (longest, "longest_same_speaker")

  4. concat = concatenate_adjacent_same_speaker(cue, max_ms=10000)
     if adequate(concat): return (concat, "adjacent_concat")

  5. raise ReferenceUnavailable(spk, cue.index)
```

**Adjacent concat:** Merge cue's segment with preceding/following same-speaker segments from `segments/` until ≥ 1.5 s or 10 s cap.

### 4. MOSS-TTS invocation unchanged

Reference path changes; API call shape stays:

```python
processor.build_user_message(text=text_edited, reference=[resolved_ref_path], ...)
```

MOSS-TTS uses long reference + short edited text — ideal for fallback bank.

### 5. Synthesis manifest extension

Per cue in `synthesis_manifest.json`:

```json
{
  "index": 3,
  "reference_source": "speaker_bank",
  "reference_path": "speaker_refs/spk1.wav",
  "reference_fallback_reason": "cue_segment_too_short: 420ms < 1500ms",
  "reference_duration_ms": 4200,
  "reference_quality_score": 0.85
}
```

### 6. Web UI

**Before synthesis:**
- Scan modified cues → `reference_quality.json` + per-cue validation
- Show badge: ✅ adequate / ⚠️ fallback will be used / ❌ no reference available
- Click ⚠️ cue → show which fallback will apply; optional dropdown to pick another same-speaker segment

**API:**
- `GET /api/projects/{id}/reference-quality` — per-cue and per-speaker status
- `PUT /api/projects/{id}/cues/{index}/reference` — manual override path

### 7. Failure handling

| Case | Behavior |
|------|----------|
| Fallback resolved | Synthesize; log fallback in manifest |
| No adequate ref for speaker | Mark cue `status: failed`; continue other cues; remux blocked if any failed (existing) |
| User override invalid (wrong spk) | HTTP 422 |

### 8. Integration point

Build speaker bank in `pipeline.process()` after segment split:

```
extract → transcribe → srt → split → build_speaker_reference_bank()
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Bank from different sentence → prosody mismatch | Same speaker timbre still captured; MOSS-TTS clones timbre not prosody |
| Adjacent concat includes other words | Acceptable for cloning; only used as reference not output |
| False positive "inadequate" | Configurable `--min-ref-duration-ms`; user manual override |
| Heuristic quality inaccurate | Conservative thresholds; user can override |

## Migration Plan

1. Apply after `funasr-video-subtitles-audio-split`; hook bank build into pipeline
2. Apply with `moss-tts-segment-synthesis` — replace direct segment reference with `resolve_reference()`
3. Existing projects: rebuild bank on next open or explicit `caption-helper build-refs`

## Open Questions

- Default `MIN_REF_MS`? _1500 ms based on MOSS-TTS short-text cloning guidance._
- Auto-retry with bank if cue-ref synthesis sounds bad? _Defer; v1 is pre-selection only._
