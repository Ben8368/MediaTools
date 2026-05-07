# MediaTools

> **[English](./README.md)** - 英文版本是项目默认入口。

MediaTools 是一个面向内容创作和本地素材处理的 Web 工作台。它把视频下载、字幕处理、AI 分析、FFmpeg 转码/切片、音乐解密、素材管理、文件管理、Adobe 自动化和执行型 AI 助手整合到同一个项目里。

当前主入口是：

- Web 服务：`python app.py`
- Web 前端：已构建版本由后端直接服务；开发时可单独运行 `frontend`
- CLI：`python main.py <module> ...`

## 当前能力

- 视频信息探测、下载和字幕获取，底层使用 `yt-dlp`
- 字幕清洗、VTT/SRT 转换和 AI 片段分析
- FFmpeg 转码、音频提取、单段切片和批量切片
- 当前工作区管理、素材扫描、素材预览和文件浏览
- 音乐/媒体解密，底层可接入 Unlock Music CLI
- Photoshop、After Effects 和其他 Adobe 自动化适配
- 素材审核、截图生成、朋友圈图片生成等辅助工具
- 任务中心、系统状态、日志查看和 AI 助手工具调用
- 实验性 CapCut/capcut-mate 联动

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+，仅前端开发时需要
- Go 1.21+，仅编译 `um-cli` 时需要
- Windows 环境优先使用仓库内的 `.bat` 启动脚本

### 安装依赖

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

前端开发依赖：

```powershell
cd frontend
npm install
```

### 配置环境变量

复制 `.env.example` 为 `.env`，按需填写：

```powershell
Copy-Item .env.example .env
```

常用配置：

- `TEC_CHI_API_KEY`：AI 分析和 AI 助手使用的 API Key
- `OPENAI_BASE_URL`：OpenAI 兼容接口地址
- `ANALYSIS_MODEL`：字幕分析/助手默认模型
- `GUI_SERVER_NAME`、`GUI_SERVER_PORT`：后端监听地址和端口
- `API_SECRET_KEY`：绑定到非本机地址时建议设置
- `WORKSPACE_ALLOWED_ROOTS`：允许选择的工作区根目录

### 准备外部工具

```powershell
python main.py fetcher ytdlp download
python main.py fetcher ytdlp status
```

FFmpeg/ffprobe 建议放入 `bin/`，或确保系统 `PATH` 可访问。Unlock Music CLI 可通过项目脚本或手动方式放入 `bin/`。

### 启动

```powershell
python app.py
```

默认访问地址：

- Web 工作台：`http://127.0.0.1:7860`
- API 文档：`http://127.0.0.1:7860/docs`

Windows 也可以双击：

- `start_mediatools.bat`：常规启动
- `start_mediatools_dev.bat`：开发启动

后端热重载：

```powershell
python app.py --reload
```

前端开发：

```powershell
cd frontend
npm run dev
```

## CLI 用法

```powershell
python main.py --help
python main.py fetcher --help
python main.py encoder --help
python main.py workbench --help
```

规范模块名：

| 模块 | 用途 |
|---|---|
| `fetcher` | 媒体下载、字幕下载、yt-dlp 管理 |
| `encoder` | 转码、音频提取、切片 |
| `decryptor` | 音乐/媒体解密 |
| `assets` | 素材扫描、搜索、统计 |
| `workbench` | 字幕分析和片段导出 |
| `editor` | 实验性 CapCut/capcut-mate 适配 |
| `photoshop` | Photoshop 自动化 |
| `auditor` | 素材审核流程 |
| `generator` | 截图、朋友圈图片等素材生成 |

兼容旧别名仍可使用：

- `fetch` -> `fetcher`
- `encode` -> `encoder`
- `decrypt` -> `decryptor`
- `edit` -> `editor`

示例：

```powershell
python main.py fetcher ytdlp status
python main.py fetcher download https://youtube.com/watch?v=xxxx --video --subtitles original_only
python main.py encoder to-h265 input.mp4 --crf 28
python main.py encoder slice input.mp4 --start 00:00:10 --end 00:00:25
python main.py decryptor run -i song.ncm
python main.py generator screenshot video.mp4 00:01:30 -o frame.jpg
```

