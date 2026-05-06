# MediaTools

[![CI](https://github.com/yourusername/MediaTools/workflows/CI/badge.svg)](https://github.com/yourusername/MediaTools/actions)
[![Lint](https://github.com/yourusername/MediaTools/workflows/Lint/badge.svg)](https://github.com/yourusername/MediaTools/actions)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)](https://github.com/yourusername/MediaTools)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

面向内容创作场景的本地媒体工作台。当前主入口为 `FastAPI + Web 前端 + Agent`，同时保留 CLI 作为底层能力入口。

## 当前能力

1. 视频下载与原始字幕获取（YouTube + 多平台）
2. 字幕下载（原语言 + 中文翻译）
3. 字幕分析、亮点提取、自动切片
4. FFmpeg 转码、音频提取、批量导出
5. 音乐文件解密并归档到素材库
6. PSD 批量处理（文案和字体修改）
7. 素材生成（视频截图 + 朋友圈图片）
8. 素材审核（Auditor 集成）
9. 单项目工作区管理
10. Agent 驱动的执行型工作流

## 相关文档

- [WORKFLOW.md](./WORKFLOW.md) - 工作流程说明
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架构设计文档
- [API 文档](http://127.0.0.1:7860/docs) - FastAPI 自动生成的交互式文档

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+ (前端开发)
- Go 1.21+ (仅编译 `um-cli` 时需要)
- Windows 推荐直接使用仓库内脚本启动 Web 服务

### 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 开发环境额外依赖
pip install -r requirements-dev.txt

# 前端依赖（可选）
cd frontend && npm install
```

### 配置环境变量

```bash
cp .env.example .env
```

然后在 `.env` 中补齐：
- `TEC_CHI_API_KEY` - AI 分析 API 密钥
- `OPENAI_BASE_URL` - OpenAI 兼容 API 地址
- `ANALYSIS_MODEL` - 使用的模型名称

### 初始化外部工具

```powershell
# 下载 yt-dlp
python main.py fetch ytdlp download

# 手动放置 ffmpeg / ffprobe 到 bin/

# 编译 um-cli
.\scripts\build-um.ps1
```

### 启动服务

**生产模式**（推荐日常使用）：
```bash
# 命令行启动
python app.py

# Windows 双击启动
start_mediatools.bat
```

**开发模式**（前端热更新）：
```bash
# 命令行启动
python app.py --reload

# Windows 双击启动
start_mediatools_dev.bat
```

访问 http://127.0.0.1:7860 使用 Web 界面。

### CLI 使用

```bash
# 查看帮助
python main.py --help

# 下载视频和字幕
python main.py fetch download https://youtube.com/watch?v=xxx --video --subtitles original_only

# 视频转码
python main.py encode to-h265 input.mp4 --crf 28

# 音乐解密
python main.py decrypt run -i song.ncm

# 更多示例见下方
```

## 当前推荐流程

1. 选择当前项目工作区
2. 下载视频和原始字幕
3. 用 AI 分析字幕亮点
4. 自动切片并导出带字幕片段
5. 在剪辑工作台中微调后再次导出

`capcut-mate` / 剪映联动仍属于实验能力，当前更稳定的主线是 `FFmpeg + 字幕分析 + 自动切片`。

## 模块概览

| 模块 | CLI | 说明 |
|---|---|---|
| `fetch` | `python main.py fetch` | 视频下载、字幕下载（原语言+中文）、视频信息探测、字幕格式转换 |
| `encode` | `python main.py encode` | 转码、音频提取、FFmpeg 切片 |
| `decrypt` | `python main.py decrypt` | 音乐解密，可选加入素材库 |
| `assets` | `python main.py assets` | 扫描当前工作区或指定目录 |
| `edit` | `python main.py edit` | capcut-mate 实验链路与 FFmpeg 备选切片 |
| `photoshop` | `python main.py photoshop` | PSD 批量处理（文案和字体修改）|
| `generator` | `python main.py generator` | 素材生成（视频截图 + 朋友圈图片）|
| `auditor` | `python main.py auditor` | 素材审核 |

桌面端当前包含：

1. 控制台总览
2. 媒体获取
3. 编码转码
4. 音乐解密
5. 素材库
6. 剪辑工作台
7. AI 助手
8. 工作区

## 使用示例

### 媒体获取

```bash
# 获取视频信息
python main.py fetch info https://youtube.com/watch?v=xxx

# 下载视频和原始字幕
python main.py fetch download https://youtube.com/watch?v=xxx --video --video-codec h264 --subtitles original_only --subtitle-format srt

# 仅下载原始字幕
python main.py fetch download https://youtube.com/watch?v=xxx --subtitles original_only --subtitle-format srt

# 查看 / 更新 yt-dlp
python main.py fetch ytdlp status
python main.py fetch ytdlp update
```

### 媒体转码与切片

```bash
# H.265 转码
python main.py encode to-h265 input.mp4 --crf 28

# 提取音频
python main.py encode extract-audio input.mp4

# 单次切片
python main.py encode slice input.mp4 --start 00:00:10 --end 00:00:25

# 快速切片
python main.py encode slice input.mp4 --start 00:00:10 --end 00:00:25 --fast
```

### 音乐解密

```bash
# 解密单文件
python main.py decrypt run -i song.ncm

# 批量解密
python main.py decrypt run -i .\encrypted_music\ -o .\output\

# 查看状态 / 编译 um-cli
python main.py decrypt status
python main.py decrypt build
```

### 素材管理

```bash
# 扫描目录
python main.py assets scan
python main.py assets scan .\projects\default\

# 搜索 / 统计
python main.py assets search "subtitle"
python main.py assets stats --directory .\projects\default\
```

## AI 助手

桌面端内置全局 AI 助手，支持：

1. 配置 `API Base URL / API Key / Model`
2. 测试连接
3. 执行下载、字幕分析、自动切片、转码、解密入库等任务

推荐任务示例：
```text
下载这个视频，自动获取可分析字幕，分析出最值得切的 3 个片段，并直接切片输出到当前项目工作区。
```

## 工作区模式

当前项目采用单项目工作区模型，当前工作区会持久化到：

```text
runtime/workspace.json
```

默认工作区结构：

```text
projects/default/
├── inputs/
├── downloads/
├── decrypted/
├── transcoded/
├── clips/
├── subtitles/
├── analysis/
├── assets/
├── imports/
├── cache/
├── logs/
├── manifests/
└── exports/
```

说明：
1. 视频默认下载到 `downloads/`，字幕会归档到 `subtitles/`
2. 解密结果默认落到 `decrypted/`，可选复制到 `assets/`
3. 转码结果默认落到 `transcoded/`
4. 自动切片与工作台批量导出默认落到 `clips/`
5. 分析 JSON 默认落到 `analysis/`
6. 剪辑工作台和素材库读取的是当前工作区，而不是仓库根目录

## 开发

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试文件
python -m pytest tests/test_workspace.py

# 查看覆盖率
python -m pytest --cov=. --cov-report=html
```

### 代码质量检查

```bash
# 代码格式化
black .

# Linting
ruff check .

# 类型检查
mypy .
```

### 前端开发

```bash
cd frontend

# 开发服务器
npm run dev

# 类型检查
npm run typecheck

# 运行测试
npm test

# 构建
npm run build
```

## 目录说明

```text
MediaTools/
├── main.py                 # CLI 入口
├── app.py                  # Web 服务入口
├── config.py               # 配置管理
├── .env.example            # 环境变量模板
├── start_mediatools.bat    # Windows 启动脚本（生产）
├── start_mediatools_dev.bat # Windows 启动脚本（开发）
├── adapters/               # 外部工具适配器
├── core/                   # 核心功能
├── modules/                # 功能模块
├── patches/                # 补丁入口
├── services/               # 业务服务层
├── gui/                    # GUI 相关（已废弃）
├── vendor/                 # 第三方工具
├── bin/                    # 二进制工具
├── runtime/                # 运行时状态
├── projects/               # 项目工作区
├── scripts/                # 辅助脚本
├── tests/                  # 测试文件
└── frontend/               # Web 前端
```

其中：
1. `adapters/` 封装 `yt-dlp`、`ffmpeg`、`um-cli` 等外部工具
2. `patches/` 提供补丁入口，便于兼容上游更新
3. `services/` 是当前后端能力核心
4. `runtime/` 保存工作区和运行时状态
5. `projects/` 保存默认工作区及产物
6. `vendor/` 存放 `capcut-mate` 与 `unlock-music`

## Patch Config

外部工具补丁配置按以下顺序加载：

1. `patches/tool_patches.json`
2. `runtime/tool_patches.json`
3. `projects/<current-workspace>/manifests/tool_patches.json`

后加载的配置可以覆盖前面的规则。可参考 `patches/tool_patches.example.json`。

## 已知限制

1. `capcut-mate` 仍是实验链路，不建议作为唯一主流程依赖
2. 字幕质量依赖平台返回结果
3. 自动化测试仍不完整

## 故障排查

| 问题 | 说明 |
|---|---|
| `yt-dlp 未找到` | 执行 `python main.py fetch ytdlp download` |
| `FFmpeg 未找到` | 将 `ffmpeg` / `ffprobe` 放到 `bin/` |
| `um-cli 未找到` | 执行 `.\scripts\build-um.ps1` |
| `AI 分析失败` | 检查 `.env` 中的 `TEC_CHI_API_KEY` / `OPENAI_BASE_URL` / `ANALYSIS_MODEL` |
| `自动切片没有字幕` | 确保原始字幕已成功下载，并使用可分析的字幕文件 |

## 技术栈

- **后端**: FastAPI + Python 3.11+
- **前端**: React 18 + TypeScript + Vite
- **媒体处理**: FFmpeg + yt-dlp
- **音乐解密**: Unlock Music CLI (Go)
- **AI 集成**: OpenAI 兼容 API
- **实验功能**: capcut-mate（剪映联动）

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
