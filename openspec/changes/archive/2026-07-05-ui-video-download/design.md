## Context

CaptionHelper 的合成流程在 remux 完成后于项目目录生成 `output_video.mp4`。后端已有 `GET /api/projects/{id}/output-video`（`FileResponse`），预览页 `PreviewPage.tsx` 在 `outputReady` 时渲染侧边 `<a href download>` 链接。但该入口不够醒目，且纯锚点下载在部分浏览器中可能内联播放视频而非保存；`output-preview` 变更中的下载需求尚未归档到主 spec。

当前相关代码：

- 后端：`src/caption_helper/web/routes/projects.py` — `stream_output_video`
- 前端：`frontend/src/pages/PreviewPage.tsx` — `.download-links` 区域
- API 辅助：`frontend/src/api.ts` — `outputVideoUrl()`

## Goals / Non-Goals

**Goals:**

- 预览页工具栏提供醒目的「下载视频」按钮
- 通过 `fetch` + Blob 实现跨浏览器一致的保存行为
- API 显式返回 `Content-Disposition: attachment`
- 首页项目列表对 `remux_ready` 项目显示快捷下载
- 下载中/失败的用户反馈

**Non-Goals:**

- 打包 zip（视频 + 音频 + 字幕）导出
- 自定义输出文件名 UI 或格式转码
- 断点续传或分片下载
- 移除现有音频下载链接（保留，与视频并列）

## Decisions

### 1. 下载实现：程序化 Blob 下载

**选择：** 在 `api.ts` 新增 `downloadOutputVideo(projectId, filename?)`：

```typescript
export async function downloadOutputVideo(id: string, filename = "output_video.mp4"): Promise<void> {
  const res = await fetch(outputVideoUrl(id));
  if (!res.ok) throw new Error("下载失败");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

**理由：** 不依赖 `<a download>` 对同源 API 的浏览器差异；视频播放器仍用 `outputVideoUrl` 流式 URL，下载走独立路径。

**备选：** 仅依赖 `Content-Disposition: attachment` + 普通链接 — 拒绝，Safari/Chrome 对 `video/mp4` 仍可能内联打开。

### 2. 后端 Content-Disposition

**选择：** `FileResponse(path, media_type="video/mp4", filename="output_video.mp4", content_disposition_type="attachment")`（Starlette 参数）。

**理由：** 双保险：即使直接打开 API URL 也触发下载；与前端 Blob 方案互补。

### 3. 预览页 UI 布局

**选择：** 在 `editor-toolbar` 内、视频源切换按钮旁增加 `<button type="button">下载视频</button>`，仅 `outputReady` 时启用；保留或精简现有 `.download-links` 区域（音频链保留，视频链可改为调用同一 helper 或移除重复）。

**理由：** 与「生成输出」「原视频/输出视频」切换同一视觉层级，符合用户完成合成后的首要操作。

### 4. 首页快捷下载

**选择：** `HomePage` 项目表操作列： `remux_ready` 显示「下载」链接/按钮，点击调用 `downloadOutputVideo(p.id)`；其他状态不显示。

**理由：** 用户无需进入预览页即可取回成品；改动面小。

### 5. 加载与错误状态

**选择：** 组件本地 `downloading` boolean；按钮文案切换为「下载中…」；`catch` 后 `setMessage` 显示错误（复用预览页现有 `message` 区域）。

**理由：** 大文件 fetch 可能耗时，需防重复点击。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 大视频一次性加载到内存 | 本地工具场景文件通常可接受；未来可加 `Content-Length` 进度条 |
| 重复下载浪费带宽 | 下载中禁用按钮 |
| `remux_ready` 但文件被手动删除 | API 404，前端显示错误 |
| 首页轮询与下载并发 | 无状态 GET，无副作用 |

## Migration Plan

1. 后端加 `content_disposition_type="attachment"`（向后兼容，无数据迁移）
2. 前端加 helper 与 UI 按钮
3. 补充 `test_web.py` 断言 `Content-Disposition` 头
4. 无需配置或数据库变更；回滚即还原 UI 与响应头

## Open Questions

- 下载文件名是否使用源视频名派生（如 `my_clip_output.mp4`）— 首版固定 `output_video.mp4`，后续可从 `project.filename` 派生
