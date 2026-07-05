import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Cue,
  ReferenceCueReport,
  ReferenceQualityReport,
  RerunAction,
  SynthesisManifestCue,
  availableRerunActions,
  formatMs,
  getCompressionRisk,
  getModifiedSegments,
  getProject,
  getReferenceQuality,
  getSubtitles,
  getSynthesisManifest,
  getSynthesisStatus,
  getTimeline,
  isProjectProcessing,
  refStatusLabel,
  rerunAsr,
  rerunReferences,
  rerunSynthesis,
  saveSubtitles,
  segmentFilename,
  segmentUrl,
  setCueReference,
  setSyncMode,
  setTtsProvider,
  startSynthesis,
  ttsSegmentUrl,
  videoUrl,
} from "../api";

const RERUN_LABELS: Record<RerunAction, string> = {
  asr: "重跑 ASR",
  references: "重建参考音库",
  synthesis: "重新合成",
  remux: "重新 remux",
};

export default function EditorPage() {
  const { id = "" } = useParams();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState("loading");
  const [cues, setCues] = useState<Cue[]>([]);
  const [modifiedCount, setModifiedCount] = useState(0);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [synthesizing, setSynthesizing] = useState(false);
  const [synthProgress, setSynthProgress] = useState({ completed: 0, total: 0 });
  const [manifestByCue, setManifestByCue] = useState<Record<number, SynthesisManifestCue>>({});
  const [refByCue, setRefByCue] = useState<Record<number, ReferenceCueReport>>({});
  const [refReport, setRefReport] = useState<ReferenceQualityReport | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [syncMode, setSyncModeState] = useState<"fixed-slot" | "natural-pace">("fixed-slot");
  const [ttsProvider, setTtsProviderState] = useState<"moss-tts" | "glm-tts">("moss-tts");
  const [lastSynthProvider, setLastSynthProvider] = useState<"moss-tts" | "glm-tts" | null>(
    null,
  );
  const [compressionRiskCount, setCompressionRiskCount] = useState(0);
  const [codeMixedRecommendCount, setCodeMixedRecommendCount] = useState(0);
  const [codeMixedModifiedCount, setCodeMixedModifiedCount] = useState(0);
  const [providerGuidance, setProviderGuidance] = useState<string | null>(null);
  const [durationDeltaMs, setDurationDeltaMs] = useState<number | null>(null);
  const [rerunning, setRerunning] = useState(false);
  const prevStatusRef = useRef("loading");

  const editable =
    status === "ready" ||
    status === "synthesis_ready" ||
    status === "synthesis_failed" ||
    status === "remux_ready" ||
    status === "remux_failed";
  const unavailableCount = refReport?.unavailable.length ?? 0;

  const loadManifest = async () => {
    const manifest = await getSynthesisManifest(id);
    if (!manifest) return;
    const byIndex: Record<number, SynthesisManifestCue> = {};
    for (const entry of manifest.cues) {
      byIndex[entry.index] = entry;
    }
    setManifestByCue(byIndex);
    if (manifest.tts_provider === "glm-tts" || manifest.tts_provider === "moss-tts") {
      setLastSynthProvider(manifest.tts_provider);
    }
    if (manifest.fallback_count && manifest.fallback_count > 0) {
      setMessage(`合成完成（${manifest.fallback_count} 个片段使用了备用参考音频）`);
    }
  };

  const loadReferenceQuality = async () => {
    try {
      const report = await getReferenceQuality(id);
      setRefReport(report);
      const byIndex: Record<number, ReferenceCueReport> = {};
      for (const entry of report.cues) {
        byIndex[entry.index] = entry;
      }
      setRefByCue(byIndex);
    } catch {
      setRefReport(null);
      setRefByCue({});
    }
  };

  const loadCompressionRisk = async () => {
    try {
      const report = await getCompressionRisk(id);
      setCompressionRiskCount(report.at_risk_count);
      setCodeMixedModifiedCount(report.code_mixed_modified_count);
      setProviderGuidance(report.provider_guidance);
      setCodeMixedRecommendCount(
        report.cues.filter((c) => c.recommend_natural_pace).length,
      );
    } catch {
      setCompressionRiskCount(0);
      setCodeMixedRecommendCount(0);
      setCodeMixedModifiedCount(0);
      setProviderGuidance(null);
    }
  };

  const loadTimelinePreview = async () => {
    const timeline = await getTimeline(id);
    if (timeline) setDurationDeltaMs(timeline.duration_delta_ms);
  };

  const loadEditorData = async () => {
    const data = await getSubtitles(id);
    const modified = await getModifiedSegments(id);
    setCues(data.cues);
    setModifiedCount(modified.length);
    await loadReferenceQuality();
    await loadManifest();
    await loadCompressionRisk();
    await loadTimelinePreview();
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const project = await getProject(id);
      setStatus(project.status);
      setSyncModeState(
        project.sync_mode === "natural-pace" ? "natural-pace" : "fixed-slot",
      );
      setTtsProviderState(project.tts_provider === "glm-tts" ? "glm-tts" : "moss-tts");
      prevStatusRef.current = project.status;
      if (project.status === "ready" || project.status.startsWith("synthesis")) {
        if (cues.length === 0) {
          await loadEditorData();
        } else {
          await loadReferenceQuality();
          await loadManifest();
          await loadCompressionRisk();
          await loadTimelinePreview();
        }
      }
    };
    load();
    const timer = setInterval(async () => {
      const project = await getProject(id);
      const prev = prevStatusRef.current;
      setStatus(project.status);
      if (
        prev !== project.status &&
        project.status === "ready" &&
        (prev === "building_references" ||
          prev === "extracting" ||
          prev === "transcribing" ||
          prev === "splitting")
      ) {
        if (prev === "building_references") {
          await loadReferenceQuality();
          if (!cancelled) setMessage("参考音库已重建，请重新合成");
        } else {
          setManifestByCue({});
          setLastSynthProvider(null);
          await loadEditorData();
          if (!cancelled) setMessage("ASR 已完成，字幕已更新");
        }
      }
      prevStatusRef.current = project.status;
      if (
        (project.status === "ready" || project.status.startsWith("synthesis")) &&
        cues.length === 0
      ) {
        const data = await getSubtitles(id);
        const modified = await getModifiedSegments(id);
        if (!cancelled) {
          setCues(data.cues);
          setModifiedCount(modified.length);
        }
      }
      if (project.status === "synthesizing") {
        const synth = await getSynthesisStatus(id);
        setSynthProgress({ completed: synth.completed, total: synth.total });
      }
      if (project.status === "synthesis_ready" || project.status === "synthesis_failed") {
        await loadManifest();
        await loadTimelinePreview();
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [id, cues.length]);

  const seekTo = (cue: Cue) => {
    setActiveIndex(cue.index);
    const video = videoRef.current;
    if (video) video.currentTime = cue.start_ms / 1000;
  };

  const onTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;
    const t = video.currentTime * 1000;
    const current = cues.find((c) => t >= c.start_ms && t <= c.end_ms);
    setActiveIndex(current?.index ?? null);
  };

  const updateText = (index: number, text: string) => {
    setCues((prev) =>
      prev.map((c) => (c.index === index ? { ...c, text_edited: text } : c)),
    );
  };

  const onSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await saveSubtitles(id, cues);
      const data = await getSubtitles(id);
      const modified = await getModifiedSegments(id);
      setCues(data.cues);
      setModifiedCount(modified.length);
      await loadReferenceQuality();
      await loadCompressionRisk();
      setMessage("已保存");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const runSynthesis = async (skipUnavailable: boolean) => {
    setSynthesizing(true);
    setMessage(null);
    try {
      const res = await startSynthesis(id, { skipUnavailable, syncMode });
      setStatus("synthesizing");
      setSynthProgress({ completed: 0, total: res.total });
      if (res.sync_mode) {
        setSyncModeState(res.sync_mode === "natural-pace" ? "natural-pace" : "fixed-slot");
      }
      const poll = setInterval(async () => {
        const project = await getProject(id);
        const synth = await getSynthesisStatus(id);
        setStatus(project.status);
        setSynthProgress({ completed: synth.completed, total: synth.total });
        if (project.status !== "synthesizing") {
          clearInterval(poll);
          setSynthesizing(false);
          await loadManifest();
          await loadTimelinePreview();
          if (project.status !== "synthesis_ready" && !message) {
            setMessage("合成失败，请查看错误详情");
          }
        }
      }, 1500);
    } catch (e) {
      setSynthesizing(false);
      setMessage(e instanceof Error ? e.message : "合成启动失败");
    }
  };

  const onPickReference = async (cueIndex: number, segmentPath: string) => {
    try {
      await setCueReference(id, cueIndex, segmentPath);
      await loadReferenceQuality();
      setMessage(`已设置 cue #${cueIndex} 的参考音频`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "设置参考失败");
    }
  };

  const onSyncModeChange = async (mode: "fixed-slot" | "natural-pace") => {
    try {
      const project = await setSyncMode(id, mode);
      setSyncModeState(project.sync_mode === "natural-pace" ? "natural-pace" : "fixed-slot");
      setMessage(mode === "natural-pace" ? "已切换为自然语速模式" : "已切换为固定槽位模式");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "切换模式失败");
    }
  };

  const onTtsProviderChange = async (provider: "moss-tts" | "glm-tts") => {
    try {
      const project = await setTtsProvider(id, provider);
      setTtsProviderState(project.tts_provider === "glm-tts" ? "glm-tts" : "moss-tts");
      setMessage(provider === "glm-tts" ? "已切换为 GLM-TTS" : "已切换为 MOSS-TTS");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "切换 TTS 失败");
    }
  };

  const onRerun = async (action: RerunAction) => {
    if (action === "asr") {
      const ok = window.confirm(
        "重跑 ASR 将删除所有字幕、编辑与下游合成结果，是否继续？",
      );
      if (!ok) return;
    }
    setRerunning(true);
    setMessage(null);
    try {
      if (action === "asr") await rerunAsr(id);
      else if (action === "references") await rerunReferences(id);
      else await rerunSynthesis(id, { syncMode });
      const project = await getProject(id);
      setStatus(project.status);
      prevStatusRef.current = project.status;
      if (action === "synthesis") {
        setSynthesizing(true);
        setSynthProgress({ completed: 0, total: modifiedCount });
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "重跑失败");
    } finally {
      setRerunning(false);
    }
  };

  const rerunActions = availableRerunActions(status).filter((a) => a !== "remux");
  const pipelineBusy = isProjectProcessing(status) || rerunning || synthesizing;

  if (!editable && status !== "synthesizing") {
    return (
      <div className="panel">
        <p>处理中：{status}</p>
        <Link to="/">返回列表</Link>
      </div>
    );
  }

  return (
    <div className="editor">
      <div className="editor-toolbar">
        <Link to="/">← 返回</Link>
        <span className="muted">ASR: FunASR</span>
        <div className="toggle-group">
          <button
            type="button"
            className={syncMode === "fixed-slot" ? "toggle active" : "toggle"}
            onClick={() => onSyncModeChange("fixed-slot")}
            disabled={synthesizing}
          >
            固定槽位
          </button>
          <button
            type="button"
            className={syncMode === "natural-pace" ? "toggle active" : "toggle"}
            onClick={() => onSyncModeChange("natural-pace")}
            disabled={synthesizing}
          >
            自然语速
          </button>
        </div>
        <div className="toggle-group">
          <button
            type="button"
            className={ttsProvider === "moss-tts" ? "toggle active" : "toggle"}
            onClick={() => onTtsProviderChange("moss-tts")}
            disabled={synthesizing}
          >
            MOSS-TTS
          </button>
          <button
            type="button"
            className={ttsProvider === "glm-tts" ? "toggle active" : "toggle"}
            onClick={() => onTtsProviderChange("glm-tts")}
            disabled={synthesizing}
          >
            GLM-TTS
          </button>
        </div>
        <button onClick={onSave} disabled={saving || synthesizing || rerunning}>
          {saving ? "保存中…" : "保存"}
        </button>
        {rerunActions.length > 0 && (
          <div className="rerun-group">
            {rerunActions.map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => onRerun(action)}
                disabled={pipelineBusy}
              >
                {rerunning ? "重跑中…" : RERUN_LABELS[action]}
              </button>
            ))}
          </div>
        )}
        <button
          onClick={() => runSynthesis(false)}
          disabled={synthesizing || rerunning || modifiedCount === 0 || unavailableCount > 0}
          title={
            unavailableCount > 0
              ? `${unavailableCount} 个片段无可用参考音频`
              : modifiedCount === 0
                ? "请先修改并保存字幕"
                : undefined
          }
        >
          {synthesizing ? "合成中…" : "合成已修改片段"}
        </button>
        {unavailableCount > 0 && (
          <button
            onClick={() => runSynthesis(true)}
            disabled={synthesizing || modifiedCount === 0}
          >
            合成可用片段
          </button>
        )}
        {synthesizing && synthProgress.total > 0 && (
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${(synthProgress.completed / synthProgress.total) * 100}%`,
              }}
            />
            <span className="progress-label">
              {synthProgress.completed}/{synthProgress.total}
            </span>
          </div>
        )}
        {message && <span className="muted">{message}</span>}
        {lastSynthProvider && (
          <span className="muted">
            上次合成引擎：{lastSynthProvider === "glm-tts" ? "GLM-TTS" : "MOSS-TTS"}
          </span>
        )}
        {durationDeltaMs !== null && durationDeltaMs !== 0 && syncMode === "natural-pace" && (
          <span className="muted">
            时间轴延长 {formatMs(Math.abs(durationDeltaMs))}
            {durationDeltaMs > 0 ? "" : "（缩短）"}
          </span>
        )}
        {(status === "synthesis_ready" || status === "remux_ready" || status === "ready") && (
          <Link to={`/projects/${id}/preview`}>预览输出 →</Link>
        )}
      </div>
      {syncMode === "fixed-slot" &&
        (compressionRiskCount > 0 ||
          (ttsProvider === "glm-tts" && codeMixedModifiedCount > 0)) && (
        <div className="compression-banner">
          <span>
            {ttsProvider === "glm-tts" && providerGuidance
              ? providerGuidance
              : codeMixedRecommendCount > 0
                ? `${codeMixedRecommendCount} 个中英混合片段在固定槽位下英文发音可能被压缩，强烈建议切换为`
                : `${compressionRiskCount} 个片段在固定槽位模式下可能被压缩，建议切换为`}
          </span>
          <button type="button" onClick={() => onSyncModeChange("natural-pace")}>
            自然语速
          </button>
        </div>
      )}
      <div className="editor-body">
        <div className="video-pane">
          <video
            ref={videoRef}
            src={videoUrl(id)}
            controls
            onTimeUpdate={onTimeUpdate}
          />
        </div>
        <div className="cue-list">
          {cues.map((cue) => {
            const manifest = manifestByCue[cue.index];
            const refInfo = refByCue[cue.index];
            const segName = segmentFilename(cue);
            const spkOptions = refReport?.same_speaker_segments[String(cue.spk)] ?? [];
            return (
              <div
                key={cue.index}
                className={`cue-item ${activeIndex === cue.index ? "active" : ""}`}
                onClick={() => seekTo(cue)}
              >
                <div className="cue-meta">
                  <span>#{cue.index}</span>
                  <span>说话人 {cue.spk}</span>
                  <span>
                    {formatMs(cue.start_ms)} – {formatMs(cue.end_ms)}
                  </span>
                  {cue.modified && <span className="badge-modified">已修改</span>}
                  {cue.modified && refInfo && (
                    <span className={`badge-ref badge-ref-${refInfo.status}`}>
                      {refStatusLabel(refInfo.status)}
                    </span>
                  )}
                </div>
                <textarea
                  value={cue.text_edited}
                  onChange={(e) => updateText(cue.index, e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  rows={2}
                  disabled={synthesizing}
                />
                {cue.text_edited !== cue.text_original && (
                  <div className="original" title="原文">
                    原文：{cue.text_original}
                  </div>
                )}
                {cue.modified && refInfo?.status === "fallback" && (
                  <div className="ref-detail" onClick={(e) => e.stopPropagation()}>
                    备用参考：{refInfo.reference_path}
                    {refInfo.fallback_reason && (
                      <span className="muted"> ({refInfo.fallback_reason})</span>
                    )}
                  </div>
                )}
                {cue.modified && refInfo?.status === "unavailable" && (
                  <div className="error" onClick={(e) => e.stopPropagation()}>
                    无可用参考：{refInfo.fallback_reason}
                  </div>
                )}
                {cue.modified && spkOptions.length > 0 && (
                  <div className="ref-picker" onClick={(e) => e.stopPropagation()}>
                    <label>
                      手动选择参考：
                      <select
                        defaultValue=""
                        onChange={(e) => {
                          if (e.target.value) onPickReference(cue.index, e.target.value);
                        }}
                      >
                        <option value="">—</option>
                        {spkOptions.map((opt) => (
                          <option key={opt.path} value={opt.path}>
                            #{opt.cue_index} {opt.duration_ms}ms
                            {opt.adequate ? " ✓" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}
                {cue.modified && (
                  <div className="audio-preview" onClick={(e) => e.stopPropagation()}>
                    <audio controls preload="none" src={segmentUrl(id, segName)} />
                    {manifest?.status === "success" && manifest.output_path && (
                      <audio
                        controls
                        preload="none"
                        src={ttsSegmentUrl(id, segName)}
                        title="TTS 合成"
                      />
                    )}
                    {manifest?.status === "failed" && manifest.error && (
                      <div className="error">合成错误：{manifest.error}</div>
                    )}
                    {manifest?.reference_fallback_reason && (
                      <div className="muted">
                        合成参考：{manifest.reference_source} — {manifest.reference_fallback_reason}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
