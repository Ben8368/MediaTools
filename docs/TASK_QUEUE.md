# 任务中心和长任务

本文取代早期 Celery/RQ 方案草稿，描述当前代码库中的实际任务机制。

## 当前状态

MediaTools 当前使用内置任务中心，而不是 Celery、RQ 或外部 Redis 队列。

核心文件：

- `services/task_center.py`
- `services/api_task_center.py`
- `services/api_server_runtime.py`
- `services/task_resumers/`
- `frontend/src/apps/mediatools/automation.ts`
- `frontend/src/apps/mediatools/AutomationTaskDialog.tsx`

API 前缀：

```text
/api/tasks
```

## 职责

任务中心负责：

- 为长任务分配任务 ID
- 记录任务状态、进度和日志
- 支持前端轮询任务列表和单个任务详情
- 支持取消、删除、清理历史
- 为部分任务提供恢复/续跑入口

适合纳入任务中心的能力：

- 视频下载
- 转码和切片
- AI 分析和自动导出
- 解密
- Adobe/Photoshop 执行
- 审核和批处理

## API 概览

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/tasks/list` | 任务列表 |
| `GET` | `/api/tasks/active` | 活跃任务 |
| `GET` | `/api/tasks/history/week` | 最近一周历史 |
| `GET` | `/api/tasks/{task_id}` | 单个任务详情 |
| `POST` | `/api/tasks/{task_id}/cancel` | 取消任务 |
| `DELETE` | `/api/tasks/{task_id}` | 删除任务记录 |
| `POST` | `/api/tasks/clear` | 清理任务 |
| `DELETE` | `/api/tasks/history/cleanup` | 清理历史 |

## 和早期 Celery 方案的关系

早期文档建议过 `Celery + Redis`，但当前项目已经选择内置任务中心作为本地桌面式工作台的默认方案。

保留外部队列的适用场景：

- 多机器 worker
- 需要持久化分布式队列
- 需要严格优先级和重试策略
- 需要把媒体处理从 Web 服务进程彻底拆出

在这些需求出现前，不建议引入 Celery/RQ，避免提高本地部署成本。

## 新增长任务的建议

1. 服务函数放在 `services/`，不要把长逻辑写在 API 路由里。
2. 任务启动时登记到 `task_center`。
3. 执行过程中写入阶段、进度和日志。
4. 失败时返回可读错误和可排查的日志。
5. 前端通过 `/api/tasks` 轮询状态。
6. 如果任务可恢复，把恢复逻辑放到 `services/task_resumers/`。

## 设计边界

- 当前任务中心主要服务单机本地工作台。
- 任务状态不等同于完整的分布式作业系统。
- 重启后的恢复能力取决于具体任务是否实现 resumer。
- 涉及外部进程的任务仍要在对应 runtime service 中处理 PID、日志和异常。
