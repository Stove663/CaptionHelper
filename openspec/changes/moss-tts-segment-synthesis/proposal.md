## Why

After users correct ASR subtitle text in the Web UI, modified segments need new speech audio that matches the original speaker's voice and fits the existing time slot. [MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS) provides zero-shot voice cloning and token-level duration control, making it the right engine to re-synthesize only the edited cues while preserving speaker identity and timing constraints from the ASR pipeline.

Additionally, the subtitle editor must restrict edits to text only — timestamps and speaker IDs are determined by ASR and must remain fixed so segment boundaries and voice references stay consistent for TTS.

## What Changes

- **Restrict subtitle editor** to text-only editing; timestamps and speaker labels are read-only
- Integrate [MOSS-TTS-v1.5](https://github.com/OpenMOSS/MOSS-TTS) for per-segment TTS synthesis on modified cues only
- Use original segment WAV (`segments/`) as voice-cloning reference per speaker
- Control output duration to match cue time slot (`end_ms - start_ms`) via MOSS-TTS `tokens` parameter and post-processing trim/pad
- Store synthesized audio in `tts_segments/` separate from original `segments/`
- Add Web UI "Synthesize modified segments" action and API endpoint with job progress
- Update `subtitle-versioning`: `modified` flag triggers only on text changes (not timestamp/speaker)

## Capabilities

### New Capabilities

- `moss-tts-synthesis`: Voice-cloned TTS re-synthesis for modified subtitle segments using MOSS-TTS with duration matching

### Modified Capabilities

- `subtitle-editor`: Remove timestamp and speaker editing; text-only inline editing with read-only time/speaker display
- `subtitle-versioning`: `modified` flag applies only when `text_edited` differs from `text_original`; timestamp and speaker are immutable after ASR

## Impact

- **New dependencies**: MOSS-TTS (`OpenMOSS/MOSS-TTS`), `transformers>=5.0`, `torchaudio`; large model download (~8B MOSS-TTS-v1.5)
- **GPU required**: MOSS-TTS-v1.5 inference needs CUDA; CPU fallback documented but slow
- **New code**: `src/caption_helper/tts/` (MOSS-TTS wrapper, duration mapping, batch synthesizer)
- **New API**: `POST /api/projects/{id}/synthesize`, `GET /api/projects/{id}/synthesis-status`
- **New artifacts per project**: `tts_segments/`, `synthesis_manifest.json`
- **Depends on**: `add-subtitle-editor-ui` (editor, versioning), `funasr-video-subtitles-audio-split` (segments)
