## 1. Project metadata and API

- [x] 1.1 Add `asr_provider` field to `ProjectMeta` with default `funasr` and `setdefault` on read in `store.py`
- [x] 1.2 Add `store.update_asr_provider()` validating `funasr` | `moss-audio`
- [x] 1.3 Add `PUT /api/projects/{id}/asr-provider` endpoint with 422 on invalid value and 409 while ASR busy
- [x] 1.4 Return `asr_provider` in `GET /api/projects/{id}` and project list responses
- [x] 1.5 Accept optional `asr_provider` on video upload (`POST /api/projects`) and persist in `meta.json`
- [x] 1.6 Add API unit tests for provider validation, persistence, default fallback, and busy-state rejection

## 2. Transcription layer refactor

- [x] 2.1 Introduce `BaseTranscriber` protocol / ABC with `transcribe(audio_path) -> list[Sentence]`
- [x] 2.2 Rename or alias existing `Transcriber` as `FunASRTranscriber` implementing the shared contract
- [x] 2.3 Add `get_transcriber(provider, config)` factory in `transcribe.py`
- [x] 2.4 Update `pipeline.process()` to accept `asr_provider` and dispatch via factory
- [x] 2.5 Update `JobRunner` background ASR and ASR rerun to pass `project.asr_provider`
- [x] 2.6 Add `--asr-provider {funasr,moss-audio}` to `caption-helper process` CLI

## 3. MOSS-Audio backend

- [x] 3.1 Add optional `[moss-audio]` extra in `pyproject.toml` with MOSS-Audio runtime dependencies documented
- [x] 3.2 Implement `MossAudioTranscriber` in `transcribe/moss_audio.py` (or `transcribe.py`) with lazy model load
- [x] 3.3 Load `openmoss/MOSS-Audio-4B-Instruct` from ModelScope by default; respect `--hub hf` and `HF_ENDPOINT`
- [x] 3.4 Implement timestamp-ASR prompt and `sentences_from_moss_audio_output()` parser
- [x] 3.5 Implement long-audio chunking with ffmpeg and timestamp offset merge
- [x] 3.6 Implement diarization parse-failure fallback (`spk=0` + warning log)
- [x] 3.7 Add unit tests for output parser and chunk merge logic with fixture model responses

## 4. Preflight and errors

- [x] 4.1 Add MOSS-Audio preflight: CUDA required, minimum VRAM check, `[moss-audio]` extra installed
- [x] 4.2 Return clear errors on web upload and CLI when preflight fails
- [x] 4.3 Block `PUT /asr-provider` to `moss-audio` when preflight would fail (optional warning in API response)

## 5. Web UI provider selector

- [x] 5.1 Add `asr_provider` to frontend `ProjectMeta` types and API client helpers
- [x] 5.2 Add FunASR / MOSS-Audio toggle on `HomePage` upload form; send provider on upload
- [x] 5.3 Add FunASR / MOSS-Audio toggle in `EditorPage` toolbar; persist via `setAsrProvider` API
- [x] 5.4 Disable ASR provider toggle while status is `extracting`, `transcribing`, or `splitting`
- [x] 5.5 Show active ASR provider in project detail or status panel

## 6. Documentation and verification

- [x] 6.1 Document MOSS-Audio install, ModelScope checkpoint download, and provider selection in README
- [x] 6.2 Manual test: upload with MOSS-Audio selected, verify subtitles and segments generated
- [x] 6.3 Manual test: ASR rerun uses stored provider without re-upload
- [x] 6.4 Manual test: existing projects without `asr_provider` default to FunASR unchanged
