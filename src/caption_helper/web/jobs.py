from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from caption_helper.tts.glm_tts import GLMTTSConfig
from caption_helper.tts.moss_tts import MossTTSConfig
from caption_helper.tts.reference import ReferenceConfig
from caption_helper.web.services import ProjectPipelineService, ReferenceService, RemuxService, SynthesisService
from caption_helper.web.store import ProjectStore


@dataclass
class SynthesisProgress:
    status: str = "idle"
    completed: int = 0
    total: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RemuxProgress:
    status: str = "idle"
    stage: str = ""
    error: str | None = None


class JobRunner:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._pipeline_lock = asyncio.Lock()
        self._synthesis_lock = asyncio.Lock()
        self._remux_lock = asyncio.Lock()
        self._references_lock = asyncio.Lock()
        self._pipeline_options: dict[str, Any] = {}
        self._tts_config = MossTTSConfig()
        self._glm_tts_config = GLMTTSConfig()
        self._ref_config = ReferenceConfig()
        self._synthesis_progress: dict[str, SynthesisProgress] = {}
        self._remux_progress: dict[str, RemuxProgress] = {}
        self._pipeline_service = ProjectPipelineService(store, self._ref_config, self._pipeline_options)
        self._reference_service = ReferenceService(store, self._ref_config)
        self._synthesis_service = SynthesisService(store, self._ref_config, self._tts_config, self._glm_tts_config)
        self._remux_service = RemuxService(store)

    def set_pipeline_options(self, **options: Any) -> None:
        self._pipeline_options.update(options)

    def set_tts_options(self, **kwargs: Any) -> None:
        self._tts_config.__dict__.update({k: v for k, v in kwargs.items() if v is not None})

    def tts_model_id(self, *, provider: str = "moss-tts") -> str:
        return self._glm_tts_config.model if provider == "glm-tts" else self._tts_config.model

    def tts_device(self) -> str | None:
        return self._tts_config.device

    def ref_config(self) -> ReferenceConfig:
        return self._ref_config

    def set_ref_options(self, **kwargs: Any) -> None:
        self._ref_config.__dict__.update({k: v for k, v in kwargs.items() if v is not None})

    def get_synthesis_progress(self, project_id: str) -> SynthesisProgress:
        return self._synthesis_progress.get(project_id, SynthesisProgress())

    def get_remux_progress(self, project_id: str) -> RemuxProgress:
        return self._remux_progress.get(project_id, RemuxProgress())

    async def enqueue(self, project_id: str) -> None:
        async with self._pipeline_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._pipeline_service.run, project_id)

    async def enqueue_asr_rerun(self, project_id: str) -> None:
        self.store.clear_downstream_artifacts(project_id, through="asr")
        self.store.update_status(project_id, "uploaded", error=None)
        async with self._pipeline_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._pipeline_service.run, project_id)

    async def enqueue_references(self, project_id: str) -> None:
        async with self._references_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._reference_service.run, project_id)

    async def enqueue_synthesis(self, project_id: str, *, skip_unavailable: bool = False) -> None:
        async with self._synthesis_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._synthesis_service.run, project_id, skip_unavailable=skip_unavailable)

    async def enqueue_remux(self, project_id: str) -> None:
        async with self._remux_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._remux_service.run, project_id)
