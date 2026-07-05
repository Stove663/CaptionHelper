## MODIFIED Requirements

### Requirement: Voice cloning from original segment

The system SHALL support MOSS-TTS as one selectable synthesis provider for modified cues. When MOSS-TTS is selected, the system SHALL resolve voice-cloning reference audio for each modified cue using the reference fallback hierarchy, not always the cue's own segment. The resolved reference MUST belong to the same speaker (`spk`) as the cue.

#### Scenario: Resolved reference passed to MOSS-TTS

- **WHEN** synthesizing cue index 3 with `spk=1` and the resolved reference is `speaker_refs/spk1.wav`
- **THEN** MOSS-TTS receives `text_edited` and `reference=[speaker_refs/spk1.wav]`

#### Scenario: Missing reference blocks cue synthesis

- **WHEN** no adequate reference can be resolved for cue index 3's speaker
- **THEN** the system marks cue 3 as failed in `synthesis_manifest.json` and continues with remaining cues

#### Scenario: Reference resolution before synthesis

- **WHEN** a TTS synthesis job starts
- **THEN** the system resolves reference audio for every modified cue before calling MOSS-TTS
