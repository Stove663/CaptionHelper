import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from caption_helper.network.mirrors import apply_china_mirror_defaults
from caption_helper.tts.preflight import log_gpu_info, resolve_tts_model
from caption_helper.web.jobs import JobRunner
from caption_helper.web.lifecycle import CLEANUP_INTERVAL_SECONDS, STARTUP_DELAY_SECONDS, purge_expired_projects
from caption_helper.web.routes.projects import router as projects_router
from caption_helper.web.store import ProjectStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    store: ProjectStore = app.state.store
    jobs: JobRunner = app.state.jobs

    async def cleanup_loop() -> None:
        await asyncio.sleep(STARTUP_DELAY_SECONDS)
        while True:
            try:
                await asyncio.to_thread(purge_expired_projects, store, jobs)
            except Exception:
                logger.exception("Project expiration cleanup failed")
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app(
    data_dir: Path,
    frontend_dist: Path | None = None,
    tts_model: str | None = None,
    tts_device: str | None = None,
) -> FastAPI:
    apply_china_mirror_defaults()
    app = FastAPI(title="CaptionHelper", version="0.1.0", lifespan=_lifespan)
    store = ProjectStore(data_dir)
    jobs = JobRunner(store)
    app.state.store = store
    app.state.jobs = jobs
    app.include_router(projects_router)

    model_id = resolve_tts_model(tts_model) if tts_model else None
    if model_id:
        log_gpu_info(model_id, device=tts_device)

    dist = frontend_dist or Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            return FileResponse(dist / "index.html")

    return app