## 推荐工作流

1. 在 Web 工作台里设置当前项目工作区。
2. 下载视频和可分析字幕。
3. 使用 AI 助手或工作台分析字幕亮点。
4. 自动生成片段建议并用 FFmpeg 导出 clips。
5. 在工作台中复核、微调、再次导出。
6. 在素材管理或文件管理中查看最终产物。

当前最稳的生产主线是 `yt-dlp + 字幕分析 + FFmpeg 切片`。`capcut-mate` 和部分 Adobe 联动属于可用但仍需按环境验证的扩展能力。

## 项目结构

```text
MediaTools/
├── app.py                    # Web 服务入口，启动 services/api_server.py
├── main.py                   # 统一 CLI 入口
├── config.py                 # 环境变量和路径配置
├── frontend/                 # React + TypeScript + Vite 前端
├── services/                 # FastAPI 路由、业务服务、任务中心
├── modules/                  # CLI 模块和底层能力封装
├── adapters/                 # 外部工具/运行时适配器
├── core/                     # 通用基础能力
├── patches/                  # 外部工具补丁规则
├── scripts/                  # 开发和维护脚本
├── tests/                    # Python 测试
├── vendor/                   # 第三方源码或嵌入工具
├── bin/                      # 本地二进制工具，通常不提交
├── runtime/                  # 运行时状态，通常不提交
└── projects/                 # 工作区数据，通常不提交
```

## 文档入口

- [文档索引](./docs/README.md)
- [工作流说明](./WORKFLOW.zh.md) | [English](./WORKFLOW.md)
- [当前架构](./ARCHITECTURE.zh.md) | [English](./ARCHITECTURE.md)
- [变更记录](./CHANGELOG.zh.md) | [English](./CHANGELOG.md)
- [API 概览](./docs/API_OVERVIEW.zh.md) | [English](./docs/API_OVERVIEW.md)
- [前端结构](./docs/FRONTEND_OVERVIEW.zh.md) | [English](./docs/FRONTEND_OVERVIEW.md)
- [目录结构](./docs/DIRECTORY_STRUCTURE.zh.md) | [English](./docs/DIRECTORY_STRUCTURE.md)
- [外部工具管理](./docs/EXTERNAL_TOOLS.zh.md) | [English](./docs/EXTERNAL_TOOLS.md)
- [任务中心](./docs/TASK_QUEUE.zh.md) | [English](./docs/TASK_QUEUE.md)
- [补丁系统](./docs/PATCH_SYSTEM.zh.md) | [English](./docs/PATCH_SYSTEM.md)
- [vendor 组织规范](./docs/VENDOR_ORGANIZATION.zh.md) | [English](./docs/VENDOR_ORGANIZATION.md)
- [模块依赖](./docs/MODULE_DEPENDENCIES.zh.md) | [English](./docs/MODULE_DEPENDENCIES.md)
- [命名规范](./docs/NAMING_CONVENTIONS.zh.md) | [English](./docs/NAMING_CONVENTIONS.md)
- [工具路线](./docs/TOOL_FACTIONS.zh.md) | [English](./docs/TOOL_FACTIONS.md)

## 开发

```powershell
python -m pytest
```

前端：

```powershell
cd frontend
npm run typecheck
npm test
npm run build
```

代码格式和静态检查按 `pyproject.toml`、`.pre-commit-config.yaml` 和前端配置执行。

## 已知限制

- 部分历史文档仍是专题设计材料，不一定代表当前实现，优先以根 README、`WORKFLOW.md`、`ARCHITECTURE.md` 和 `docs/README.md` 为准。
- `capcut-mate`、Adobe 自动化和素材审核依赖本机软件、端口、插件和外部工具版本。
- AI 字幕分析质量取决于字幕质量、模型配置和 API 可用性。
- `vendor/` 中包含第三方项目文档，不属于 MediaTools 自有说明文档。

## License

MIT License
