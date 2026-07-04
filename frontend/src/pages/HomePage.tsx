import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProjects, Project, uploadVideo } from "../api";

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setProjects(await listProjects());
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [refresh]);

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
        <p>拖拽视频到此处，或选择文件上传</p>
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
          {projects.map((p) => (
            <tr key={p.id}>
              <td>{p.filename}</td>
              <td>
                <span className={`badge badge-${p.status}`}>{p.status}</span>
              </td>
              <td>{new Date(p.created_at).toLocaleString()}</td>
              <td>
                {p.status === "ready" ? (
                  <Link to={`/projects/${p.id}/edit`}>编辑</Link>
                ) : (
                  <span className="muted">处理中</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
