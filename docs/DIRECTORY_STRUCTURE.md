# 目录结构

本文说明 MediaTools 当前目录职责。第三方项目自己的目录结构以 `vendor/` 内上游文档为准。

## 根目录

```text
MediaTools/
├── app.py                    # Web 服务入口（启动 backend/api/server.py）
├── main.py                   # CLI 统一入口（代理到 cli/main.py）
├── config.py                 # 配置读取（代理到 backend/config）
├── cli/                      # 新版 CLI 入口
├── backend/                  # 后端代码（API、服务、Agent、配置）
├── frontend/                 # React + TypeScript 前端
├── modules/                  # 可 CLI 调用的功能模块
├── adapters/                 # 外部工具和本机软件适配
├── core/                     # 通用基础能力
├── patches/                  # 工具补丁配置和加载逻辑
├── scripts/                  # 开发、构建、维护脚本
├── tests/                    # Python 测试
├── docs/                     # 项目自有文档
├── LICENSES/                 # 第三方许可文件
├── vendor/                   # 第三方源码或嵌入工具
├── bin/                      # 本地二进制工具，通常不提交
├── runtime/                  # 运行时状态，通常不提交
└── projects/                 # 用户工作区和产物，通常不提交
```

## 入口文件

- `app.py`：启动 uvicorn、加载 `backend/api/server.py`。
- `cli/main.py`：CLI 主入口；`main.py` 为兼容代理。
- `backend/config/`：集中读取 `.env` 和环境变量；根 `config.py` 为兼容代理。

## `backend/`

后端主维护层，分层如下。

### `backend/api/`

| 子目录/文件 | 职责 |
|---|---|
| `server.py` | FastAPI 应用创建、静态资源、路由挂载 |
| `setup.py` | 路由注册配置 |
| `models.py` | Pydantic 数据模型 |
| `runtime.py` | 运行时管理 |
| `routes/` | 全部路由文件（16个）：system、media、workspace、workbench、assets、files、filebrowser、task_center、log、path_picker、photoshop、adobe、auditor、wechat、browser |

### `backend/services/`

| 文件/目录 | 职责 |
|---|---|
| `media/` | 媒体服务（fetch、encoding、decrypt、workflows） |
| `runtime/` | 外部工具运行时（editor、filebrowser） |
| `workspace.py` | 工作区管理 |
| `workbench.py` | 工作台服务 |
| `task_center.py` | 长任务状态和日志 |
| `photoshop.py` | Photoshop 服务 |
| `photoshop_state.py` | Photoshop 状态管理 |
| `auditor.py` | 审核服务 |
| `fetcher.py` | 视频和字幕获取 |
| `encoder.py` | 转码和切片 |
| `decryptor.py` | 解密服务 |
| `browser_manager.py` | 浏览器控制会话 |
| `system_fonts.py` | 系统字体扫描 |
| `system_monitor.py` | 系统监控 |
| `log_buffer.py` | 日志缓存 |
| `wechat_moments.py` | 朋友圈图片生成 |

### `backend/agent/`

| 文件 | 职责 |
|---|---|
| `service.py` | AI Agent 服务 |
| `tools.py` | Agent 工具实现 |
| `tool_specs.py` | 工具规范定义 |
| `helpers.py` | 辅助函数 |
| `routes.py` | AI 助手直连路由 |

### `backend/config/`

| 文件 | 职责 |
|---|---|
| `settings.py` | 全局配置 |
| `__init__.py` | 重新导出配置，兼容旧导入 |

## `frontend/`

前端工作台，技术栈为 React、TypeScript、Vite。

常用子目录：

- `frontend/src/apps/`：桌面式应用窗口，例如下载器、工作台、文件管理、AI 助手。
- `frontend/src/apps/mediatools/`：MediaTools 内部通用组件和自动化任务 UI。
- `frontend/src/apps/downloader/`：下载器拆分组件。
- `frontend/src/apps/file-manager/`：文件管理器拆分组件。
- `frontend/public/`：静态资源和多语言文本。
- `frontend/dist/`：生产构建产物，由后端服务。

## `services/`

> 当前 `services/` 是旧的兼容预留目录，实际后端代码已在 `backend/services/` 下。

详见 [backend/](#backend) 一节。

## `modules/`

底层能力模块，通常有自己的 `cli.py`。

| 模块 | 职责 |
|---|---|
| `fetcher` | 视频下载、字幕下载、字幕处理、yt-dlp 管理 |
| `encoder` | FFmpeg 转码、音频提取、切片 |
| `decryptor` | 解密工具封装 |
| `assets` | 素材扫描、搜索、预览、文件操作 |
| `workbench` | 字幕分析和片段导出 CLI |
| `editor` | capcut-mate 适配 |
| `adobe` | Adobe 通用、Photoshop、After Effects 自动化 |
| `photoshop` | Photoshop CLI 入口 |
| `auditor` | 素材审核入口 |
| `generator` | 截图、朋友圈图片等生成 |
| `filebrowser` | filebrowser 服务封装 |

## `adapters/`

隔离外部工具、本机软件和第三方运行时差异。服务层应通过 adapter 或 runtime service 调用外部能力，避免把平台细节散落在路由里。

## `core/`

通用基础能力，例如：

- `ffmpeg.py`
- `logger.py`
- `auth.py`
- `validation.py`

## `patches/`

维护外部工具补丁规则。全局规则放这里，运行时覆盖规则放 `runtime/` 或工作区 `manifests/`。

## `vendor/`

第三方项目和嵌入工具目录。这里的 README、CHANGELOG、LICENSE 多数属于上游项目，不视为 MediaTools 主文档。

## `bin/`

本地可执行工具目录。常见文件包括 `ffmpeg`、`ffprobe`、`yt-dlp`、`um-cli`。该目录属于本机环境配置，不应假设每个开发者完全一致。

## `runtime/`

运行状态目录。常见内容包括：

- 当前工作区配置
- 外部进程 PID
- 运行日志
- 临时状态文件

## `projects/`

用户工作区目录，保存下载、字幕、分析、切片、解密和导出产物。

推荐结构见 [WORKFLOW.md](../WORKFLOW.md)。
