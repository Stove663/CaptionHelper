import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  RerunAction,
  availableRerunActions,
  deleteProject,
  downloadOutputVideo,
  isProjectProcessing,
  listProjects,
  Project,
  rerunAsr,
  rerunReferences,
  rerunRemux,
  rerunSynthesis,
  uploadVideo,
} from "../api";

const RERUN_LABELS: Record<RerunAction, string> = {
  asr: "重跑 ASR",
  references: "重建参考音库",
  synthesis: "重新合成",
  remux: "重新 remux",
};

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [rerunningId, setRerunningId] = useState<string | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setProjects(await listProjects());
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [refresh]);

  const onDownload = async (projectId: string) => {
    setDownloadingId(projectId);
    setError(null);
    try {
      await downloadOutputVideo(projectId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "下载失败");
    } finally {
      setDownloadingId(null);
    }
  };

  const onRerun = async (projectId: string, action: RerunAction) => {
    if (action === "asr") {
      const ok = window.confirm(
        "重跑 ASR 将删除所有字幕、编辑与下游合成结果，是否继续？",
      );
      if (!ok) return;
    }
    setRerunningId(projectId);
    setError(null);
    setOpenMenuId(null);
    try {
      if (action === "asr") await rerunAsr(projectId);
      else if (action === "references") await rerunReferences(projectId);
      else if (action === "synthesis") await rerunSynthesis(projectId);
      else await rerunRemux(projectId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "重跑失败");
    } finally {
      setRerunningId(null);
    }
  };

  const onDelete = async (projectId: string) => {
    const ok = window.confirm(
      "将永久删除该任务及所有相关文件，无法恢复。是否继续？",
    );
    if (!ok) return;
    setDeletingId(projectId);
    setError(null);
    setOpenMenuId(null);
    try {
      await deleteProject(projectId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeletingId(null);
    }
  };

  const onFile = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      await uploadVideo(file);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <section
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files[0];
          if (file) onFile(file);
        }}
      >
        <p>拖拽视频到此处，或选择文件上传（ASR：FunASR）</p>
        <input
          type="file"
          accept="video/*,.mp4,.mov,.mkv"
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
          }}
        />
        {uploading && <p className="muted">上传中…</p>}
        {error && <p className="error">{error}</p>}
      </section>

      <table className="project-table">
        <thead>
          <tr>
            <th>文件名</th>
            <th>状态</th>
            <th>创建时间</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => {
            const processing = isProjectProcessing(p.status);
            const rerunActions = availableRerunActions(p.status);
            const busy = rerunningId === p.id || deletingId === p.id || processing;
            return (
              <tr key={p.id}>
                <td>{p.filename}</td>
                <td>
                  <span className={`badge badge-${p.status}`}>{p.status}</span>
                </td>
                <td>{new Date(p.created_at).toLocaleString()}</td>
                <td className="project-actions">
                  {p.status === "ready" ||
                  p.status === "remux_ready" ||
                  p.status === "synthesis_ready" ||
                  p.status === "synthesis_failed" ||
                  p.status === "remux_failed" ? (
                    <>
                      <Link to={`/projects/${p.id}/edit`}>编辑</Link>
                      {p.status === "remux_ready" && (
                        <>
                          {" · "}
                          <button
                            type="button"
                            className="link-button"
                            disabled={downloadingId === p.id}
                            onClick={() => onDownload(p.id)}
                          >
                            {downloadingId === p.id ? "下载中…" : "下载"}
                          </button>
                        </>
                      )}
                    </>
                  ) : processing ? (
                    <span className="muted">处理中</span>
                  ) : p.status === "failed" ? (
                    <span className="muted">失败</span>
                  ) : (
                    <span className="muted">处理中</span>
                  )}
                  {rerunActions.length > 0 && (
                    <div className="rerun-menu">
                      <button
                        type="button"
                        className="link-button"
                        disabled={busy}
                        onClick={() =>
                          setOpenMenuId((id) => (id === p.id ? null : p.id))
                        }
                      >
                        {busy ? "重跑中…" : "重跑 ▾"}
                      </button>
                      {openMenuId === p.id && !busy && (
                        <div className="rerun-dropdown">
                          {rerunActions.map((action) => (
                            <button
                              key={action}
                              type="button"
                              onClick={() => onRerun(p.id, action)}
                            >
                              {RERUN_LABELS[action]}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <button
                    type="button"
                    className="link-button delete-button"
                    disabled={busy}
                    onClick={() => onDelete(p.id)}
                  >
                    {deletingId === p.id ? "删除中…" : "删除"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
