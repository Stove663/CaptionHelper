from __future__ import annotations

import mimetypes
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from caption_helper.remux.pipeline import remux_warnings
from caption_helper.remux.ripple import load_timeline
from caption_helper.remux.assemble import MissingTTSClipsError, validate_clips
from caption_helper.remux.manifest import load_remux_manifest
from caption_helper.subtitles_json import (
    generate_modified_segments,
    load_subtitles,
    save_subtitles,
    validate_save_request,
    write_srt_from_cues,
)
from caption_helper.asr_preflight import check_asr_compatibility
from caption_helper.tts.compression_risk import VALID_SYNC_MODES, compression_risks_at_risk
from caption_helper.tts.glm_phoneme import count_code_mixed_modified, glm_provider_guidance
from caption_helper.tts.preflight import check_tts_compatibility
from caption_helper.tts.reference import build_reference_quality_report, save_reference_override
from caption_helper.web.jobs import JobRunner
from caption_helper.web.lifecycle import is_project_busy
from caption_helper.web.rerun import RerunConflictError, check_rerun_allowed
from caption_helper.web.store import ProjectStore

router = APIRouter(prefix="/api/projects")


def _store(request: Request) -> ProjectStore:
    return request.app.state.store


def _jobs(request: Request) -> JobRunner:
    return request.app.state.jobs


def _rerun_conflict(exc: RerunConflictError) -> HTTPException:
    return HTTPException(status_code=409, detail=exc.message)


@router.post("/{project_id}/rerun/asr", status_code=202)
async def rerun_asr(request: Request, project_id: str) -> dict[str, Any]:
    store = _store(request)
    jobs = _jobs(request)
    try:
        store.find_source_video(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="No source video for project") from exc
    try:
        check_rerun_allowed(store, jobs, project_id, "asr")
    except RerunConflictError as exc:
        raise _rerun_conflict(exc) from exc
    await jobs.enqueue_asr_rerun(project_id)
    return {"status": "extracting"}


@router.post("/{project_id}/rerun/references", status_code=202)
async def rerun_references(request: Request, project_id: str) -> dict[str, Any]:
    store = _store(request)
    jobs = _jobs(request)
    project_dir = _project_dir(request, project_id)
    if not (project_dir / "subtitles.json").is_file():
        raise HTTPException(status_code=400, detail="Subtitles not ready")
    segments = list((project_dir / "segments").glob("*.wav"))
    if not segments:
        raise HTTPException(status_code=400, detail="No audio segments")
    try:
        check_rerun_allowed(store, jobs, project_id, "references")
    except RerunConflictError as exc:
        raise _rerun_conflict(exc) from exc
    await jobs.enqueue_references(project_id)
    return {"status": "building_references"}


