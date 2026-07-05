## 1. Store and job runner

- [x] 1.1 Add `ProjectStore.clear_downstream_artifacts(project_id, through="asr"|"tts"|"remux")` with unit tests for expected paths removed
- [x] 1.2 Add `JobRunner._run_references` and `enqueue_references` with `building_references` status updates
- [x] 1.3 Refactor ASR enqueue to call `clear_downstream_artifacts(through="asr")` before `_run_project` when triggered via rerun
- [x] 1.4 Add shared `_busy` guards: reject conflicting reruns with clear checks per design mutex table

## 2. API endpoints

- [x] 2.1 Implement `POST /api/projects/{id}/rerun/asr` (202, 400, 409)
- [x] 2.2 Implement `POST /api/projects/{id}/rerun/references` (202, 400, 409)
- [x] 2.3 Implement `POST /api/projects/{id}/rerun/synthesis` delegating to existing synthesis logic with same body options
- [x] 2.4 Implement `POST /api/projects/{id}/rerun/remux` delegating to existing remux logic
- [x] 2.5 Add `tests/test_web.py` coverage for each endpoint: success, missing prerequisites, 409 while busy, ASR cleanup

## 3. Frontend API helpers

- [x] 3.1 Add `rerunAsr`, `rerunReferences`, `rerunSynthesis`, `rerunRemux` to `frontend/src/api.ts`
- [x] 3.2 Export helper to map project status → available rerun actions

## 4. Home page UI

- [x] 4.1 Add rerun action controls on `HomePage.tsx` for post-upload projects (ASR, references, synthesis, remux by status)
- [x] 4.2 Wire confirmation dialog for ASR rerun; disable buttons and show in-progress label during processing

## 5. Editor and preview UI

- [x] 5.1 Add rerun toolbar group on `EditorPage.tsx` (ASR confirm, rebuild references, re-synthesize)
- [x] 5.2 Reload subtitles, reference quality, and synthesis state when polling detects rerun completion
- [x] 5.3 Add explicit「重新 remux」on `PreviewPage.tsx` calling `rerunRemux` (alongside existing generate flow if applicable)

## 6. Polish

- [x] 6.1 Add CSS for rerun button group / dropdown consistent with existing toolbar styles
- [x] 6.2 Run full test suite (`uv run pytest`) and manual smoke test: upload → edit → rerun each stage without re-upload
