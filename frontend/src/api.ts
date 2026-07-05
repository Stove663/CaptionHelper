export type Project = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  error?: string | null;
  sync_mode?: string;
  tts_provider?: "moss-tts" | "glm-tts";
};

export type CompressionRiskCue = {
  index: number;
  text_edited: string;
  slot_ms: number;
  estimated_ms: number;
  compression_ratio: number;
  at_risk: boolean;
  cjk_chars: number;
  latin_chars: number;
};

export type TimelineData = {
  sync_mode: string;
  duration_delta_ms: number;
  cues: {
    index: number;
    start_ms_orig: number;
    end_ms_orig: number;
    start_ms_adj: number;
    end_ms_adj: number;
    delta_ms: number;
  }[];
};

export type Cue = {
  index: number;
  spk: number;
  start_ms: number;
  end_ms: number;
  text_original: string;
  text_edited: string;
  modified: boolean;
};

export type ReferenceCueReport = {
  index: number;
  spk: number;
  status: "adequate" | "fallback" | "unavailable";
  reference_source?: string | null;
  reference_path?: string | null;
  fallback_reason?: string | null;
};

export type ReferenceQualityReport = {
  speakers: Record<string, unknown>;
  cues: ReferenceCueReport[];
  unavailable: number[];
  same_speaker_segments: Record<
    string,
    { cue_index: number; path: string; duration_ms: number; quality_score: number; adequate: boolean }[]
  >;
};

export type SynthesisStatus = {
  status: string;
  completed: number;
  total: number;
  errors: { index: number | null; error: string }[];
};

export type SynthesisManifestCue = {
  index: number;
  status: string;
  output_path?: string;
  error?: string;
  reference_segment?: string;
  reference_source?: string;
  reference_fallback_reason?: string;
  tokens?: number;
};

export type SynthesisManifest = {
  tts_provider?: "moss-tts" | "glm-tts";
  completed?: number;
  cues: SynthesisManifestCue[];
};

export type RemuxStatus = {
  status: string;
  stage: string;
  error?: string | null;
};

export async function setSyncMode(id: string, syncMode: string): Promise<Project> {
  const res = await fetch(`/api/projects/${id}/sync-mode`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sync_mode: syncMode }),
  });
  if (!res.ok) throw new Error("Failed to set sync mode");
  return res.json();
}

export async function setTtsProvider(
  id: string,
  ttsProvider: "moss-tts" | "glm-tts",
): Promise<Project> {
  const res = await fetch(`/api/projects/${id}/tts-provider`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tts_provider: ttsProvider }),
  });
  if (!res.ok) throw new Error("Failed to set TTS provider");
  return res.json();
}

export async function getCompressionRisk(
  id: string,
): Promise<{ at_risk_count: number; cues: CompressionRiskCue[] }> {
  const res = await fetch(`/api/projects/${id}/compression-risk`);
  if (!res.ok) throw new Error("Failed to load compression risk");
  return res.json();
}

export async function getTimeline(id: string): Promise<TimelineData | null> {
  const res = await fetch(`/api/projects/${id}/timeline`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to load timeline");
  return res.json();
}

export async function getRemuxWarnings(
  id: string,
): Promise<{ warnings: string[]; sync_mode: string }> {
  const res = await fetch(`/api/projects/${id}/remux-warnings`);
  if (!res.ok) throw new Error("Failed to load remux warnings");
  return res.json();
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch("/api/projects");
  if (!res.ok) throw new Error("Failed to list projects");
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`/api/projects/${id}`);
  if (!res.ok) throw new Error("Project not found");
  return res.json();
}

export async function uploadVideo(file: File): Promise<Project> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/projects", { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function getSubtitles(id: string): Promise<{ cues: Cue[] }> {
  const res = await fetch(`/api/projects/${id}/subtitles`);
  if (!res.ok) throw new Error("Subtitles not ready");
  return res.json();
}

