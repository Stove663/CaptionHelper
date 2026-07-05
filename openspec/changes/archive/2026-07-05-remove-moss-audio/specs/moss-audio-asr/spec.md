## REMOVED Requirements

### Requirement: MOSS-Audio transcription backend

**Reason**: MOSS-Audio ASR backend removed from the project.

**Migration**: Use FunASR (default). Re-run ASR on any projects previously processed with MOSS-Audio if different transcription is needed.

### Requirement: MOSS-Audio model download defaults to ModelScope

**Reason**: MOSS-Audio backend removed.

**Migration**: N/A.

### Requirement: MOSS-Audio long audio chunking

**Reason**: MOSS-Audio backend removed.

**Migration**: FunASR VAD handles long audio segmentation.

### Requirement: MOSS-Audio diarization fallback

**Reason**: MOSS-Audio backend removed.

**Migration**: FunASR cam++ provides native speaker diarization.
