## Why

上传视频后，若 ASR 识别不准、参考音库质量差、TTS 合成失败或需更换 TTS 引擎，用户目前只能重新上传同一视频才能从头跑流程。TTS 与 remux 虽可在编辑/预览页再次触发，但缺少统一的「重跑环节」入口；ASR 与说话人参考音库（克隆准备）则完全无法在 Web UI 中重跑。需要让用户在保留已上传 `source.*` 的前提下，按需重新执行各处理环节。

## What Changes

- 新增后端 API：对已有项目重跑 ASR 全流程（提取 → 转写 → 切分 → 初始化字幕）、重跑说话人参考音库构建、重跑 TTS 合成、重跑 remux
- 重跑 ASR 时清除并覆盖该项目的字幕、片段、参考音库及下游 TTS/remux 产物，并在操作前要求用户确认
- 重跑参考音库时仅重建 `speaker_refs/`，保留现有字幕与 `segments/`
- 复用并明确现有 TTS/remux 触发端点，统一纳入「重跑」语义（含进行中互斥与状态轮询）
- 首页项目列表与编辑/预览页增加「重跑」操作入口（按项目状态显示可用环节）
- 重跑任务以后台作业执行，状态通过现有 `meta.json` 与轮询 API 反馈
- 某环节正在执行时拒绝并发重跑同一环节（HTTP 409）

## Capabilities

### New Capabilities

- `pipeline-stage-rerun`: 对已有项目按环节（ASR、参考音库、TTS、remux）重新执行处理流程的 API 与 Web UI 能力，含确认提示、状态互斥与产物清理规则

### Modified Capabilities

- `web-ui-server`: 新增重跑各环节的 REST 端点、作业入队与状态约束；扩展项目列表/详情在重跑进行中的状态展示
- `subtitle-editor`: 编辑页提供重跑 ASR、参考音库、TTS 的控件；重跑进行中禁用冲突操作并显示进度

## Impact

- **后端**: `src/caption_helper/web/routes/projects.py`（新 rerun 端点）、`src/caption_helper/web/jobs.py`（拆分/复用 `_run_project`、参考音库、合成、remux 入队方法；ASR 重跑前清理逻辑）、`src/caption_helper/web/store.py`（可选：清理辅助方法）
- **前端**: `frontend/src/pages/HomePage.tsx`（项目行操作菜单）、`frontend/src/pages/EditorPage.tsx`、`frontend/src/pages/PreviewPage.tsx`、`frontend/src/api.ts`
- **测试**: `tests/test_web.py`（端点行为、409 互斥、ASR 重跑后产物覆盖）
- **依赖**: 无新依赖；复用现有 pipeline、reference、synthesizer、remux 模块
