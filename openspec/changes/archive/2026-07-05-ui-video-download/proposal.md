## Why

合成流程完成后，用户需要将带新配音与字幕的最终视频保存到本地。预览页虽已能播放 `output_video.mp4`，但缺少明确、可靠的下载入口；现有侧边文字链接易被忽略，且浏览器对 `<a download>` 配合流媒体响应的行为不一致，可能导致内联播放而非保存文件。需要把「下载最终视频」作为一等功能纳入 Web UI 规范。

## What Changes

- 在预览页工具栏增加醒目的「下载视频」按钮，输出就绪后可用
- 提供可靠的客户端下载实现（`fetch` + Blob + 程序化触发保存），不依赖浏览器对 `download` 属性的隐式行为
- API 响应为 `output_video.mp4` 设置 `Content-Disposition: attachment`，确保各浏览器一致触发下载
- 项目列表页对 `remux_ready` 状态的项目提供快捷下载链接
- 下载进行中显示加载状态；文件未就绪时禁用按钮并给出提示
- 可选保留音频下载链接，与视频下载并列

## Capabilities

### New Capabilities

- `output-video-download`: Web UI 与 API 对最终合成视频（`output_video.mp4`）的可靠下载能力，含预览页按钮、项目列表快捷入口及附件响应头

### Modified Capabilities

- `web-ui-server`: 补充 `GET /api/projects/{id}/output-video` 必须以附件形式响应、供浏览器保存文件的要求

## Impact

- **前端**: `PreviewPage.tsx`、`HomePage.tsx`、`api.ts`（新增 `downloadOutputVideo` 辅助函数）
- **后端**: `src/caption_helper/web/routes/projects.py`（`stream_output_video` 显式 `Content-Disposition: attachment`）
- **测试**: `tests/test_web.py` 断言响应头与下载端点行为
- **依赖**: 无新依赖
