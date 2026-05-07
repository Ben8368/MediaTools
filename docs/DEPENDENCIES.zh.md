# Dependencies and Naming Conventions

> [English](./DEPENDENCIES.md)

代码放置和命名规范。

## 依赖方向

```
frontend
  → 仅通过 HTTP API 调用
  → 不依赖 Python 文件结构

cli/main.py
  → modules/*/cli.py
  → modules/* 或 backend/services/
```

## 放置规则

| 代码类型 | 位置 |
|---|---|
| 新 API 路由 | `backend/api/routes/<domain>.py` |
| 业务工作流 | `backend/services/` |
| 可复用能力 | `modules/`（CLI 可测试） |
| 外部工具差异 | `adapters/`、`core/` 或 `backend/services/runtime/` |
| 请求/响应模型 | `backend/api/models.py` |
| 长任务 | 接入 `backend/services/task_center.py` |

## 模块参考

| 能力 | 服务 | 底层模块 |
|---|---|---|
| 下载/字幕 | `backend/services/fetcher.py` | `modules/fetcher`, `yt-dlp` |
| 转码/切片 | `backend/services/encoder.py` | `modules/encoder`, `FFmpeg` |
| 工作流（下载→切片） | `backend/services/media/workflows.py` | `fetcher`, `encoder`, AI |
| 解密 | `backend/services/decryptor.py` | `modules/decryptor`, `um-cli` |
| 工作区 | `backend/services/workspace.py` | filesystem |
| AI 助手 | `backend/agent/` | media/workspace 服务 |

## 避免

- 前端依赖 Python 文件路径
- 路由拼接复杂 shell 命令
- 模块依赖前端概念
- `vendor/` 代码反向依赖项目服务
- 外部工具路径散落在业务文件中

## 命名

| 上下文 | 规范 |
|---|---|
| Python 文件 | `snake_case.py` |
| Python 函数 | `snake_case` |
| Python 类 | `PascalCase` |
| 常量 | `UPPER_SNAKE_CASE` |
| React 组件 | `PascalCase.tsx` |
| React hooks | `useSomething.ts` |
| 应用窗口 | `<Name>App.tsx` |
| 工作区目录 | 小写复数（`downloads/`、`clips/`） |
| CLI 模块 | `fetcher`、`encoder`、`decryptor`、`assets`、`workbench`、`editor`、`photoshop`、`auditor`、`generator` |

## 测试

| 范围 | 位置 |
|---|---|
| 模块逻辑 | `tests/test_<module>.py` |
| API 路由 | `tests/test_api_*routes.py` |
| 外部工具 | Mock adapters/runtime |
