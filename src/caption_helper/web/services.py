from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caption_helper.web.manifests import StageArtifactManifest
from caption_helper.web.manifest_writer import write_stage_manifest

from caption_helper.extract import extract_audio
from caption_helper.split import split_segments
from caption_helper.subtitles_json import initialize_subtitle_files
from caption_helper.transcribe import TranscriberConfig, get_transcriber
from caption_helper.tts.compression_risk import SYNC_MODE_NATURAL
from caption_helper.tts.glm_tts import GLMTTSConfig, GLMTTSEngine
from caption_helper.tts.moss_tts import MossTTSConfig, MossTTSEngine
from caption_helper.tts.preflight import check_tts_compatibility, log_gpu_info, resolve_tokens_per_second, resolve_tts_model
from caption_helper.tts.reference import ReferenceConfig, build_speaker_reference_bank
from caption_helper.tts.synthesizer import load_synthesis_manifest, synthesize_modified_segments
from caption_helper.remux.ripple import apply_ripple_artifacts
from caption_helper.remux.pipeline import remux_pipeline
from caption_helper.web.domain import ProjectStatus
from caption_helper.web.store import ProjectStore


@dataclass
class PipelineResult:
    status: str
    error: str | None = None


class ProjectPipelineService:
    def __init__(self, store: ProjectStore, ref_config: ReferenceConfig, pipeline_options: dict[str, Any]) -> None:
        self.store = store
        self.ref_config = ref_config
        self.pipeline_options = pipeline_options

    def run(self, project_id: str) -> PipelineResult:
        try:
            project_dir = self.store.project_path(project_id)
            source = self.store.find_source_video(project_id)
            audio_wav = project_dir / "audio.wav"
            segments_dir = project_dir / "segments"
            self.store.update_status(project_id, ProjectStatus.EXTRACTING.value)
            extract_audio(source, audio_wav)
            self.store.update_status(project_id, ProjectStatus.TRANSCRIBING.value)
            transcriber = get_transcriber(TranscriberConfig(
                device=self.pipeline_options.get("device"),
                language=self.pipeline_options.get("language", "中文"),
                hub=self.pipeline_options.get("hub"),
                max_single_segment_time=self.pipeline_options.get("max_single_segment_time", 30_000),
            ))
            sentences = transcriber.transcribe(str(audio_wav))
            if not sentences:
                raise RuntimeError("Transcription returned no sentences")
            self.store.update_status(project_id, ProjectStatus.SPLITTING.value)
            initialize_subtitle_files(project_dir, sentences)
            split_segments(audio_wav, sentences, segments_dir)
            build_speaker_reference_bank(project_dir, config=self.ref_config)
            self.store.update_status(project_id, ProjectStatus.READY.value)
            manifest = StageArtifactManifest(
                stage="pipeline",
                inputs=[str(source)],
                outputs=[str(audio_wav), str(project_dir / "subtitles.json")],
                notes="ASR extraction, transcription, split, and reference bank generation",
            )
            write_stage_manifest(project_dir / "pipeline_manifest.json", manifest)
            return PipelineResult(status=ProjectStatus.READY.value)
        except Exception as exc:
            self.store.update_status(project_id, ProjectStatus.FAILED.value, error=str(exc))
            return PipelineResult(status=ProjectStatus.FAILED.value, error=str(exc))


class ReferenceService:
    def __init__(self, store: ProjectStore, ref_config: ReferenceConfig) -> None:
        self.store = store
        self.ref_config = ref_config

    def run(self, project_id: str) -> PipelineResult:
        try:
            project_dir = self.store.project_path(project_id)
            self.store.update_status(project_id, ProjectStatus.BUILDING_REFERENCES.value)
            build_speaker_reference_bank(project_dir, config=self.ref_config)
            self.store.update_status(project_id, ProjectStatus.READY.value)
            manifest = StageArtifactManifest(
                stage="references",
                inputs=[str(project_dir / "segments")],
                outputs=[str(project_dir / "speaker_refs")],
                notes="Reference bank rebuild",
            )
            write_stage_manifest(project_dir / "references_manifest.json", manifest)
            return PipelineResult(status=ProjectStatus.READY.value)
        except Exception as exc:
            self.store.update_status(project_id, ProjectStatus.FAILED.value, error=str(exc))
            return PipelineResult(status=ProjectStatus.FAILED.value, error=str(exc))


