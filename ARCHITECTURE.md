# MediaTools 架构文档

本文档描述 MediaTools 项目的当前架构设计。

## 总览

MediaTools 是一个综合媒体处理平台，包含前端 WebUI、后端 CLI 工具和 AI Agent。

```text
入口层
├── app.py (Web 服务)
├── cli/main.py (CLI 工具)
└── backend/api/server.py (API 服务器)

后端层
├── backend/config/ - 配置管理
├── backend/agent/ - AI Agent 层
├── backend/api/ - API 层
│   ├── server.py - FastAPI 应用
│   ├── routes/ - API 路由（16个）
│   ├── runtime.py - 运行时管理
│   └── models.py - 数据模型
├── backend/services/ - 业务服务层
│   ├── media/ - 媒体处理服务
│   ├── runtime/ - 运行时管理
│   └── ... - 其他服务
└── modules/ - 功能模块层

基础设施层
├── core/ - 核心工具（FFmpeg、日志、认证）
├── adapters/ - 外部工具适配器
├── patches/ - 工具补丁系统
└── vendor/ - 第三方代码

前端层
└── frontend/ - React + TypeScript + Vite
```

## 设计原则

1. **清晰的分层架构**
   - 入口层：CLI/API/Agent
   - 业务层：Services
   - 功能层：Modules
   - 基础层：Core/Adapters

2. **Agent 独立成层**
   - `backend/agent/` 独立管理 AI 能力
   - 包含 service、tools、routes 等完整功能

3. **API 路由集中**
   - 所有 API 路由集中在 `backend/api/routes/`
   - 易于查找和管理

4. **模块可独立调用**
   - 每个 `modules/` 下的模块都有独立的 CLI
   - 可被 CLI、API、Agent 任意调用

5. **前端完全独立**
   - 独立的构建流程
   - 通过 HTTP API 与后端通信

## 目录结构

### backend/ - 后端代码

```
backend/
├── config/              # 配置管理
│   ├── __init__.py
│   └── settings.py      # 全局配置
│
├── agent/               # AI Agent 层
│   ├── service.py       # Agent 服务
│   ├── tools.py         # Agent 工具实现
│   ├── tool_specs.py    # 工具规范定义
│   ├── helpers.py       # 辅助函数
│   └── routes.py        # Agent 路由
│
├── api/                 # API 层
│   ├── server.py        # FastAPI 应用
│   ├── setup.py         # 路由配置
│   ├── runtime.py       # 运行时管理
│   ├── models.py        # Pydantic 模型
│       └── routes/          # API 路由（16个）
│       ├── media.py     # 媒体处理
│       ├── workspace.py # 工作区管理
│       ├── workbench.py # 工作台
│       ├── assets.py    # 素材管理
│       ├── files.py     # 文件操作
│       ├── photoshop.py # Photoshop 自动化
│       ├── adobe.py     # Adobe 通用
│       ├── auditor.py   # 审核
│       ├── wechat.py    # 微信朋友圈
│       ├── system.py    # 系统信息
│       ├── filebrowser.py # 文件浏览器
│       ├── browser.py   # 浏览器管理
│       ├── path_picker.py # 路径选择
│       ├── task_center.py # 任务中心
│       └── log.py       # 日志查看
│
└── services/            # 业务服务层
    ├── media/           # 媒体服务
    │   ├── core.py      # 兼容门面
    │   ├── fetch.py     # 视频获取
    │   ├── encoding.py  # 转码切片
    │   ├── decrypt.py   # 解密
    │   ├── workflows.py # 组合工作流
    │   └── helpers.py   # 辅助函数
    ├── runtime/         # 运行时管理
    │   ├── editor.py    # 编辑器运行时
    │   └── filebrowser.py # 文件浏览器运行时
    ├── workspace.py     # 工作区管理
    ├── workbench.py     # 工作台服务
    ├── task_center.py   # 任务中心
    ├── photoshop.py     # Photoshop 服务
    ├── auditor.py       # 审核服务
    └── ... # 其他服务
```

