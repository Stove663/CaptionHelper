## REMOVED Requirements

### Requirement: ASR provider selection in Web UI

**Reason**: FunASR is the sole ASR backend; per-project provider selection is no longer a product feature.

**Migration**: Remove ASR provider toggle from upload form and editor; users always get FunASR transcription.

### Requirement: ASR provider reported by API

**Reason**: No multiple ASR providers to report or route.

**Migration**: Remove `asr_provider` from API request/response schemas, or stop exposing it in `GET /api/projects/{id}` responses.

### Requirement: CLI ASR provider flag

**Reason**: `--asr-provider` existed only to choose between FunASR and MOSS-Audio.

**Migration**: Remove `--asr-provider` from `caption-helper process`; scripts passing `--asr-provider moss-audio` must drop the flag (FunASR is implicit).