class SynthesisService:
    def __init__(self, store: ProjectStore, ref_config: ReferenceConfig, tts_config: MossTTSConfig, glm_tts_config: GLMTTSConfig) -> None:
        self.store = store
        self.ref_config = ref_config
        self.tts_config = tts_config
        self.glm_tts_config = glm_tts_config
        self._moss_engine: MossTTSEngine | None = None
        self._glm_engine: GLMTTSEngine | None = None

    def _engine(self, provider: str):
        if provider == "glm-tts":
            if self._glm_engine is None:
                self._glm_engine = GLMTTSEngine(self.glm_tts_config)
            return self._glm_engine
        if self._moss_engine is None:
            self._moss_engine = MossTTSEngine(self.tts_config)
        return self._moss_engine

    def run(self, project_id: str, *, skip_unavailable: bool = False) -> PipelineResult:
        project = self.store.get_project(project_id)
        provider = project.tts_provider
        model_id = self.tts_config.model if provider != "glm-tts" else self.glm_tts_config.model
        preflight = check_tts_compatibility(model_id, provider=provider, device=self.tts_config.device)
        if not preflight.ok:
            return PipelineResult(status=ProjectStatus.SYNTHESIS_FAILED.value, error=preflight.message)
        log_gpu_info(model_id, device=self.tts_config.device)
        project_dir = self.store.project_path(project_id)
        self.store.update_status(project_id, ProjectStatus.SYNTHESIZING.value)
        result = synthesize_modified_segments(
            project_dir,
            engine=self._engine(provider),
            ref_config=self.ref_config,
            sync_mode=project.sync_mode,
            tts_provider=provider,
            glm_phoneme_mode=project.glm_phoneme_mode,
            skip_unavailable=skip_unavailable,
        )
        if project.sync_mode == SYNC_MODE_NATURAL and result.completed > 0:
            apply_ripple_artifacts(project_dir, sync_mode=project.sync_mode)
        if result.total == 0 or result.failed == 0 or result.completed > 0:
            self.store.update_status(project_id, ProjectStatus.SYNTHESIS_READY.value)
            manifest = StageArtifactManifest(
                stage="synthesis",
                inputs=[str(project_dir / "subtitles.json")],
                outputs=[str(project_dir / "tts_segments")],
                notes="Synthesis completed",
            )
            write_stage_manifest(project_dir / "synthesis_manifest.json", manifest)
            return PipelineResult(status=ProjectStatus.SYNTHESIS_READY.value)
        self.store.update_status(project_id, ProjectStatus.SYNTHESIS_FAILED.value, error=f"All {result.failed} synthesis jobs failed")
        return PipelineResult(status=ProjectStatus.SYNTHESIS_FAILED.value, error=f"All {result.failed} synthesis jobs failed")


class RemuxService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    def run(self, project_id: str) -> PipelineResult:
        try:
            project_dir = self.store.project_path(project_id)
            sync_mode = self.store.get_project(project_id).sync_mode
            self.store.update_status(project_id, ProjectStatus.REMUXING.value)
            remux_pipeline(project_dir, sync_mode=sync_mode)
            self.store.update_status(project_id, ProjectStatus.REMUX_READY.value)
            manifest = StageArtifactManifest(
                stage="remux",
                inputs=[str(project_dir / "output_audio.wav")],
                outputs=[str(project_dir / "output_video.mp4")],
                notes="Remux completed",
            )
            write_stage_manifest(project_dir / "remux_manifest.json", manifest)
            return PipelineResult(status=ProjectStatus.REMUX_READY.value)
        except Exception as exc:
            self.store.update_status(project_id, ProjectStatus.REMUX_FAILED.value, error=str(exc))
            return PipelineResult(status=ProjectStatus.REMUX_FAILED.value, error=str(exc))
