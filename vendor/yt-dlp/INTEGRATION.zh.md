# yt-dlp 集成说明

> [English](./INTEGRATION.md)

## 用途

视频信息探测、下载和字幕获取。

## 状态

**核心** - 媒体获取流程必需。

## 维护

- 源码：`vendor/yt-dlp/source/`（上游）
- 可执行文件：`bin/yt-dlp`（通过 `python -m cli.main fetcher ytdlp download` 下载）
- 状态检查：`python -m cli.main fetcher ytdlp status`
- 代码位置：`modules/fetcher/`、`backend/services/fetcher.py`

## 上游信息

- 官方：https://github.com/yt-dlp/yt-dlp
- 平台规则经常变化；下载失败时优先更新
- 原始文档：`vendor/yt-dlp/source/`

## 在 MediaTools 中的使用

| 功能 | 模块 |
|---|---|
| 视频信息 | `modules/fetcher` |
| 下载 | `backend/services/media/fetch.py` |
| 字幕获取 | `modules/fetcher` |
| yt-dlp 管理 | `modules/fetcher/ytdlp.py` |
