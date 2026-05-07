# MediaTools 工作流

> **[English](./WORKFLOW.md)**

这份文档描述当前推荐使用的真实流程。旧的 Gradio/GUI 文档、早期方案和第三方工具说明不再作为主入口；需要查专题资料时从 `docs/README.md` 进入。

## 1. 启动工作台

```powershell
python app.py
```

默认访问：

- 工作台：`http://127.0.0.1:7860`
- API 文档：`http://127.0.0.1:7860/docs`

开发时可同时启动前端：

```powershell
cd frontend
npm run dev
```

后端绑定到非本机地址前，应设置 `API_SECRET_KEY`。

## 2. 设置工作区

MediaTools 使用“当前工作区”组织下载、分析、导出和素材扫描结果。工作区状态保存在：

```text
runtime/workspace.json
```

推荐结构：

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

常见约定：

- `downloads/`：下载的视频和原始字幕
- `subtitles/`：可分析/可复用字幕
- `analysis/`：AI 分析 JSON 或片段建议
- `clips/`、`exports/`：自动切片和工作台导出结果
- `decrypted/`：解密输出
- `assets/`：整理后可复用素材

## 3. 主流程：下载、分析、切片

最稳的生产链路是：

```text
设置工作区
-> 下载视频和字幕
-> 清洗/转换字幕
-> AI 分析片段亮点
-> FFmpeg 自动切片
-> 工作台复核
-> 导出 clips
```

推荐做法：

1. 在下载器/媒体获取功能中输入视频 URL。
2. 同时下载视频和字幕，字幕优先保存为 SRT。
3. 使用 AI 助手或工作台生成片段建议。
4. 让系统自动扩边并用 FFmpeg 导出。
5. 在工作台里检查时间点、原文和中文简介。
6. 需要时手动微调后重新导出。

AI 助手可使用类似任务：

```text
下载这个视频，获取可分析字幕，找出最值得切的 3 个片段，并导出到当前工作区。
https://www.youtube.com/watch?v=xxxx
```

## 4. 工作台复核

工作台负责把字幕分析结果变成可复核的片段列表。

典型操作：

1. 载入当前工作区的视频和字幕。
2. 设置片段数量。
3. 分析字幕，生成片段建议。
4. 查看建议 JSON、片段表和时间轴概览。
5. 调整开始时间、结束时间、中文简介和原文。
6. 批量导出。

当自动链路已经跑完，但需要人工判断节奏、语义或边界时，优先回到工作台复核。

## 5. 转码和手动切片

FFmpeg 能力由 `encoder` 模块和后端媒体服务提供。

CLI 示例：

```powershell
python main.py encoder to-h265 input.mp4 --crf 28
python main.py encoder extract-audio input.mp4
python main.py encoder slice input.mp4 --start 00:00:10 --end 00:00:25
```

适合场景：

- 单独转码
- 提取音频
- 快速导出一个明确时间段
- 自动链路失败时手动补救

## 6. 音乐/媒体解密

解密流程由 `decryptor` 模块和 `services/media_decrypt.py` 支撑。

CLI 示例：

```powershell
python main.py decryptor run -i song.ncm
python main.py decryptor run -i .\encrypted_music\ -o .\projects\default\decrypted\
```

推荐将成功解密后的素材复制或输出到当前工作区的 `assets/` 或 `decrypted/`，再通过素材管理扫描。

## 7. 素材和文件管理

素材管理更像“当前工作区索引器”，不是重型资产数据库。

推荐扫描整个工作区，而不只是 `assets/`：

```text
projects/default/
```

这样可以同时看到：

- 下载结果
- 字幕和分析文件
- 转码产物
- clips 和 exports
- 解密素材

文件管理和预览能力用于浏览工作区、选择路径、检查输出文件。

## 8. Adobe 和扩展能力

Adobe、Photoshop、After Effects、素材审核、朋友圈图生成、capcut-mate 等能力已经纳入项目，但依赖本机环境。

使用前先检查：

- 相关软件是否安装并允许自动化
- `vendor/` 或 `bin/` 中工具是否存在
- 端口和权限是否正确
- API/插件配置是否完整

`capcut-mate` 当前仍是实验链路；稳定导出优先使用 FFmpeg。

## 9. CLI 的定位

CLI 适合批处理、调试、工具状态检查和脚本化任务。完整日常工作流优先使用 Web 工作台。

```powershell
python main.py --help
python main.py fetcher ytdlp status
python main.py photoshop status
python main.py auditor status
```

## 10. 排查顺序

遇到问题时建议按这个顺序查：

1. 看 Web 任务中心和日志。
2. 打开 `http://127.0.0.1:7860/docs` 验证 API 是否可用。
3. 检查 `.env` 中的模型、API、端口和工作区配置。
4. 检查 `bin/` 或系统 `PATH` 中的 `ffmpeg`、`ffprobe`、`yt-dlp`、`um-cli`。
5. 用 CLI 跑对应模块的 `status` 或最小命令。
6. 运行相关测试。

## 11. 已知边界

- 字幕分析强依赖平台字幕质量。
- 自动扩边能减少截断，但关键片段仍建议人工复核。
- CLI 和 Web 的能力覆盖正在收敛，最新完整链路通常先出现在 Web 服务层。
- 第三方工具文档在 `vendor/` 中，仅代表上游项目。
