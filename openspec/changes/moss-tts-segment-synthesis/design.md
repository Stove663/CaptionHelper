## Context

CaptionHelper's pipeline produces per-sentence audio segments and diarized subtitles. Users edit subtitle text in the Web UI; only modified cues need re-synthesis. Timestamps and speaker IDs must stay fixed because they define the video timeline and which reference voice to clone.

[MOSS-TTS-v1.5](https://github.com/OpenMOSS/MOSS-TTS) supports zero-shot voice cloning via reference audio and duration control via the `tokens` generation parameter, aligning with our need to match each cue's time slot while preserving speaker voice from the original segment WAV.

## Goals / Non-Goals

**Goals:**

- Text-only subtitle editing (timestamps and speaker read-only in UI and API)
- Synthesize TTS only for cues where `text_edited != text_original`
- Clone speaker voice using that cue's original `segments/*.wav` as MOSS-TTS reference
- Target duration = `end_ms - start_ms` of the cue (converted to MOSS-TTS `tokens`)
- Output `tts_segments/{index:04d}_spk{spk}_{start}-{end}.wav` for each modified cue
- Unmodified cues: no TTS output; final audio assembly uses original `segments/` clip
- Web UI button + background job with progress (`synthesizing` status)
- `synthesis_manifest.json` recording per-cue synthesis metadata (model, tokens, reference path)

**Non-Goals:**

- Re-synthesizing unmodified segments
- Editing timestamps or re-assigning speakers in the editor
- Full video re-mux with replaced audio (future change)
- Fine-tuning MOSS-TTS on project data
- Real-time streaming TTS (use MOSS-TTS-Realtime separately if needed later)

## Decisions

### 1. MOSS-TTS model: MOSS-TTS-v1.5 (MossTTSDelay 8B)

**Choice:** `OpenMOSS-Team/MOSS-TTS-v1.5`

**Rationale:** Best documented voice cloning + `tokens` duration control in the [MOSS-TTS quickstart](https://github.com/OpenMOSS/MOSS-TTS). v1.5 improves cloning stability and punctuation-following prosody.

**Alternatives considered:**
- MOSS-TTS-Local-Transformer-v1.5: 48 kHz stereo but different API; defer unless stereo needed.
- MOSS-TTS-Nano: CPU-friendly but lower quality for voice cloning.

### 2. Voice reference: per-cue original segment WAV

**Choice:** `reference=[segments/0003_spk1_5200-8100.wav]` for cue index 3.

**Rationale:** Segment already contains the correct speaker's voice for that time slot; short-text cloning from segment audio is MOSS-TTS's intended use case.

**Speaker consistency:** If multiple modified cues share the same `spk`, each uses its own segment as reference (may differ in prosody but same speaker ID).

### 3. Duration control: tokens mapping + ffmpeg trim/pad

**Choice:**
1. Compute `target_duration_s = (end_ms - start_ms) / 1000`
2. Map to MOSS-TTS `tokens` via calibrated formula: `tokens = int(target_duration_s * TOKENS_PER_SECOND)` (default `TOKENS_PER_SECOND ≈ 25`, tunable)
3. Generate with `processor.build_user_message(text=text_edited, reference=[segment_wav], tokens=tokens)`
4. Post-process with ffmpeg: trim if over-duration, pad silence if under-duration to exact slot length

**Rationale:** MOSS-TTS `tokens` gives approximate duration control; ffmpeg ensures exact fit for timeline assembly.

### 4. Subtitle editor restriction

**Choice:** Frontend renders `start_ms`, `end_ms`, `spk` as read-only labels; API rejects PUT payloads that change `start_ms`, `end_ms`, or `spk` from stored values.

**Rationale:** User requirement; prevents desync between segments, video timeline, and TTS references.

### 5. Modification tracking update

**Choice:** `modified = (text_edited.strip() != text_original.strip())`; timestamp/speaker changes are not possible via API.

**Rationale:** Only text edits trigger TTS re-synthesis.

### 6. Synthesis job flow

```
User clicks "Synthesize" 
  → read modified_segments.json
  → for each modified cue:
      load reference segment WAV
      call MOSS-TTS with text_edited + reference + tokens
      post-process to exact duration
      write tts_segments/NNNN_spkX_start-end.wav
  → write synthesis_manifest.json
  → status: synthesis_ready
```

**Concurrency:** Process modified cues sequentially (GPU memory); batch_size=1.

### 7. MOSS-TTS integration module

```
src/caption_helper/tts/
├── __init__.py
├── moss_tts.py       # model load, generate()
├── duration.py       # ms → tokens mapping, ffmpeg trim/pad
└── synthesizer.py    # batch over modified_segments
```

**Lazy model loading:** Load MOSS-TTS on first synthesis request; keep in memory for session.

### 8. API additions

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/projects/{id}/synthesize` | Start TTS job for modified segments |
| GET | `/api/projects/{id}/synthesis-status` | Job progress, count done/total |

### 9. Project layout extension

```
<project>/
├── segments/           # original ASR clips (voice reference)
├── tts_segments/       # MOSS-TTS output for modified cues only
├── synthesis_manifest.json
└── ...
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 8B model VRAM (~16GB+) | Document GPU requirements; optional MOSS-TTS-Nano fallback flag |
| Token→duration mapping imprecise | Calibrate `TOKENS_PER_SECOND`; ffmpeg post-process to exact length |
| Long reference + short edited text | MOSS-TTS v1.5 handles this; use segment clip not full audio |
| MOSS-TTS install complexity | Document separate venv or optional `[tts]` extra in pyproject.toml |
| Synthesis slower than editing | Background job + progress bar; one project at a time |

## Migration Plan

1. Apply after `add-subtitle-editor-ui`
2. Update `add-subtitle-editor-ui` implementation to match text-only editor when both are applied
3. Delta specs in this change override subtitle-editor and subtitle-versioning requirements

## Open Questions

- Default `TOKENS_PER_SECOND` calibration value? _Start with 25, expose `--tokens-per-second` for tuning._
- Language tag for Chinese content? _Default `language="Chinese"` in `build_user_message`._
