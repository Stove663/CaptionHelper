import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Cue,
  downloadOutputAudio,
  downloadOutputVideo,
  formatMs,
  getProject,
  getRemuxStatus,
  getRemuxWarnings,
  getSubtitles,
  outputVideoUrl,
  rerunRemux,
  videoUrl,
} from "../api";

type VideoSource = "original" | "output";

export default function PreviewPage() {
  const { id = "" } = useParams();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState("loading");
  const [remuxStage, setRemuxStage] = useState("");
  const [remuxing, setRemuxing] = useState(false);
  const [videoSource, setVideoSource] = useState<VideoSource>("output");
  const [cues, setCues] = useState<Cue[]>([]);
  const [activeCue, setActiveCue] = useState<Cue | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [outputReady, setOutputReady] = useState(false);
  const [syncMode, setSyncMode] = useState("fixed-slot");
  const [remuxWarnings, setRemuxWarnings] = useState<string[]>([]);
  const [showWarningDialog, setShowWarningDialog] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const canBuild =
    status === "ready" ||
    status === "synthesis_ready" ||
    status === "synthesis_failed" ||
    status === "remux_ready" ||
    status === "remux_failed";

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const project = await getProject(id);
      if (cancelled) return;
      setStatus(project.status);
      setSyncMode(project.sync_mode === "natural-pace" ? "natural-pace" : "fixed-slot");
      setOutputReady(project.status === "remux_ready");
      if (project.error && project.status === "remux_failed") {
        setMessage(project.error);
      }
      try {
        const data = await getSubtitles(id);
        if (!cancelled) setCues(data.cues);
      } catch {
        /* subtitles may not exist yet */
      }
    };
    load();
    const timer = setInterval(async () => {
      const project = await getProject(id);
      if (cancelled) return;
      setStatus(project.status);
      if (project.status === "remuxing") {
        const remux = await getRemuxStatus(id);
        setRemuxStage(remux.stage);
      }
      if (project.status === "remux_ready") {
        setOutputReady(true);
        setRemuxing(false);
        setMessage("输出视频已就绪");
      }
      if (project.status === "remux_failed") {
        setRemuxing(false);
        setMessage(project.error ?? "合成输出失败");
      }
    }, 1500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [id]);

  useEffect(() => {
    if (videoSource === "output" && !outputReady) {
      setVideoSource("original");
    }
  }, [outputReady, videoSource]);

  const onTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;
    const t = video.currentTime * 1000;
    const current = cues.find((c) => t >= c.start_ms && t <= c.end_ms);
    setActiveCue(current ?? null);
  };

  const runRemux = async (skipWarningCheck = false) => {
    if (!skipWarningCheck && syncMode === "natural-pace") {
      try {
        const { warnings } = await getRemuxWarnings(id);
        if (warnings.length > 0) {
          setRemuxWarnings(warnings);
          setShowWarningDialog(true);
          return;
        }
      } catch {
        /* proceed without warnings */
      }
    }
    setRemuxing(true);
    setMessage(null);
    setShowWarningDialog(false);
    try {
      await rerunRemux(id);
      setStatus("remuxing");
      setRemuxStage("assembling");
    } catch (e) {
      setRemuxing(false);
      setMessage(e instanceof Error ? e.message : "启动输出失败");
    }
  };

  const onDownloadVideo = async () => {
    setDownloading(true);
    setMessage(null);
    try {
      await downloadOutputVideo(id);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "下载失败");
    } finally {
      setDownloading(false);
    }
  };

  const onDownloadAudio = async () => {
    setDownloading(true);
    setMessage(null);
    try {
      await downloadOutputAudio(id);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "下载失败");
    } finally {
      setDownloading(false);
    }
  };

  const stageLabel =
    remuxStage === "assembling"
      ? "正在组装音频…"
      : remuxStage === "muxing"
        ? "正在封装视频…"
        : remuxing
          ? "处理中…"
          : "";

  const videoSrc = videoSource === "output" && outputReady ? outputVideoUrl(id) : videoUrl(id);

  if (!canBuild && status !== "remuxing") {
    return (
      <div className="panel">
        <p>项目尚未就绪：{status}</p>
        <Link to={`/projects/${id}/edit`}>返回编辑</Link>
      </div>
    );
  }

  return (
    <div className="preview">
      <div className="editor-toolbar">
        <Link to={`/projects/${id}/edit`}>← 返回编辑</Link>
        <span className="badge">
          {syncMode === "natural-pace" ? "自然语速" : "固定槽位"}
        </span>
        <button onClick={() => runRemux()} disabled={remuxing}>
          {remuxing ? "生成中…" : outputReady ? "重新 remux" : "生成输出视频"}
        </button>
        <div className="toggle-group">
          <button
            type="button"
            className={videoSource === "original" ? "toggle active" : "toggle"}
            onClick={() => setVideoSource("original")}
          >
            原视频
          </button>
          <button
            type="button"
            className={videoSource === "output" ? "toggle active" : "toggle"}
            onClick={() => setVideoSource("output")}
            disabled={!outputReady}
          >
            输出视频
          </button>
        </div>
        {outputReady && (
          <button type="button" onClick={onDownloadVideo} disabled={downloading}>
            {downloading ? "下载中…" : "下载视频"}
          </button>
        )}
        {stageLabel && <span className="muted">{stageLabel}</span>}
        {message && <span className="muted">{message}</span>}
      </div>

      {showWarningDialog && (
        <div className="warning-dialog">
          <p>以下片段需要较大慢动作，视频可能不自然：</p>
          <ul>
            {remuxWarnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          <div className="warning-actions">
            <button type="button" onClick={() => setShowWarningDialog(false)}>
              取消
            </button>
            <button type="button" onClick={() => runRemux(true)}>
              仍然生成
            </button>
          </div>
        </div>
      )}

      <div className="preview-body">
        <div className="video-pane preview-video">
          <video
            ref={videoRef}
            key={videoSrc}
            src={videoSrc}
            controls
            onTimeUpdate={onTimeUpdate}
          />
          {activeCue && (
            <div className="subtitle-overlay">
              <span className="subtitle-speaker">说话人 {activeCue.spk}</span>
              <span>{activeCue.text_edited}</span>
            </div>
          )}
        </div>

        {outputReady && (
          <div className="download-links">
            <button type="button" onClick={onDownloadAudio} disabled={downloading}>
              下载 output_audio.wav
            </button>
          </div>
        )}

        <div className="cue-timeline muted">
          {cues.length > 0 && (
            <p>
              共 {cues.length} 条字幕，{cues.filter((c) => c.modified).length} 条已修改
            </p>
          )}
          {activeCue && (
            <p>
              当前 #{activeCue.index} · {formatMs(activeCue.start_ms)} –{" "}
              {formatMs(activeCue.end_ms)}
              {activeCue.modified && <span className="badge-modified"> 已修改</span>}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
