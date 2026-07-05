## Context

CaptionHelper Web UI 在上传视频后自动入队 ASR 作业（`JobRunner._run_project`）：提取音频 → FunASR 转写 → 切分片段 → 初始化字幕 → 构建说话人参考音库，最终状态 `ready`。用户可在编辑页修改字幕后触发 TTS（`POST /synthesize`）与 remux（`POST /remux`）。

当前缺口：

- **ASR 重跑**：无 API；失败或识别差时只能重新上传
- **参考音库重跑**：CLI 有 `caption-helper build-refs`，Web 无入口
- **TTS / remux 重跑**：端点存在但 UI 分散，首页无统一入口；用户不易发现可「不重新上传」再次执行

`JobRunner` 已对 pipeline、synthesis、remux 使用独立 `asyncio.Lock`，天然支持「同类作业串行、异类可排队」的扩展。

## Goals / Non-Goals

**Goals:**

- 四个可重跑环节：**ASR**、**参考音库**（克隆准备）、**TTS**、**remux**
- 各环节独立 REST 端点，返回 `202 Accepted` 并入队后台作业
- 明确各环节重跑时的产物清理范围
- 首页与编辑/预览页提供按状态启用的重跑按钮；破坏性操作（ASR）需浏览器确认
- 与现有状态机（`extracting`…`ready`…`synthesis_ready`…`remux_ready`）兼容，复用轮询

**Non-Goals:**

- 选择性重跑 ASR 子步骤（仅转写、仅切分）
- 重跑时保留用户已编辑字幕（ASR 重跑一律全量覆盖）
- 批量重跑多个项目
- 删除项目（另开变更）
- 修改 ASR/TTS 模型参数的专用重跑 UI（沿用服务端启动参数）

## Decisions

### 1. 环节划分与端点命名

**选择：** 新增四个 `POST` 端点，统一前缀 `/api/projects/{id}/rerun/`：

| 环节 | 端点 | 作业方法 |
|------|------|----------|
| ASR 全流程 | `POST .../rerun/asr` | `_run_project`（重跑前清理） |
| 参考音库 | `POST .../rerun/references` | 新增 `_run_references` |
| TTS | `POST .../rerun/synthesis` | 复用 `_run_synthesis` |
| remux | `POST .../rerun/remux` | 复用 `_run_remux` |

**理由：** `rerun/` 命名空间与首次上传触发的隐式流程区分清晰；TTS/remux 与现有 `POST /synthesize`、`POST /remux` 行为一致，实现时可内部共用 helper，spec 要求 UI 统一走 rerun 语义（现有端点可保留兼容）。

**备选：** 单一 `POST .../rerun` + `stage` 字段 — 拒绝，四端点更利于 OpenAPI 与测试。

### 2. ASR 重跑产物清理

**选择：** 入队前删除（若存在）：

- `audio.wav`、`subtitles.json`、`subtitles.srt`、`subtitles_edited.srt`
- `segments/` 内所有 wav
- `speaker_refs/`、`modified_segments.json`
- `tts_segments/`、`synthesis_manifest.json`
- `output_audio.wav`、`output_video.mp4`、remux/ripple 相关 manifest

保留 `source.*` 与 `meta.json`（重置 `status`，清空 `error`）。

**理由：** ASR 结果变化会导致字幕与下游全部失效；部分保留易致不一致。

### 3. 参考音库重跑范围

**选择：** 仅调用 `build_speaker_reference_bank(project_dir)`，覆盖 `speaker_refs/`；不改动字幕、`segments/`、TTS/remux 产物。状态短暂设为 `building_references`，完成后恢复为 `ready`（若此前为 `synthesis_*` / `remux_*` 则仍回到 `ready`，提示用户需重新合成）。

**理由：** 与 CLI `build-refs` 一致；用户常在调整参考策略后仅需重建音库。

**备选：** 参考音库重跑后自动触发 TTS — 拒绝，副作用过大。

### 4. 并发与互斥

**选择：**

- 与现有逻辑相同：同环节进行中返回 **409**
- ASR 重跑进行中：拒绝 synthesis、remux、references 重跑
- synthesis 进行中：拒绝 remux、ASR、references
- remux 进行中：拒绝 ASR、synthesis
- references 重跑：可与 ASR 互斥；synthesis/remux 进行中拒绝

**理由：** 复用现有 lock 模式，避免文件竞争。

### 5. 前置条件

| 环节 | 要求 |
|------|------|
| ASR | `source.*` 存在；状态非 `extracting`/`transcribing`/`splitting` |
| references | `segments/` 非空且 `subtitles.json` 存在 |
| synthesis | `modified_segments.json` 非空（与现逻辑一致）；可选 body `skip_unavailable` |
| remux | 与现 `POST /remux` 相同校验（clips 齐全） |

### 6. 前端入口布局

**选择：**

- **HomePage**：操作列增加「更多 ▾」下拉或链接组：`重跑 ASR`、`重建参考音库`（`ready` 及以后）、`重新合成`（有修改片段时）、`重新 remux`（`synthesis_ready` 后）
- **EditorPage**：工具栏增加「重跑」按钮组；ASR 重跑 `window.confirm` 提示将丢失编辑
- **PreviewPage**：保留「生成输出」，增加「重新 remux」别名调用同一 API

**理由：** 首页便于失败后快速重试；编辑页上下文最完整。

### 7. Store 清理辅助

**选择：** 在 `ProjectStore` 新增 `clear_downstream_artifacts(project_id, *, through: Literal["asr", "tts", "remux"])` 集中处理删除，供 jobs 与路由调用。

**理由：** 避免路由层散落 `shutil.rmtree`；便于单测。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| ASR 重跑误删用户编辑 | 确认对话框 + 文案说明 |
| 参考音库重跑后旧 TTS 片段与新区不匹配 | 重跑后状态回 `ready`，UI 提示需重新合成 |
| 长作业重复点击 | 409 + 按钮 disabled + 轮询状态 |
| 磁盘清理不完整残留 | `clear_downstream_artifacts` 单测列举预期路径 |
| 与 `failed` 状态项目 | 允许重跑 ASR 从 `failed` 恢复 |

## Migration Plan

1. 实现 `ProjectStore.clear_downstream_artifacts` 与 `JobRunner._run_references`
2. 添加四个 rerun 路由与测试
3. 前端 API helper + 各页按钮
4. 无数据迁移；已存在项目目录结构不变
5. 回滚：移除端点与 UI，不影响已生成文件

## Open Questions

- TTS 重跑是否支持「强制全量合成所有 cue」而不仅是 `modified_segments` — 首版保持现有「仅修改片段」语义，与编辑页一致
- 是否在 rerun 响应中返回 `job_id` — 首版沿用 project `status` 轮询，不引入新 job 表