### cli/ - CLI 入口

```
cli/
├── __init__.py
└── main.py              # CLI 主入口
```

### modules/ - 功能模块

```
modules/
├── fetcher/             # 视频下载、字幕处理
├── encoder/             # 转码、切片
├── decryptor/           # 解密
├── assets/              # 素材管理
├── workbench/           # 工作台
├── editor/              # CapCut 集成
├── photoshop/           # Photoshop 自动化
├── adobe/               # Adobe 通用
├── auditor/             # 审核
├── generator/           # 素材生成
└── filebrowser/         # 文件浏览器
```

### frontend/ - 前端

```
frontend/
├── src/
│   ├── main.tsx         # 入口
│   ├── App.tsx          # 主应用
│   ├── apps/            # 应用模块
│   ├── components/      # 通用组件
│   ├── stores/          # 状态管理（Zustand）
│   ├── services/        # API 调用
│   └── i18n/            # 国际化
└── dist/                # 构建输出
```

## 主要数据流

### 1. 下载到切片流程

```text
Frontend / AI Assistant / CLI
→ backend/api/routes/media.py
→ backend/services/media/workflows.py
→ backend/services/media/fetch.py
→ modules/fetcher
→ backend/services/media/encoding.py
→ modules/encoder
→ projects/<workspace>/clips
```

### 2. 工作台复核流程

```text
Frontend Workbench
→ backend/api/routes/workbench.py
→ backend/services/workbench.py
→ modules/fetcher/analyzer.py
→ modules/encoder/transcoder.py
→ projects/<workspace>/clips
```

### 3. AI 助手执行任务

```text
Frontend AI Assistant
→ backend/agent/routes.py
→ backend/agent/service.py
→ backend/agent/tools.py
→ backend/services/* (media/workspace/assets)
```

## 启动方式

### Web 服务

```bash
# 生产模式
python app.py

# 开发模式（自动重载）
python app.py --reload

# 指定端口
python app.py --port 8080
```

### CLI 工具

```bash
# 新方式（推荐）
python -m cli.main fetcher download <url>

# 旧方式（兼容）
python main.py fetcher download <url>
```

### 前端开发

```bash
cd frontend
npm run dev          # 启动开发服务器
npm run build        # 构建生产版本
```

## 配置管理

配置文件位于 `backend/config/settings.py`，支持通过 `.env` 文件覆盖：

```bash
# .env 示例
TEC_CHI_API_KEY=your_api_key
GUI_SERVER_PORT=7860
WORKSPACE_ALLOWED_ROOTS=/path/to/projects
```

## 向后兼容

为了保持向后兼容，保留了以下兼容层：

- `config.py` → `backend.config`
- `main.py` → `cli.main`

这些文件会显示 DeprecationWarning，建议逐步迁移到新的导入路径。

## 开发建议

1. **新的跨模块业务流程**：放到 `backend/services/`
2. **底层可复用能力**：放到 `modules/`，保持 CLI 可测
3. **外部软件差异**：放到 `adapters/` 或 `backend/services/runtime/`
4. **Web 路由**：只做请求解析、校验和响应组织
5. **长任务**：接入 `task_center`，让前端能展示状态和日志
6. **工作区路径**：同步检查安全校验和测试

## 测试

```bash
# 运行测试套件
pytest tests/ -v

# 运行覆盖率测试
pytest tests/ --cov=. --cov-report=html

# 类型检查
mypy backend/ --ignore-missing-imports
```

## 当前边界

- Web 服务是能力最完整的入口，CLI 是辅助和批处理入口
- 素材管理是工作区索引器，不是完整资产数据库
- CapCut-Mate、Adobe 自动化和审核工具依赖本机环境
- `vendor/` 中的第三方代码不应被当作项目自有业务层维护
