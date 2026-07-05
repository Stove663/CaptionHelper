## 1. Storage layer

- [x] 1.1 Add `delete_project(project_id)` to `ProjectStore` using `shutil.rmtree` on the project directory
- [x] 1.2 Add shared `is_project_busy(status, jobs, project_id)` helper (reuse rerun busy checks) in `rerun.py` or a small `lifecycle.py` module

## 2. Expiration cleanup

- [x] 2.1 Add `purge_expired_projects(store, *, retention_days=7)` that deletes non-busy projects older than retention window
- [x] 2.2 Register FastAPI lifespan in `create_app` to run cleanup at startup and hourly thereafter

## 3. Delete API

- [x] 3.1 Add `DELETE /api/projects/{id}` route returning 204 / 404 / 409 per spec
- [x] 3.2 Wire route to `store.delete_project` after busy-status check

## 4. Frontend

- [x] 4.1 Add `deleteProject(id)` to `frontend/src/api.ts`
- [x] 4.2 Add delete button with confirmation dialog to `HomePage.tsx`; disable while processing or rerunning

## 5. Tests

- [x] 5.1 Test successful delete removes directory and excludes project from list
- [x] 5.2 Test delete returns 404 for unknown project and 409 while processing
- [x] 5.3 Test `purge_expired_projects` deletes old idle projects and skips busy/recent ones