@router.post("/{project_id}/rerun/synthesis", status_code=202)
async def rerun_synthesis(
    request: Request,
    project_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _store(request)
    jobs = _jobs(request)
    try:
        check_rerun_allowed(store, jobs, project_id, "synthesis")
    except RerunConflictError as exc:
        raise _rerun_conflict(exc) from exc
    return await _start_synthesis(request, project_id, body)


@router.post("/{project_id}/rerun/remux", status_code=202)
async def rerun_remux(request: Request, project_id: str) -> dict[str, Any]:
    store = _store(request)
    jobs = _jobs(request)
    try:
        check_rerun_allowed(store, jobs, project_id, "remux")
    except RerunConflictError as exc:
        raise _rerun_conflict(exc) from exc
    return await _start_remux(request, project_id)


@router.post("", status_code=202)
async def create_project(
    request: Request,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload")

    hub = request.app.state.jobs._pipeline_options.get("hub")
    preflight = check_asr_compatibility(hub=hub)
    if not preflight.ok:
        raise HTTPException(status_code=400, detail=preflight.message)

    store = _store(request)
    meta = store.create_project(file.filename)
    store.save_upload(meta.id, file.filename, content)
    await _jobs(request).enqueue(meta.id)
    return meta.to_dict()


@router.get("")
def list_projects(request: Request) -> list[dict[str, Any]]:
    return [m.to_dict() for m in _store(request).list_projects()]


@router.get("/{project_id}")
def get_project(request: Request, project_id: str) -> dict[str, Any]:
    try:
        return _store(request).get_project(project_id).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=204)
def delete_project_route(request: Request, project_id: str) -> None:
    store = _store(request)
    jobs = _jobs(request)
    try:
        meta = store.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if is_project_busy(meta.status, jobs, project_id):
        raise HTTPException(status_code=409, detail="Project is processing")
    store.delete_project(project_id)


@router.put("/{project_id}/sync-mode")
def set_sync_mode(request: Request, project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    sync_mode = str(body.get("sync_mode", ""))
    if sync_mode not in VALID_SYNC_MODES:
        raise HTTPException(status_code=422, detail=f"sync_mode must be one of {sorted(VALID_SYNC_MODES)}")
    try:
        meta = _store(request).update_sync_mode(project_id, sync_mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return meta.to_dict()


@router.put("/{project_id}/tts-provider")
def set_tts_provider(request: Request, project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    provider = str(body.get("tts_provider", "moss-tts")).strip().lower()
    if provider not in {"moss-tts", "glm-tts"}:
        raise HTTPException(status_code=422, detail="tts_provider must be one of ['glm-tts', 'moss-tts']")
    try:
        meta = _store(request).update_tts_provider(project_id, provider)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return meta.to_dict()


@router.get("/{project_id}/compression-risk")
def compression_risk(request: Request, project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    json_path = project_dir / "subtitles.json"
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail="Subtitles not ready")
    meta = _store(request).get_project(project_id)
    cues = load_subtitles(json_path)
    risks = compression_risks_at_risk(cues)
    code_mixed_modified_count = count_code_mixed_modified(cues)
    return {
        "at_risk_count": len(risks),
        "code_mixed_modified_count": code_mixed_modified_count,
        "provider_guidance": glm_provider_guidance(
            tts_provider=meta.tts_provider,
            sync_mode=meta.sync_mode,
            code_mixed_modified_count=code_mixed_modified_count,
        ),
        "cues": [asdict(r) for r in risks],
    }


@router.get("/{project_id}/timeline")
def get_timeline(request: Request, project_id: str) -> dict[str, Any]:
    timeline = load_timeline(_project_dir(request, project_id))
    if timeline is None:
        raise HTTPException(status_code=404, detail="No timeline computed yet")
    return timeline.to_dict()


@router.get("/{project_id}/remux-warnings")
def get_remux_warnings(request: Request, project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    meta = _store(request).get_project(project_id)
    warnings = remux_warnings(project_dir, sync_mode=meta.sync_mode)
    return {"warnings": warnings, "sync_mode": meta.sync_mode}


@router.get("/{project_id}/subtitles")
def get_subtitles(request: Request, project_id: str) -> dict[str, Any]:
    import json

    path = _project_dir(request, project_id) / "subtitles.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Subtitles not ready")
    return json.loads(path.read_text(encoding="utf-8"))


@router.put("/{project_id}/subtitles")
def save_subtitles_api(request: Request, project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    json_path = project_dir / "subtitles.json"
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail="Subtitles not found")

    existing = load_subtitles(json_path)
    try:
        updated = validate_save_request(existing, body.get("cues", []))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    save_subtitles(json_path, updated)
    write_srt_from_cues(updated, project_dir / "subtitles_edited.srt")
    modified = generate_modified_segments(project_dir, updated)
    return {"cues": [asdict(c) for c in updated], "modified_count": len(modified)}


@router.get("/{project_id}/modified-segments")
def get_modified_segments(request: Request, project_id: str) -> list[dict[str, Any]]:
    path = _project_dir(request, project_id) / "modified_segments.json"
    if not path.is_file():
        return []
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{project_id}/reference-quality")
def reference_quality(request: Request, project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    return build_reference_quality_report(project_dir, config=_jobs(request).ref_config())


@router.put("/{project_id}/cues/{cue_index}/reference")
def set_cue_reference(
    request: Request,
    project_id: str,
    cue_index: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    segment_path = str(body.get("segment_path", ""))
    if not segment_path:
        raise HTTPException(status_code=422, detail="segment_path is required")

    cues = load_subtitles(project_dir / "subtitles.json")
    cue = next((c for c in cues if c.index == cue_index), None)
    if cue is None:
        raise HTTPException(status_code=404, detail=f"Cue {cue_index} not found")

    seg_match = re.search(r"_spk(\d+)_", segment_path)
    if not seg_match or int(seg_match.group(1)) != cue.spk:
        raise HTTPException(status_code=422, detail="Reference segment must be same speaker")

    full = project_dir / segment_path
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Segment file not found")

    save_reference_override(project_dir, cue_index, segment_path)
    return {"index": cue_index, "segment_path": segment_path}


@router.post("/{project_id}/synthesize", status_code=202)
async def start_synthesis(
    request: Request,
    project_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await _start_synthesis(request, project_id, body)


async def _start_synthesis(
    request: Request,
    project_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    modified_path = project_dir / "modified_segments.json"
    if not modified_path.is_file():
        raise HTTPException(status_code=400, detail="No modified segments to synthesize")

    import json

    modified = json.loads(modified_path.read_text(encoding="utf-8"))
    if not modified:
        raise HTTPException(status_code=400, detail="No modified segments to synthesize")

    jobs = _jobs(request)
    provider = _store(request).get_project(project_id).tts_provider
    model_id = jobs.tts_model_id(provider=provider)
    preflight = check_tts_compatibility(
        model_id, provider=provider, device=jobs.tts_device()
    )
    if not preflight.ok:
        raise HTTPException(status_code=400, detail=preflight.message)

    skip_unavailable = bool((body or {}).get("skip_unavailable", False))
    sync_mode = (body or {}).get("sync_mode")
    store = _store(request)
    if sync_mode:
        if sync_mode not in VALID_SYNC_MODES:
            raise HTTPException(status_code=422, detail="Invalid sync_mode")
        store.update_sync_mode(project_id, sync_mode)

    report = build_reference_quality_report(project_dir, config=jobs.ref_config())
    if report.get("unavailable") and not skip_unavailable:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some modified cues have no adequate reference audio",
                "unavailable": report["unavailable"],
            },
        )

    progress = jobs.get_synthesis_progress(project_id)
    if progress.status == "synthesizing":
        raise HTTPException(status_code=409, detail="Synthesis already in progress")

    await jobs.enqueue_synthesis(project_id, skip_unavailable=skip_unavailable)
    meta = store.get_project(project_id)
    return {
        "status": "synthesizing",
        "total": len(modified),
        "skip_unavailable": skip_unavailable,
        "sync_mode": meta.sync_mode,
        "tts_provider": meta.tts_provider,
    }


@router.get("/{project_id}/synthesis-status")
def synthesis_status(request: Request, project_id: str) -> dict[str, Any]:
    _project_dir(request, project_id)
    jobs = _jobs(request)
    progress = jobs.get_synthesis_progress(project_id)
    errors = progress.errors or jobs.load_manifest_errors(project_id)
    return {
        "status": progress.status,
        "completed": progress.completed,
        "total": progress.total,
        "errors": errors,
    }


@router.get("/{project_id}/synthesis-manifest")
def get_synthesis_manifest(request: Request, project_id: str) -> dict[str, Any]:
    from caption_helper.tts.synthesizer import load_synthesis_manifest

    manifest = load_synthesis_manifest(_project_dir(request, project_id))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No synthesis manifest")
    return manifest


@router.get("/{project_id}/segments/{filename}")
def get_segment_audio(request: Request, project_id: str, filename: str) -> FileResponse:
    path = _project_dir(request, project_id) / "segments" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Segment not found")
    return FileResponse(path, media_type="audio/wav", filename=filename)


@router.get("/{project_id}/tts-segments/{filename}")
def get_tts_segment_audio(request: Request, project_id: str, filename: str) -> FileResponse:
    path = _project_dir(request, project_id) / "tts_segments" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="TTS segment not found")
    return FileResponse(path, media_type="audio/wav", filename=filename)


@router.post("/{project_id}/remux", status_code=202)
async def start_remux(request: Request, project_id: str) -> dict[str, Any]:
    return await _start_remux(request, project_id)


async def _start_remux(request: Request, project_id: str) -> dict[str, Any]:
    project_dir = _project_dir(request, project_id)
    if not (project_dir / "audio.wav").is_file():
        raise HTTPException(status_code=400, detail="Project audio not ready")

    cues = load_subtitles(project_dir / "subtitles.json")
    try:
        validate_clips(cues, project_dir)
    except MissingTTSClipsError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": "Modified cues missing TTS clips", "missing": exc.missing},
        ) from exc

    meta = _store(request).get_project(project_id)
    if meta.status == "remuxing":
        raise HTTPException(status_code=409, detail="Remux already in progress")

    await _jobs(request).enqueue_remux(project_id)
    return {"status": "remuxing"}


@router.get("/{project_id}/remux-status")
def remux_status(request: Request, project_id: str) -> dict[str, Any]:
    meta = _store(request).get_project(project_id)
    progress = _jobs(request).get_remux_progress(project_id)
    status = meta.status if meta.status.startswith("remux") else progress.status
    return {
        "status": status,
        "stage": progress.stage,
        "error": progress.error or meta.error,
    }


@router.get("/{project_id}/remux-manifest")
def get_remux_manifest(request: Request, project_id: str) -> dict[str, Any]:
    manifest = load_remux_manifest(_project_dir(request, project_id))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No remux manifest")
    return manifest


@router.get("/{project_id}/output-video")
def stream_output_video(request: Request, project_id: str) -> FileResponse:
    path = _project_dir(request, project_id) / "output_video.mp4"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Output video not ready")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="output_video.mp4",
        content_disposition_type="attachment",
    )


@router.get("/{project_id}/output-audio")
def stream_output_audio(request: Request, project_id: str) -> FileResponse:
    path = _project_dir(request, project_id) / "output_audio.wav"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Output audio not ready")
    return FileResponse(path, media_type="audio/wav", filename="output_audio.wav")


@router.get("/{project_id}/video")
def stream_video(request: Request, project_id: str) -> FileResponse:
    try:
        video = _store(request).find_source_video(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media_type = mimetypes.guess_type(video.name)[0] or "video/mp4"
    return FileResponse(video, media_type=media_type, filename=video.name)


def _project_dir(request: Request, project_id: str) -> Path:
    try:
        return _store(request).project_path(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
