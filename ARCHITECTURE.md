# MediaTools 当前架构

本文只描述当前代码库中的真实结构。历史方案、第三方工具原始文档和实验设计从 `docs/README.md` 进入。

## 总览

```text
用户入口
├── Web: app.py -> services/api_server.py -> frontend/dist
└── CLI: main.py -> modules/*/cli.py

后端服务层
├── services/api_*_routes.py
├── services/media_*.py
├── services/task_center.py
├── services/agent*.py
├── services/workspace.py
└── services/*_runtime.py

能力模块层
├── modules/fetcher
├── modules/encoder
├── modules/decryptor
├── modules/assets
├── modules/workbench
├── modules/adobe
├── modules/photoshop
├── modules/auditor
├── modules/generator
└── modules/editor

基础和外部依赖
├── core
├── adapters
├── patches
├── vendor
├── bin
├── runtime
└── projects
```

设计原则：

- `services/` 是 Web API 和跨模块业务流程的主层。
- `modules/` 保持可 CLI 调用的底层能力。
- `adapters/` 隔离外部软件、第三方工具和本机运行时差异。
- `vendor/` 放第三方源码或嵌入工具，不作为自有业务代码入口。
- `runtime/` 和 `projects/` 保存运行状态与工作产物，通常不提交。

## 入口层

### Web 服务

入口文件：`app.py`

职责：

- 读取 `GUI_SERVER_NAME`、`GUI_SERVER_PORT`、`API_SECRET_KEY`
- 配置 Windows 事件循环兼容处理
- 通过 uvicorn 启动 `services/api_server.py`
- 默认服务地址为 `http://127.0.0.1:7860`

非本机绑定时，如果未设置 `API_SECRET_KEY`，启动会拒绝继续，避免无认证暴露 API。

### API 应用

核心文件：`services/api_server.py`

职责：

- 创建 FastAPI 应用
- 挂载 API 路由
- 服务前端静态资源
- 管理运行时、任务中心、日志和错误响应

路由主要拆分在：

- `services/api_media_routes.py`
- `services/api_assets_routes.py`
- `services/api_files_routes.py`
- `services/api_filebrowser_routes.py`
- `services/api_workbench_routes.py`
- `services/api_workspace_routes.py`
- `services/api_task_center.py`
- `services/api_photoshop_routes.py`
- `services/api_adobe_routes.py`
- `services/api_auditor_routes.py`
- `services/api_system_routes.py`
- `services/agent_direct_routes.py`

### 前端

目录：`frontend/`

技术栈：

- React 18
- TypeScript
- Vite
- Zustand
- i18next

当前界面是桌面式 Web 工作台，主要应用包括下载器、工作台、文件管理、AI 助手、Photoshop、AE、审核、设置等。

生产构建输出在 `frontend/dist/`，由后端服务。开发时运行：

```powershell
cd frontend
npm run dev
```

### CLI

入口文件：`main.py`

规范模块：

- `fetcher`
- `encoder`
- `decryptor`
- `assets`
- `workbench`
- `editor`
- `photoshop`
- `auditor`
- `generator`

兼容旧别名：

- `fetch` -> `fetcher`
- `encode` -> `encoder`
- `decrypt` -> `decryptor`
- `edit` -> `editor`

CLI 负责把命令分发到 `modules/*/cli.py`，适合批处理和调试。

## 服务层

`services/` 是当前后端的主要维护边界。

### 媒体流程

核心文件：

- `services/media.py`
- `services/media_fetch.py`
- `services/media_encoding.py`
- `services/media_decrypt.py`
- `services/media_workflows.py`
- `services/media_helpers.py`

职责：

- 视频信息探测
- 下载和字幕获取
- 转码、切片、音频提取
- 下载 -> 字幕分析 -> 自动切片的组合流程
- 解密任务封装
- 输出摘要和日志组织

### 工作区和工作台

核心文件：

- `services/workspace.py`
- `services/workbench.py`
- `services/path_picker.py`

职责：

- 当前工作区读取和设置
- 工作区目录展示
- 视频/字幕/导出结果枚举
- 字幕分析和片段建议
- clips 批量导出
- 路径选择和安全校验

### 任务中心和系统状态

核心文件：

- `services/task_center.py`
- `services/api_task_center.py`
- `services/system_monitor.py`
- `services/log_buffer.py`

职责：

- 长任务状态跟踪
- 任务日志输出
- 系统状态和工具状态检查
- 前端轮询数据模型

