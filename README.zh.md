# MediaTools

> **[English](./README.md)** | 中文

MediaTools 是一个面向内容创作和本地媒体处理的 Web 工作台。整合视频下载、字幕处理、AI 分析、FFmpeg 转码、素材管理、Adobe 自动化和执行型 AI 助手。

## 入口

| 入口 | 命令 |
|---|---|
| Web 服务 | `python app.py` |
| CLI | `python -m cli.main <module> ...` |
| 前端开发 | `cd frontend && npm run dev` |

## 功能

| 类别 | 功能 |
|---|---|
| **媒体获取** | 通过 `yt-dlp` 下载视频和字幕 |
| **字幕处理** | VTT/SRT 转换、AI 片段分析 |
| **FFmpeg 操作** | 转码、音频提取、单段/批量切片 |
| **工作区管理** | 素材扫描、预览、文件浏览 |
| **解密** | 通过 Unlock Music CLI 解密音乐/媒体 |
| **Adobe 自动化** | Photoshop、After Effects 自动化 |
| **辅助工具** | 素材审核、截图生成、朋友圈图片生成 |
| **AI 助手** | 任务中心、系统状态、日志查看、工具调用 |
| **实验性** | CapCut/capcut-mate 集成 |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+（仅前端开发需要）
- Windows 优先使用 `.bat` 启动脚本

### 安装

```powershell
# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 配置环境
Copy-Item .env.example .env
# 编辑 .env：设置 TEC_CHI_API_KEY，按需调整端口
```

### 准备外部工具

```powershell
python -m cli.main fetcher ytdlp download
```

FFmpeg/ffprobe 应放入 `bin/` 或系统 `PATH`。

### 启动

```powershell
python app.py
```

默认地址：
- Web 工作台：`http://127.0.0.1:7860`
- API 文档：`http://127.0.0.1:7860/docs`

Windows 用户可双击 `start_mediatools.bat`（常规）或 `start_mediatools_dev.bat`（开发）。

## CLI 参考

```powershell
python -m cli.main --help
python -m cli.main fetcher download <url>
python -m cli.main encoder to-h265 input.mp4 --crf 28
python -m cli.main decryptor run -i song.ncm
python -m cli.main generator screenshot video.mp4 00:01:30 -o frame.jpg
```

| 模块 | 用途 |
|---|---|
| `fetcher` | 媒体下载、字幕获取、yt-dlp 管理 |
| `encoder` | 转码、音频提取、切片 |
| `decryptor` | 音乐/媒体解密 |
| `assets` | 素材扫描、搜索、统计 |
| `workbench` | 字幕分析和片段导出 |
| `editor` | 实验性 CapCut/capcut-mate 适配 |
| `photoshop` | Photoshop 自动化 |
| `auditor` | 素材审核流程 |
| `generator` | 截图、朋友圈图片等素材生成 |

## API 概览

FastAPI 路由在 `http://127.0.0.1:7860/docs` 可查看。

| 分组 | 路径前缀 | 文件 |
|---|---|---|
| 系统状态 | `/api/system`, `/api/modules` | `backend/api/routes/system.py` |
| 媒体任务 | `/api/media` | `backend/api/routes/media.py` |
| 工作区 | `/api/workspace` | `backend/api/routes/workspace.py` |
| 工作台 | `/api/workbench` | `backend/api/routes/workbench.py` |
| 素材 | `/api/assets` | `backend/api/routes/assets.py` |
| 文件操作 | `/api/files` | `backend/api/routes/files.py` |
| filebrowser | `/api/filebrowser` | `backend/api/routes/filebrowser.py` |
| 任务中心 | `/api/tasks` | `backend/api/routes/task_center.py` |
| 日志 | `/api/logs` | `backend/api/routes/log.py` |
| Photoshop | `/api/photoshop` | `backend/api/routes/photoshop.py` |
| Adobe/AE | `/api/adobe` | `backend/api/routes/adobe.py` |
| 审核 | `/api/auditor` | `backend/api/routes/auditor.py` |
| 朋友圈 | `/api/wechat_moments` | `backend/api/routes/wechat.py` |
| 浏览器控制 | `/api/browser` | `backend/api/routes/browser.py` |
| AI 助手 | `/api/agent/*` | `backend/agent/routes.py` |

绑定非 localhost 地址时需设置 `API_SECRET_KEY`。

## 项目结构

```
MediaTools/
├── app.py              # Web 服务入口
├── cli/                # CLI 入口
├── backend/            # 后端（API、服务、agent、配置）
│   ├── api/routes/     # API 路由文件
│   ├── services/       # 业务服务
│   ├── agent/          # AI 助手
│   └── config/         # 配置管理
├── frontend/           # React + TypeScript + Vite
├── modules/            # CLI 可调用的功能模块
├── adapters/           # 外部工具适配器
├── core/               # 通用工具
├── patches/            # 工具补丁规则
├── vendor/             # 第三方源码/嵌入工具
├── docs/               # 项目文档
├── tests/              # Python 测试
├── bin/                # 本地二进制工具（不提交）
├── runtime/            # 运行时状态（不提交）
└── projects/           # 工作区数据（不提交）
```

## 文档

- [工作流程](./WORKFLOW.zh.md) | [English](./WORKFLOW.md)
- [架构说明](./ARCHITECTURE.zh.md) | [English](./ARCHITECTURE.md)
- [依赖与命名](./docs/DEPENDENCIES.zh.md) | [English](./docs/DEPENDENCIES.md)
- [外部工具](./docs/TOOLS.zh.md) | [English](./docs/TOOLS.md)

> `vendor/` 包含第三方源码和嵌入工具。每个工具目录下有 `INTEGRATION.md` / `INTEGRATION.zh.md` 说明其在 MediaTools 中的角色。

## 开发

```powershell
python -m pytest
```

前端：

```powershell
cd frontend
npm run typecheck && npm test && npm run build
```

## 已知限制

- `capcut-mate`、Adobe 自动化和审核依赖本机软件和环境
- AI 分析质量取决于字幕质量和模型配置
- `vendor/` 包含第三方文档，非 MediaTools 文档

## License

MIT License
