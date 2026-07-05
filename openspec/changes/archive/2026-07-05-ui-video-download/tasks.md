## 1. 后端 API

- [x] 1.1 在 `stream_output_video` 的 `FileResponse` 中显式设置 `content_disposition_type="attachment"` 与 `filename="output_video.mp4"`
- [x] 1.2 在 `tests/test_web.py` 的 remux 测试中断言 `GET /output-video` 响应含 `content-disposition: attachment`

## 2. 前端下载辅助

- [x] 2.1 在 `frontend/src/api.ts` 新增 `downloadOutputVideo(id, filename?)`，使用 fetch + Blob + 程序化点击触发保存
- [x] 2.2 可选：新增 `downloadOutputAudio` 复用相同模式，供音频链接使用

## 3. 预览页 UI

- [x] 3.1 在 `PreviewPage.tsx` 工具栏添加「下载视频」按钮，仅 `outputReady` 时启用
- [x] 3.2 实现 `downloading` 状态：下载中禁用按钮并显示「下载中…」
- [x] 3.3 下载失败时在现有 `message` 区域显示错误
- [x] 3.4 将侧边 `.download-links` 中的视频链接改为调用 `downloadOutputVideo`（或移除重复，保留音频链接）

## 4. 首页快捷下载

- [x] 4.1 在 `HomePage.tsx` 项目表操作列：状态为 `remux_ready` 时显示「下载」按钮
- [x] 4.2 点击调用 `downloadOutputVideo`，处理加载与错误反馈

## 5. 验证

- [x] 5.1 运行 `pytest tests/test_web.py` 确认通过
- [x] 5.2 手动验证：remux 完成后预览页与首页均可保存 `output_video.mp4`
