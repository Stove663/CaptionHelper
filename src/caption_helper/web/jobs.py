from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from caption_helper.extract import extract_audio
from caption_helper.split import split_segments
from caption_helper.subtitles_json import initialize_subtitle_files
from caption_helper.transcribe import Transcriber, TranscriberConfig
from caption_helper.tts.moss_tts import MossTTSConfig, MossTTSEngine
from caption_helper.tts.preflight import check_tts_compatibility, log_gpu_info
from caption_helper.tts.reference import ReferenceConfig, build_speaker_reference_bank
from caption_helper.remux.ripple import apply_ripple_artifacts
from caption_helper.tts.compression_risk import SYNC_MODE_NATURAL
from caption_helper.tts.synthesizer import load_synthesis_manifest, synthesize_modified_segments
from caption_helper.web.store import ProjectStore

logger = logging.getLogger(__name__)


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
    """Runs ASR and TTS pipeline jobs one at a time in a background thread pool."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._pipeline_lock = asyncio.Lock()
        self._synthesis_lock = asyncio.Lock()
        self._remux_lock = asyncio.Lock()
        self._pipeline_options: dict[str, Any] = {}
        self._tts_config = MossTTSConfig()
        self._ref_config = ReferenceConfig()
        self._tts_engine: MossTTSEngine | None = None
        self._synthesis_progress: dict[str, SynthesisProgress] = {}
        self._remux_progress: dict[str, RemuxProgress] = {}
        self._skip_unavailable = False

    def set_pipeline_options(self, **options: Any) -> None:
        self._pipeline_options.update(options)

    def set_tts_options(
        self,
        *,
        model: str | None = None,
        device: str | None = None,
        tokens_per_second: float | None = None,
        language: str | None = None,
    ) -> None:
        from caption_helper.tts.preflight import resolve_tts_model

        if model is not None:
            self._tts_config.model = resolve_tts_model(model)
        if device is not None:
            self._tts_config.device = device
        if tokens_per_second is not None:
            self._tts_config.tokens_per_second = tokens_per_second
        if language is not None:
            self._tts_config.language = language
        self._tts_engine = None

    def tts_model_id(self) -> str:
        return self._tts_config.model

    def ref_config(self) -> ReferenceConfig:
        return self._ref_config

    def set_ref_options(
        self,
        *,
        min_ref_duration_ms: int | None = None,
        min_quality_score: float | None = None,
    ) -> None:
        if min_ref_duration_ms is not None:
            self._ref_config.min_ref_duration_ms = min_ref_duration_ms
        if min_quality_score is not None:
            self._ref_config.min_quality_score = min_quality_score

    def get_synthesis_progress(self, project_id: str) -> SynthesisProgress:
        return self._synthesis_progress.get(project_id, SynthesisProgress())

    def get_remux_progress(self, project_id: str) -> RemuxProgress:
        return self._remux_progress.get(project_id, RemuxProgress())

    async def enqueue(self, project_id: str) -> None:
        async with self._pipeline_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._run_project, project_id)

    async def enqueue_synthesis(self, project_id: str, *, skip_unavailable: bool = False) -> None:
        self._skip_unavailable = skip_unavailable
        async with self._synthesis_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._run_synthesis, project_id)

    async def enqueue_remux(self, project_id: str) -> None:
        async with self._remux_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._run_remux, project_id)

    def _get_tts_engine(self) -> MossTTSEngine:
        if self._tts_engine is None:
            self._tts_engine = MossTTSEngine(self._tts_config)
        return self._tts_engine

    def _run_project(self, project_id: str) -> None:
        try:
            project_dir = self.store.project_path(project_id)
            source = self.store.find_source_video(project_id)
            audio_wav = project_dir / "audio.wav"
            segments_dir = project_dir / "segments"

            self.store.update_status(project_id, "extracting")
            extract_audio(source, audio_wav)

            self.store.update_status(project_id, "transcribing")
            transcriber = Transcriber(
                TranscriberConfig(
                    device=self._pipeline_options.get("device"),
                    language=self._pipeline_options.get("language", "中文"),
                    hub=self._pipeline_options.get("hub"),
                    max_single_segment_time=self._pipeline_options.get(
                        "max_single_segment_time", 30_000
                    ),
                )
            )
            sentences = transcriber.transcribe(str(audio_wav))
            if not sentences:
                raise RuntimeError("Transcription returned no sentences")

            self.store.update_status(project_id, "splitting")
            initialize_subtitle_files(project_dir, sentences)
            split_segments(audio_wav, sentences, segments_dir)
            build_speaker_reference_bank(project_dir, config=self._ref_config)

            self.store.update_status(project_id, "ready")
            logger.info("Project %s ready", project_id)
        except Exception as exc:
            logger.exception("Project %s failed", project_id)
            self.store.update_status(project_id, "failed", error=str(exc))

    def _run_synthesis(self, project_id: str) -> None:
        model_id = self._tts_config.model
        preflight = check_tts_compatibility(model_id)
        if not preflight.ok:
            self.store.update_status(project_id, "synthesis_failed", error=preflight.message)
            return
        log_gpu_info(model_id)

        progress = SynthesisProgress(status="synthesizing")
        self._synthesis_progress[project_id] = progress
        try:
            project_dir = self.store.project_path(project_id)
            self.store.update_status(project_id, "synthesizing")

            def on_progress(completed: int, total: int) -> None:
                progress.completed = completed
                progress.total = total

            sync_mode = self.store.get_project(project_id).sync_mode

            result = synthesize_modified_segments(
                project_dir,
                engine=self._get_tts_engine(),
                ref_config=self._ref_config,
                sync_mode=sync_mode,
                on_progress=on_progress,
                skip_unavailable=self._skip_unavailable,
            )
            progress.completed = result.completed
            progress.total = result.total
            progress.errors = [
                {"index": c.index, "error": c.error}
                for c in result.cues
                if c.status == "failed" and c.error
            ]

            if sync_mode == SYNC_MODE_NATURAL and result.completed > 0:
                apply_ripple_artifacts(project_dir, sync_mode=sync_mode)

            if result.total == 0:
                progress.status = "synthesis_ready"
                self.store.update_status(project_id, "synthesis_ready")
            elif result.failed == 0:
                progress.status = "synthesis_ready"
                self.store.update_status(project_id, "synthesis_ready")
            elif result.completed == 0:
                progress.status = "synthesis_failed"
                self.store.update_status(
                    project_id,
                    "synthesis_failed",
                    error=f"All {result.failed} synthesis jobs failed",
                )
            else:
                progress.status = "synthesis_ready"
                self.store.update_status(project_id, "synthesis_ready")

            logger.info(
                "Project %s synthesis done: %s/%s",
                project_id,
                result.completed,
                result.total,
            )
        except Exception as exc:
            logger.exception("Project %s synthesis failed", project_id)
            progress.status = "synthesis_failed"
            progress.errors.append({"index": None, "error": str(exc)})
            self.store.update_status(project_id, "synthesis_failed", error=str(exc))

    def _run_remux(self, project_id: str) -> None:
        from caption_helper.remux.pipeline import remux_pipeline

        progress = RemuxProgress(status="remuxing", stage="assembling")
        self._remux_progress[project_id] = progress
        try:
            project_dir = self.store.project_path(project_id)
            sync_mode = self.store.get_project(project_id).sync_mode
            self.store.update_status(project_id, "remuxing")

            if sync_mode == SYNC_MODE_NATURAL:
                progress.stage = "speed_adjust"

            remux_pipeline(project_dir, sync_mode=sync_mode)
            progress.stage = "done"
            progress.status = "remux_ready"
            self.store.update_status(project_id, "remux_ready")
            logger.info("Project %s remux ready", project_id)
        except Exception as exc:
            logger.exception("Project %s remux failed", project_id)
            progress.status = "remux_failed"
            progress.error = str(exc)
            self.store.update_status(project_id, "remux_failed", error=str(exc))

    def load_manifest_errors(self, project_id: str) -> list[dict[str, Any]]:
        try:
            manifest = load_synthesis_manifest(self.store.project_path(project_id))
        except FileNotFoundError:
            return []
        if not manifest:
            return []
        return [
            {"index": c.get("index"), "error": c.get("error")}
            for c in manifest.get("cues", [])
            if c.get("status") == "failed"
        ]
