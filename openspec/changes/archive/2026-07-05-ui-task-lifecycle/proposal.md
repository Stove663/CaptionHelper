## Why

用户上传视频后会在数据目录中积累项目目录（含源视频、字幕、TTS 产物等），目前无法从 Web UI 主动删除任务，也没有自动清理策略，长期运行会占用大量磁盘空间。需要让用户随时彻底删除不需要的任务，同时对未操作的任务默认保留 7 天后由后台自动清除。

## What Changes

- 新增 `DELETE /api/projects/{id}` 端点：用户确认后删除整个项目目录及全部关联数据，不保留任何信息
- 项目列表 API 不再返回已删除项目；删除后相关 API 返回 404
- 后台定时任务：扫描超过 7 天（自 `created_at` 起）的项目并自动删除，与手动删除使用相同清理逻辑
- 首页项目列表增加「删除」操作，删除前弹出确认对话框；处理中的项目禁止删除（HTTP 409）
- 7 天保留期为默认行为，首版不提供用户可配置项
- 自动清理在 Web 服务启动后以固定间隔运行，无需额外进程

## Capabilities

### New Capabilities

- `project-lifecycle`: 项目（任务）的手动删除与 7 天自动过期清理，含 API、存储层删除、后台清扫与 Web UI 入口

### Modified Capabilities

- `web-ui-server`: 新增删除端点、处理中互斥约束、后台过期清扫任务；项目列表与详情在删除后不可访问

## Impact

- **后端**: `src/caption_helper/web/store.py`（`delete_project`）、`src/caption_helper/web/routes/projects.py`（`DELETE` 端点）、`src/caption_helper/web/jobs.py`（删除时取消/等待进行中作业）、`src/caption_helper/web/app.py` 或新建 `cleanup.py`（后台清扫循环）
- **前端**: `frontend/src/pages/HomePage.tsx`（删除按钮与确认）、`frontend/src/api.ts`（`deleteProject`）
- **测试**: `tests/test_web.py`（删除成功、404、处理中 409、过期清扫）
- **依赖**: 无新依赖；复用现有 `ProjectStore` 与 FastAPI 应用生命周期
