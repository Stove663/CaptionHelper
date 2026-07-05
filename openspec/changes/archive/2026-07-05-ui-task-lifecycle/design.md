## Context

CaptionHelper 将每个上传视频存为 `data-dir/projects/{uuid}/` 目录，内含 `meta.json`、`source.*` 及 ASR/TTS/remux 产物。`ProjectStore` 提供 CRUD 元数据与产物清理（`clear_downstream_artifacts`），但尚无整项目删除或过期策略。`JobRunner` 在后台线程池串行执行 pipeline/synthesis/remux 作业；删除进行中的项目需避免竞态。

当前相关代码：

- 存储：`src/caption_helper/web/store.py` — `ProjectStore`
- 路由：`src/caption_helper/web/routes/projects.py`
- 作业：`src/caption_helper/web/jobs.py` — `JobRunner`
- 应用：`src/caption_helper/web/app.py` — `create_app`（无 lifespan 钩子）
- 前端：`frontend/src/pages/HomePage.tsx` — 项目列表

## Goals / Non-Goals

**Goals:**

- 用户可从首页彻底删除任务，删除后目录与元数据均不存在
- 未手动删除的任务在 `created_at` 满 7 天后由后台自动清除
- 处理中项目禁止删除（手动与自动均跳过）
- 删除 API 与 UI 确认流程一致、可测试

**Non-Goals:**

- 用户可配置保留天数
- 软删除 / 回收站 / 可恢复
- 独立 cron 进程或系统级定时任务
- 删除时取消正在运行的线程（首版仅拒绝删除，自动清理亦跳过处理中项目）

## Decisions

### 1. 删除实现：`shutil.rmtree` 整目录

**选择：** 在 `ProjectStore` 新增 `delete_project(project_id: str) -> None`，对 `projects/{id}/` 执行 `shutil.rmtree`，目录不存在时抛 `FileNotFoundError`。

**理由：** 与「不保留任何信息」一致；比逐项 `unlink` 更简单可靠。

**备选：** 标记 `deleted_at` 软删除 — 拒绝，违反「不保留任何信息」。

### 2. 处理中状态判定

**选择：** 复用前端 `isProjectProcessing` 对应的后端逻辑，集中定义 `BUSY_STATUSES` 集合（含 `uploaded`, `extracting`, `transcribing`, `splitting`, `building_references`, `synthesizing`, `remuxing` 等进行中状态）。`DELETE` 与自动清理均检查此集合。

**理由：** 与现有 rerun 互斥（409）语义一致；避免删除后作业仍写盘。

### 3. 删除 API

**选择：** `DELETE /api/projects/{id}` → 204 No Content；404 项目不存在；409 处理中。

**理由：** REST 惯例；与现有项目 API 风格一致。

### 4. 后台清扫：FastAPI lifespan + asyncio 周期任务

**选择：** 在 `create_app` 注册 `@asynccontextmanager` lifespan：

- 启动后延迟数秒执行首次 `purge_expired_projects()`
- 后台 `asyncio.create_task` 每小时执行一次
- 关闭时 cancel 任务

`purge_expired_projects` 逻辑：

```python
RETENTION_DAYS = 7
CLEANUP_INTERVAL_SECONDS = 3600

def purge_expired_projects(store: ProjectStore) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted = []
    for meta in store.list_projects():
        if is_busy(meta.status):
            continue
        created = datetime.fromisoformat(meta.created_at)
        if created < cutoff:
            store.delete_project(meta.id)
            deleted.append(meta.id)
    return deleted
```

**理由：** 无需新依赖或外部调度；Web 服务即守护进程。

**备选：** APScheduler — 过度；单用户本地工具 hourly 扫描足够。

### 5. 保留期起算点

**选择：** 以 `meta.json` 的 `created_at`（项目创建/上传时写入）为准，满 7×24 小时删除。

**理由：** 字段已存在；用户未操作时自然过期，与「上传后 7 天」直觉一致。

### 6. 前端删除 UX

**选择：** 首页每行增加「删除」按钮；`window.confirm` 提示「将永久删除该任务及所有相关文件，无法恢复」；成功后 `refresh()`。处理中或 `rerunning` 时禁用删除。

**理由：** 与 ASR 重跑确认模式一致；改动面小。

### 7. 测试策略

**选择：**

- 单元/集成：`DELETE` 成功、404、409；删除后 `GET` 404
- 清扫：mock `created_at` 为 8 天前，调用 `purge_expired_projects`，断言目录消失
- 处理中过期项目：状态为 `transcribing` 时清扫跳过

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 删除后作业线程仍运行并写已删目录 | 409 阻止手动删除；自动清扫跳过 busy 状态 |
| 大项目 `rmtree` 耗时阻塞请求 | 删除在请求线程执行，本地场景可接受；未来可异步化 |
| 服务器停机超过 7 天，重启后一次性删除大量项目 | 启动时立即扫描；日志记录删除数量 |
| 用户在编辑页时项目被自动清理 | 编辑页 API 404 时提示并导航回首页（可选，首版依赖列表轮询） |
| 时区与 `created_at` 解析 | 统一 UTC ISO 格式，与现有 `create_project` 一致 |

## Migration Plan

1. 实现 `delete_project` 与 `DELETE` 端点
2. 添加 lifespan 清扫任务（常量 `RETENTION_DAYS=7`）
3. 前端删除按钮与 API helper
4. 补充测试
5. 无数据迁移；现有项目按 `created_at` 自然进入 7 天窗口
6. 回滚：移除端点与 lifespan，已删数据不可恢复

## Open Questions

- 编辑/预览页是否也需要删除入口 — 首版仅首页，减少范围
- 是否在 UI 展示「将于 X 日自动删除」— 首版不做，可后续加 `expires_at` 字段
