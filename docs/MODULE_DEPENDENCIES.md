# 模块依赖

本文描述当前推荐的依赖方向，用于维护时判断代码应放在哪里。

## 分层

```text
frontend
  -> services/api_*_routes.py
  -> services/*
  -> modules/*
  -> adapters/core/vendor/bin
```

CLI 路径：

```text
main.py
  -> modules/*/cli.py
  -> modules/* or services/*
```

依赖原则：

- 前端只调用 API，不直接理解 Python 模块结构。
- API 路由负责请求/响应，不承载复杂业务。
- 跨模块流程放在 `services/`。
- 单一能力放在 `modules/`。
- 外部工具细节放在 `adapters/`、`core/` 或 `services/*_runtime.py`。

## 主要模块关系

| 能力 | 主要服务 | 底层模块/工具 |
|---|---|---|
| 下载和字幕 | `services/media_fetch.py` | `modules/fetcher`, `yt-dlp` |
| 转码和切片 | `services/media_encoding.py` | `modules/encoder`, `FFmpeg` |
| 下载分析切片 | `services/media_workflows.py` | `fetcher`, `encoder`, AI API |
| 解密 | `services/media_decrypt.py` | `modules/decryptor`, `um-cli` |
| 工作区 | `services/workspace.py` | filesystem |
| 工作台 | `services/workbench.py` | `fetcher`, `encoder`, AI API |
| 素材扫描 | API routes / assets services | `modules/assets` |
| AI 助手 | `services/agent*.py` | media/workspace/assets services |
| Photoshop | `services/photoshop.py` | `modules/adobe`, Adobe runtime |
| After Effects | `services/api_adobe_routes.py` | `modules/adobe`, Adobe runtime |
| 审核 | `services/auditor.py` | `modules/auditor`, `vendor/auditor` |
| filebrowser | `services/filebrowser_runtime.py` | `modules/filebrowser`, `vendor/filebrowser` |

## 推荐放置位置

### 新增 API

1. 在 `services/api_*_routes.py` 中增加路由。
2. 请求和响应模型放在 `services/api_models.py` 或相近模块。
3. 复杂逻辑下沉到服务函数。
4. 长任务接入 `services/task_center.py`。

### 新增媒体流程

1. 单步能力放在 `modules/`。
2. 多步骤编排放在 `services/media_workflows.py` 或相近服务文件。
3. 输出路径必须走工作区和路径校验工具。
4. Web 和 AI 助手复用同一个服务函数。

### 新增外部工具

1. 工具发现、版本检查、命令执行放在 adapter/runtime service。
2. CLI 封装放在 `modules/<tool>/cli.py`。
3. Web 路由只暴露状态、启动、停止、任务结果等产品语义。
4. 相关说明写入 `docs/EXTERNAL_TOOLS.md`。

## 避免的依赖

- `frontend/` 不应依赖 Python 文件路径。
- `services/api_*_routes.py` 不应直接拼复杂 shell 命令。
- `modules/` 不应依赖前端概念。
- `vendor/` 中上游代码不应反向依赖项目服务。
- 外部工具路径不应散落在多个业务文件里。

## 测试边界

- 模块级逻辑：写 `tests/test_<module>.py`。
- API 路由：写 `tests/test_api_*routes.py`。
- 长任务和工作区：覆盖状态、路径、安全校验和失败分支。
- 外部工具：优先 mock adapter/runtime，避免测试强依赖本机软件。
