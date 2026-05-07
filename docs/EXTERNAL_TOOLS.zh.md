# 外部工具管理

> **[English](./EXTERNAL_TOOLS.md)**

MediaTools 依赖多个本机工具和第三方项目。本文说明它们的用途、位置和维护方式。

## 工具总览

| 工具 | 用途 | 推荐位置 | 状态 |
|---|---|---|---|
| `yt-dlp` | 视频信息、下载、字幕获取 | `bin/` 或 `vendor/yt-dlp/` | 核心 |
| `ffmpeg` / `ffprobe` | 转码、音频提取、切片、探测 | `bin/` 或系统 PATH | 核心 |
| `um-cli` | 音乐/媒体解密 | `bin/` | 可选 |
| `capcut-mate` | 剪映/CapCut 实验联动 | `vendor/capcut-mate/` | 实验 |
| `filebrowser` | 文件浏览服务 | `vendor/filebrowser/` | 可选 |
| Adobe 自动化组件 | Photoshop/After Effects 自动化 | `vendor/adobe/` 和本机软件 | 环境相关 |
| auditor | 素材审核 | `vendor/auditor/` | 环境相关 |

## 基本原则

- Web 和 CLI 不应假设工具一定存在，必须提供状态检查和清晰错误信息。
- 可执行文件优先从 `bin/` 或配置路径解析，再考虑系统 `PATH`。
- 上游源码放在 `vendor/`，不要把上游 README 混入项目主文档。
- 工具版本可能影响行为，排查问题时先记录版本。
- 实验工具不能成为唯一生产链路，FFmpeg 主线应保持可用。

## yt-dlp

用途：

- 视频元信息探测
- 视频下载
- 字幕下载
- 平台兼容

常用命令：

```powershell
python main.py fetcher ytdlp status
python main.py fetcher ytdlp download
python main.py fetcher ytdlp update
```

维护建议：

- 平台规则变化频繁，遇到下载失败先更新 `yt-dlp`。
- 尽量通过项目封装调用，不要在业务代码里硬编码 yt-dlp 命令。

## FFmpeg

用途：

- 视频转码
- 音频提取
- 单段和批量切片
- 字幕烧录
- 媒体信息探测

检查：

```powershell
ffmpeg -version
ffprobe -version
```

如果系统 PATH 不可用，将 `ffmpeg.exe` 和 `ffprobe.exe` 放入 `bin/`。

## um-cli

用途：

- 解密 `.ncm` 等加密音乐/媒体格式

常用命令：

```powershell
python main.py decryptor --help
python main.py decryptor run -i song.ncm
```

如果本机需要编译 Go 版本，确认 Go 环境可用。

## capcut-mate

用途：

- 剪映/CapCut 自动化实验链路

状态：

- 仍属于实验能力
- 依赖本机服务、端口、上游项目和剪映环境
- 生产导出优先使用 FFmpeg

相关配置：

```text
CAPCUT_MATE_BASE_URL=http://localhost:30000
```

## filebrowser

用途：

- 工作区文件浏览
- 本地文件服务能力

维护位置：

- `backend/services/runtime/filebrowser.py`
- `backend/api/routes/filebrowser.py`
- `modules/filebrowser/`
- `vendor/filebrowser/`

## Adobe 自动化

涉及：

- Photoshop
- After Effects
- COM/CEP/插件桥接

注意：

- 强依赖本机软件安装和权限。
- 文档见 `docs/adobe/`。
- 当前实现以 `modules/adobe/`、`backend/api/routes/adobe.py`、`backend/api/routes/photoshop.py`、`backend/services/photoshop.py`、`backend/services/photoshop_state.py` 为准。

## 排查清单

1. 工具是否存在于 `bin/` 或系统 PATH。
2. 版本是否可读取。
3. `.env` 中的路径、端口、API 配置是否正确。
4. Web 任务中心和日志是否有详细错误。
5. 对应 CLI 最小命令是否可运行。
