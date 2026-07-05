## Why

The Web UI currently assumes a single TTS backend. Users want to choose between the existing MOSS-TTS flow and a new [GLM-TTS](https://github.com/zai-org/GLM-TTS) option depending on voice quality, latency, and model availability. Some projects may work better with MOSS-TTS's existing voice-cloning and duration-control behavior, while others may benefit from GLM-TTS as an alternative synthesis engine.

A per-project TTS selector in the Web UI lets users pick the synthesis backend before they trigger subtitle re-synthesis, without changing the rest of the caption workflow.

## What Changes

- Add a per-project TTS provider selection in the Web UI with `MOSS-TTS` and `GLM-TTS`
- Persist the selected provider in project metadata so synthesis and rebuild jobs use the same backend consistently
- Route synthesis requests through the chosen provider instead of hard-coding MOSS-TTS
- Keep the existing MOSS-TTS flow as the default option for backward compatibility
- Add GLM-TTS integration requirements for model invocation, input/output audio artifacts, and failure handling

## Capabilities

### New Capabilities

- `tts-provider-selection`: Web UI and API support for choosing the active TTS backend per project
- `glm-tts-synthesis`: GLM-TTS-based subtitle re-synthesis for edited cues

### Modified Capabilities

- `moss-tts-synthesis`: Make MOSS-TTS one selectable provider rather than the only synthesis path
- `subtitle-editor` or `web-ui-server`: Expose provider selection in project controls before synthesis

## Impact

- **Project metadata**: store `tts_provider` or equivalent selection in `meta.json`
- **Web UI**: add a provider dropdown or radio group in the editor/rebuild flow
- **API**: accept and return the active TTS provider in project detail and synthesis endpoints
- **Pipeline**: dispatch synthesis jobs to the selected backend while keeping output artifacts compatible with the existing post-processing flow
- **Depends on**: `add-subtitle-editor-ui` and `moss-tts-segment-synthesis`
