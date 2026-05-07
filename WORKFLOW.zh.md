# MediaTools 工作流程

> [English](./WORKFLOW.md)

推荐生产流程：`yt-dlp + 字幕分析 + FFmpeg 切片 + 工作台复核`。

## 1. 启动

```powershell
python app.py
```

- 工作台：`http://127.0.0.1:7860`
- API 文档：`http://127.0.0.1:7860/docs`

绑定非 localhost 前设置 `API_SECRET_KEY`。

## 2. 工作区

工作区状态存储在 `runtime/workspace.json`。推荐结构：

```
projects/default/
├── downloads/      # 视频和原始字幕
├── subtitles/      # 可分析字幕
├── analysis/       # AI 分析结果
├── clips/          # 自动切片
├── exports/        # 工作台导出
├── decrypted/      # 解密输出
├── assets/         # 精选素材
└── transcoded/     # 转码输出
```

## 3. 主流程：下载 → 分析 → 切片

1. 在 Web 工作台设置工作区
2. 下载视频和字幕（优先 SRT）
3. 用 AI 助手或工作台分析亮点
4. 通过 FFmpeg 自动导出片段
5. 在工作台复核和微调

AI 助手示例：
```
下载这个视频，获取字幕，找出最有价值的3个片段，导出到当前工作区。
https://www.youtube.com/watch?v=xxxx
```

## 4. 转码和手动切片

```powershell
python -m cli.main encoder to-h265 input.mp4 --crf 28
python -m cli.main encoder extract-audio input.mp4
python -m cli.main encoder slice input.mp4 --start 00:00:10 --end 00:00:25
```

## 5. 解密

```powershell
python -m cli.main decryptor run -i song.ncm
python -m cli.main decryptor run -i .\encrypted_music\ -o .\projects\default\decrypted\
```

## 6. 素材和文件管理

素材管理索引当前工作区。扫描整个工作区：

```powershell
projects/default/
```

## 7. Adobe 和扩展工具

Adobe、审核、朋友圈、capcut-mate 依赖本机环境。验证：
- 软件已安装且允许自动化
- 工具在 `vendor/` 或 `bin/`
- 端口和权限正确

稳定导出优先 FFmpeg；capcut-mate 是实验性的。

## 8. CLI 使用

CLI 用于批量处理、调试和状态检查。日常工作流优先使用 Web 工作台。

```powershell
python -m cli.main --help
python -m cli.main fetcher ytdlp status
python -m cli.main photoshop status
```

## 9. 排查问题

1. 检查 Web UI 的任务中心和日志
2. 在 `http://127.0.0.1:7860/docs` 验证 API
3. 检查 `.env` 配置
4. 验证 `bin/` 或系统 `PATH` 中的工具
5. 运行模块 `status` 命令
6. 运行相关测试

## 10. 边界说明

- 字幕分析质量取决于原始字幕质量
- 自动填充有帮助，但关键片段需要人工复核
- `vendor/` 文档属于上游项目
