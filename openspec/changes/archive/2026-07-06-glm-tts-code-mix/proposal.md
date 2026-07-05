## Why

CaptionHelper's primary TTS edit pattern is **zh-en code-mixed subtitles** (e.g. replacing a Chinese term with English while keeping surrounding Chinese). GLM-TTS advertises mixed-text support, but the current integration passes `use_phoneme=False` always and relies on post-hoc `fit_duration` in fixed-slot mode — which compresses English syllables more aggressively than MOSS-TTS (which has token duration hints). Users selecting GLM-TTS for mixed cues need phoneme-in where it helps and stronger natural-pace guidance where fixed-slot cannot preserve quality.

## What Changes

- Enable **GLM-TTS Phoneme-in** automatically for code-mixed cues (`is_code_mixed(text)`), with project-level override `glm_phoneme_mode: auto | on | off` (default `auto`)
- Add **mixed-text preprocessing** before GLM `text_normalize` (English word spacing, preserve acronym casing) for code-mixed cues
- Wire phoneme flag through the full GLM call chain: `load_models(use_phoneme)` → `TextFrontEnd` → `generate_long(use_phoneme)` → `g2p_infer`
- Record `phoneme_enabled` and `text_prep_applied` in `synthesis_manifest.json` per cue
- Extend **natural-pace UX** when `tts_provider=glm-tts`: provider-specific banner text, pre-synthesis warning on synthesize API, and README guidance that GLM-TTS lacks duration hints in fixed-slot mode
- Add unit tests for phoneme routing, text prep, and manifest fields

## Capabilities

### New Capabilities

- `glm-tts-code-mix`: Phoneme-in auto mode, mixed-text preprocessing, and GLM synthesis manifest metadata for code-mixed cues

### Modified Capabilities

- `timeline-sync-modes`: Provider-aware natural-pace recommendations when GLM-TTS is selected and code-mixed cues are at compression risk

## Impact

- **Code**: `tts/glm_tts.py`, new `tts/glm_text_prep.py` (or inline in `code_mix.py`), `tts/synthesizer.py`, `web/routes/projects.py` (compression-risk / synthesize preflight), `frontend/EditorPage.tsx`, `meta.json` schema (`glm_phoneme_mode`), tests
- **Runtime**: GLM-TTS `load_models` must be called with matching `use_phoneme` for model lifetime; may require separate `_GLMRuntime` cache keys for phoneme on/off
- **VRAM/latency**: Phoneme mode loads `G2P_zh` and config dicts; negligible vs full GLM-TTS load
- **Non-goals**: GLM-TTS_RL weights, per-cue English-aware reference selection, phoneme UI editor, MOSS-TTS behavior changes