### AI 助手

核心文件：

- `services/agent.py`
- `services/agent_tools.py`
- `services/agent_tool_specs.py`
- `services/agent_helpers.py`
- `services/agent_direct_routes.py`

职责：

- OpenAI 兼容接口封装
- 工具定义和工具调用
- 常见媒体任务的本地直连路由
- 下载、分析、切片、解密、扫描等执行型任务编排

### 外部运行时

核心文件：

- `services/editor_runtime.py`
- `services/filebrowser_runtime.py`
- `services/photoshop.py`
- `services/photoshop_state.py`
- `services/auditor.py`
- `services/wechat_moments.py`

职责：

- 管理 capcut-mate/filebrowser 等外部进程
- 封装 Photoshop/审核/生成类能力
- 维护运行状态、PID、日志和健康检查

## 模块层

`modules/` 中的模块应尽量保持可独立 CLI 调用。

| 模块 | 职责 |
|---|---|
| `modules/fetcher` | yt-dlp 管理、视频下载、字幕处理、字幕分析 |
| `modules/encoder` | FFmpeg 转码、音频提取、单段切片 |
| `modules/decryptor` | 解密工具封装 |
| `modules/assets` | 素材扫描、搜索、预览、文件管理 |
| `modules/workbench` | 字幕分析和 clips 导出 CLI |
| `modules/editor` | capcut-mate HTTP 适配 |
| `modules/adobe` | Adobe 通用、Photoshop、After Effects 自动化 |
| `modules/photoshop` | Photoshop CLI 入口 |
| `modules/auditor` | 素材审核 CLI 入口 |
| `modules/generator` | 截图、朋友圈图片等素材生成 |
| `modules/filebrowser` | filebrowser 服务封装 |

## 外部工具和目录

### `adapters/`

封装外部工具和本机软件运行时，例如：

- Adobe Runtime
- Photoshop Runtime
- After Effects Runtime
- Auditor Runtime
- WeChat Moments Runtime
- external tools

### `core/`

通用基础能力：

- FFmpeg 路径和执行封装
- 日志
- 鉴权
- 输入校验

### `patches/`

维护外部工具补丁规则和加载逻辑。补丁配置加载顺序通常是：

1. `patches/tool_patches.json`
2. `runtime/tool_patches.json`
3. 当前工作区的 `manifests/tool_patches.json`

后加载规则可覆盖先加载规则。

### `vendor/`

第三方项目和嵌入工具，例如 yt-dlp、filebrowser、capcut-mate、Adobe 相关桥接代码等。这里的 README 和 LICENSE 主要属于上游项目。

### `bin/`

本地二进制工具目录，例如：

- `ffmpeg`
- `ffprobe`
- `yt-dlp`
- `um-cli`

### `runtime/`

运行时状态目录，例如：

- 当前工作区配置
- PID 文件
- 运行日志
- 临时数据库或 CSV

### `projects/`

工作区和用户产物目录。

## 主要数据流

### 下载到切片

```text
Frontend / AI Assistant / CLI
-> services/api_media_routes.py
-> services/media_workflows.py
-> services/media_fetch.py
-> modules/fetcher
-> services/media_encoding.py
-> modules/encoder
-> projects/<workspace>/clips or exports
```

### 工作台复核

```text
Frontend Workbench
-> services/api_workbench_routes.py
-> services/workbench.py
-> modules/fetcher/analyzer.py
-> modules/encoder/transcoder.py
-> projects/<workspace>/clips
```

### AI 助手执行任务

```text
Frontend AI Assistant
-> services/agent_direct_routes.py
-> services/agent.py
-> services/agent_tools.py
-> services/media_* / workspace / assets
```

## 开发建议

- 新的跨模块业务流程优先放到 `services/`。
- 底层可复用能力放到 `modules/`，并保持 CLI 可测。
- 外部软件差异放到 `adapters/` 或 `services/*_runtime.py`。
- Web 路由只做请求解析、校验和响应组织，避免塞入复杂业务逻辑。
- 新增长任务时接入 `task_center`，让前端能展示状态和日志。
- 修改工作区路径相关逻辑时同步检查安全校验和测试。

## 当前边界

- Web 服务是能力最完整的入口，CLI 是辅助和批处理入口。
- 素材管理是工作区索引器，不是完整资产数据库。
- capcut-mate、Adobe 自动化和审核工具依赖本机环境。
- `vendor/` 中的第三方代码不应被当作项目自有业务层维护。