export async function getModifiedSegments(id: string): Promise<unknown[]> {
  const res = await fetch(`/api/projects/${id}/modified-segments`);
  if (!res.ok) throw new Error("Failed to load modified segments");
  return res.json();
}

export async function getReferenceQuality(id: string): Promise<ReferenceQualityReport> {
  const res = await fetch(`/api/projects/${id}/reference-quality`);
  if (!res.ok) throw new Error("Failed to load reference quality");
  return res.json();
}

export async function setCueReference(
  id: string,
  cueIndex: number,
  segmentPath: string,
): Promise<void> {
  const res = await fetch(`/api/projects/${id}/cues/${cueIndex}/reference`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment_path: segmentPath }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to set reference");
  }
}

export async function saveSubtitles(id: string, cues: Cue[]): Promise<void> {
  const res = await fetch(`/api/projects/${id}/subtitles`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cues }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Save failed");
  }
}

export async function startSynthesis(
  id: string,
  options?: { skipUnavailable?: boolean; syncMode?: string },
): Promise<{ status: string; total: number; sync_mode?: string }> {
  const res = await fetch(`/api/projects/${id}/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      skip_unavailable: options?.skipUnavailable ?? false,
      sync_mode: options?.syncMode,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    if (typeof detail === "object" && detail?.message) {
      throw new Error(detail.message);
    }
    throw new Error(typeof detail === "string" ? detail : "Synthesis failed to start");
  }
  return res.json();
}

export async function getSynthesisStatus(id: string): Promise<SynthesisStatus> {
  const res = await fetch(`/api/projects/${id}/synthesis-status`);
  if (!res.ok) throw new Error("Failed to get synthesis status");
  return res.json();
}

export async function getSynthesisManifest(id: string): Promise<SynthesisManifest | null> {
  const res = await fetch(`/api/projects/${id}/synthesis-manifest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to load synthesis manifest");
  return res.json();
}

export async function startRemux(id: string): Promise<{ status: string }> {
  const res = await fetch(`/api/projects/${id}/remux`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    if (typeof detail === "object" && detail?.message) {
      throw new Error(detail.message);
    }
    throw new Error(typeof detail === "string" ? detail : "Remux failed to start");
  }
  return res.json();
}

export async function getRemuxStatus(id: string): Promise<RemuxStatus> {
  const res = await fetch(`/api/projects/${id}/remux-status`);
  if (!res.ok) throw new Error("Failed to get remux status");
  return res.json();
}

export function videoUrl(id: string): string {
  return `/api/projects/${id}/video`;
}

export function outputVideoUrl(id: string): string {
  return `/api/projects/${id}/output-video`;
}

export function outputAudioUrl(id: string): string {
  return `/api/projects/${id}/output-audio`;
}

async function downloadFile(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error("下载失败");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadOutputVideo(
  id: string,
  filename = "output_video.mp4",
): Promise<void> {
  await downloadFile(outputVideoUrl(id), filename);
}

export async function downloadOutputAudio(
  id: string,
  filename = "output_audio.wav",
): Promise<void> {
  await downloadFile(outputAudioUrl(id), filename);
}

export function segmentUrl(id: string, filename: string): string {
  return `/api/projects/${id}/segments/${filename}`;
}

export function ttsSegmentUrl(id: string, filename: string): string {
  return `/api/projects/${id}/tts-segments/${filename}`;
}

export function formatMs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${rem.toString().padStart(2, "0")}`;
}

export function segmentFilename(cue: Cue): string {
  const pad = String(cue.index).padStart(4, "0");
  return `${pad}_spk${cue.spk}_${cue.start_ms}-${cue.end_ms}.wav`;
}

export function refStatusLabel(status: ReferenceCueReport["status"]): string {
  if (status === "adequate") return "参考音频 OK";
  if (status === "fallback") return "将使用备用参考";
  return "无可用参考";
}
