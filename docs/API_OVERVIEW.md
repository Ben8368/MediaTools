# API 概览

MediaTools 后端基于 FastAPI。启动后可访问交互式文档：

```text
http://127.0.0.1:7860/docs
```

本文只列当前主要 API 分组，具体请求体以 FastAPI 文档和 `services/api_models.py` 为准。

## 服务入口

- `app.py` 启动 uvicorn。
- `services/api_server.py` 创建 FastAPI 应用。
- `services/api_server_setup.py` 注册路由。

## 路由分组

| 分组 | 路径前缀 | 文件 |
|---|---|---|
| 系统状态 | `/api/system`, `/api/modules` | `services/api_system_routes.py` |
| 媒体任务 | `/api/fetcher`, `/api/encoder`, `/api/decryptor` | `services/api_media_routes.py` |
| 工作区 | `/api/workspace` | `services/api_workspace_routes.py` |
| 工作台 | `/api/workbench` | `services/api_workbench_routes.py` |
| 素材 | `/api/assets` | `services/api_assets_routes.py` |
| 文件操作 | `/api/files` | `services/api_files_routes.py` |
| filebrowser | `/api/filebrowser` | `services/api_filebrowser_routes.py` |
| 任务中心 | `/api/tasks` | `services/api_task_center.py` |
| 日志 | `/api/logs` | `services/api_log_routes.py` |
| 路径选择 | `/api/path-picker` | `services/api_path_picker_routes.py` |
| Photoshop | `/api/photoshop` | `services/api_photoshop_routes.py` |
| Adobe/AE | `/api/adobe` | `services/api_adobe_routes.py` |
| auditor | `/api/auditor` | `services/api_auditor_routes.py` |
| 微信朋友圈图 | `/api/wechat_moments` | `services/api_wechat_routes.py` |
| AI 助手 | 见 agent routes | `services/agent_direct_routes.py` |

## 任务型 API

长任务应接入任务中心。前端通常先发起任务，再通过 `/api/tasks` 查询状态。

常见任务：

- 下载
- 转码
- 解密
- 工作台导出
- Adobe/Photoshop 执行
- 审核

## 安全和路径

- 后端绑定到非本机地址时需要设置 `API_SECRET_KEY`。
- 跨域来源由 `CORS_ALLOWED_ORIGINS` 控制。
- 工作区和文件访问必须经过允许根目录和路径解析逻辑。

## 维护建议

- 新 API 优先加入对应 `api_*_routes.py`。
- 请求/响应模型集中在 `services/api_models.py` 或同域模块。
- 路由不要直接写复杂业务逻辑。
- 文件路径相关 API 必须覆盖安全测试。
