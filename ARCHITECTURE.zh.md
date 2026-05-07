# MediaTools 架构说明

> [English](./ARCHITECTURE.md)

## 概览

```
入口层
├── app.py              # Web 服务（FastAPI + Uvicorn）
├── cli/main.py         # CLI 调度器
└── backend/agent/      # AI 助手

后端层
├── backend/api/routes/ # API 路由（仅处理请求/响应）
├── backend/services/   # 业务逻辑和工作流
├── backend/config/     # 配置管理
└── modules/            # CLI 可调用的能力模块

基础设施
├── adapters/           # 外部工具适配器
├── core/               # 通用工具（认证、日志、ffmpeg）
└── patches/            # 工具补丁规则

前端
└── frontend/           # React + TypeScript + Vite
```

## 设计原则

1. **路由仅处理请求** - 不包含复杂业务逻辑
2. **服务编排工作流** - 跨模块逻辑在 `backend/services/`
3. **模块可独立调用** - CLI、API 和 Agent 复用相同模块
4. **适配器隔离外部工具** - 平台差异封装在 `adapters/`
5. **前端仅通过 HTTP API 通信**

## 后端结构

```
backend/
├── api/
│   ├── server.py       # FastAPI 应用
│   ├── setup.py        # 路由注册
│   ├── models.py       # Pydantic 模型
│   └── routes/         # 按领域划分的路由文件
├── services/
│   ├── media/          # 媒体工作流（获取、编码、解密）
│   ├── runtime/        # 外部工具运行时
│   ├── workspace.py    # 工作区管理
│   ├── workbench.py    # 工作台服务
│   └── task_center.py  # 长任务
├── agent/
│   ├── service.py      # Agent 服务
│   ├── tools.py        # Agent 工具
│   ├── tool_specs.py   # 工具定义
│   └── routes.py       # Agent API 路由
└── config/
    └── settings.py     # 全局配置
```

## 前端结构

```
frontend/src/
├── apps/               # 桌面式应用窗口
│   ├── DownloaderApp.tsx
│   ├── WorkbenchApp.tsx
│   ├── FileManagerApp.tsx
│   ├── BrowserApp.tsx
│   ├── AIAssistantApp.tsx
│   ├── PhotoshopApp.tsx
│   ├── AEApp.tsx
│   └── AuditorApp.tsx
├── api.ts              # API 调用
├── store.ts            # 全局状态（Zustand）
└── windowStore.ts      # 窗口状态
```

## 主要数据流

### 下载 → 分析 → 切片

```
前端 / CLI / Agent
→ backend/api/routes/media.py
→ backend/services/media/workflows.py
→ modules/fetcher → modules/encoder
→ projects/<workspace>/clips
```

### AI 助手

```
前端 AI 助手
→ backend/agent/routes.py
→ backend/agent/service.py
→ backend/services/* → modules/*
```

## 配置

在 `backend/config/settings.py`，通过 `.env` 覆盖：

```
TEC_CHI_API_KEY=your_api_key
GUI_SERVER_PORT=7860
WORKSPACE_ALLOWED_ROOTS=/path/to/projects
```

## 兼容性

- `config.py` → 代理 `backend.config`
- `main.py` → 代理 `cli.main`
- 这些会显示 DeprecationWarning；新代码应使用新路径

## 开发规范

1. 新业务逻辑 → `backend/services/`
2. 可复用能力 → `modules/`（CLI 可测试）
3. 外部工具差异 → `adapters/` 或 `backend/services/runtime/`
4. 长任务 → 接入 `task_center`
5. 文件路径 → 始终验证允许根目录

## 测试

```powershell
python -m pytest
cd frontend && npm run typecheck && npm test
```

## 边界说明

- Web 服务是最完整入口；CLI 用于批量/辅助任务
- 素材管理是工作区索引，非完整数据库
- CapCut、Adobe 和审核依赖本机环境
- `vendor/` 是第三方代码，非项目业务层
