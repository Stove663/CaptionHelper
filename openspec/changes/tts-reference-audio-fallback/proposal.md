## Why

MOSS-TTS voice cloning uses each modified cue's `segments/*.wav` as reference audio. In lecture/meeting videos, individual cues can be **too short** (e.g., under 1 second) or **low quality** (noise, clipping, overlap) for reliable cloning. Without a fallback strategy, TTS output sounds wrong or synthesis fails silently. The pipeline needs automatic reference selection, per-speaker reference banks, and clear user feedback when no adequate reference exists.

## What Changes

- Build a **per-speaker reference bank** (`speaker_refs/spk{N}.wav`) after ASR from the longest clean segment per speaker
- **Validate** each cue's segment before TTS: minimum duration, clipping, silence ratio
- **Fallback hierarchy** when cue reference is inadequate:
  1. Cue's own segment (if passes validation)
  2. Per-speaker reference bank clip
  3. Longest same-speaker segment in the project
  4. Concatenated adjacent same-speaker segments (up to 10 s cap)
- Record `reference_source` and `reference_fallback_reason` in `synthesis_manifest.json`
- **Web UI warnings** before synthesis: flag cues with weak reference; allow manual override to pick another same-speaker segment
- **Block synthesis** for a cue only when no reference ≥ minimum duration exists for that speaker

## Capabilities

### New Capabilities

- `speaker-reference-bank`: Build and store per-speaker voice reference clips after ASR
- `reference-audio-validation`: Score segment quality and duration; detect inadequate references
- `reference-fallback-selection`: Automatic fallback chain and manual override for TTS reference audio

### Modified Capabilities

- `moss-tts-synthesis`: Use resolved reference (not always cue segment); record fallback metadata in manifest

## Impact

- **New artifacts**: `speaker_refs/spk0.wav`, `reference_quality.json` per project
- **New code**: `src/caption_helper/tts/reference.py` (validate, fallback, bank builder)
- **ASR pipeline hook**: build speaker reference bank after segment split
- **Web UI**: reference quality indicators on modified cues; optional manual reference picker
- **Depends on**: `funasr-video-subtitles-audio-split`, `moss-tts-segment-synthesis`
