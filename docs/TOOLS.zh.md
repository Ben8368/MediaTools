# External Tools and Patch System

> [English](./TOOLS.md)

MediaTools 依赖的外部工具及管理方式。

## 工具概览

| 工具 | 用途 | 位置 | 状态 |
|---|---|---|---|
| `yt-dlp` | 视频下载、字幕获取 | `bin/` 或 `vendor/yt-dlp/` | 核心 |
| `ffmpeg` / `ffprobe` | 转码、音频提取、切片 | `bin/` 或系统 PATH | 核心 |
| `um-cli` | 音乐/媒体解密 | `bin/` | 可选 |
| `capcut-mate` | CapCut 实验性集成 | `vendor/capcut-mate/` | 实验性 |
| `filebrowser` | 文件浏览服务 | `vendor/filebrowser/` | 可选 |
| Adobe 自动化 | Photoshop/AE 自动化 | `vendor/adobe/` + 本机软件 | 环境相关 |
| auditor | 素材审核 | `vendor/auditor/` | 环境相关 |

## 原则

1. Web 和 CLI 必须检查工具可用性；提供清晰错误信息
2. 优先从 `bin/` 解析可执行文件，再到系统 `PATH`
3. 上游源码保留在 `vendor/`；不将上游文档混入项目文档
4. 实验性工具不能作为唯一生产流程
5. 排查问题时记录工具版本

## yt-dlp

- 视频信息探测、下载、字幕获取
- 频繁更新；平台规则经常变化
- 检查状态：`python -m cli.main fetcher ytdlp status`

## FFmpeg

- 转码、音频提取、切片、媒体信息探测
- 验证：`ffmpeg -version` 和 `ffprobe -version`
- 如不在 PATH 中，将 `ffmpeg.exe` 和 `ffprobe.exe` 放入 `bin/`

## um-cli

- 上游：<https://git.um-react.app/um/cli> · [最新发布](https://git.um-react.app/um/cli/releases/latest)
- **vendor 树如何追随上游并保留补丁**：见 [VENDOR_UM_CLI.zh.md](./VENDOR_UM_CLI.zh.md)
- 解密加密格式（如 `.ncm`）
- 本地编译需要 Go
- 使用：`python -m cli.main decryptor run -i song.ncm`

## capcut-mate

- CapCut/剪映自动化（实验性）
- 依赖本地服务、端口和上游项目
- 生产导出优先 FFmpeg
- 配置：`CAPCUT_MATE_BASE_URL=http://localhost:30000`

## filebrowser

- 工作区文件浏览
- 维护位置：`backend/services/runtime/filebrowser.py`、`backend/api/routes/filebrowser.py`

## Adobe 自动化

- Photoshop 和 After Effects 自动化
- 依赖本机软件安装和权限
- 实现在：`modules/adobe/`、`backend/api/routes/adobe.py`、`backend/api/routes/photoshop.py`

## 补丁系统

工具补丁管理外部工具和环境差异。

### 加载顺序（后加载的覆盖先加载的）

1. `patches/tool_patches.json` - 全局项目默认值
2. `runtime/tool_patches.json` - 本机临时规则
3. `projects/<workspace>/manifests/tool_patches.json` - 工作区特定偏好

### 规范

- 应进入 `.env` 的密钥不应写入补丁文件
- 全局补丁应保持最小
- 工作区补丁应按上下文记录
- 修改补丁加载逻辑时，更新测试和本文档

### 排查问题

如果工具行为异常：
1. 检查工作区 `manifests/tool_patches.json`
2. 检查 `runtime/tool_patches.json`
3. 检查 `patches/tool_patches.json`
4. 通过 CLI 或 API 状态验证解析的工具路径
