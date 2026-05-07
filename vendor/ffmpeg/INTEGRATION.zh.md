# FFmpeg 集成说明

> [English](./INTEGRATION.md)

## 用途

视频转码、音频提取、切片和媒体信息探测。

## 状态

**核心** - 媒体处理流程必需。

## 维护

- 位置：`bin/` 或系统 `PATH`
- 验证：`ffmpeg -version` 和 `ffprobe -version`
- 代码：`core/ffmpeg.py`、`modules/encoder/`、`backend/services/media/encoding.py`

## 在 MediaTools 中的使用

| 功能 | 模块 |
|---|---|
| 转码 | `modules/encoder/transcoder.py` |
| 音频提取 | `modules/encoder/` |
| 切片 | `modules/encoder/` |
| 媒体信息 | `core/ffmpeg.py` |

## 安装

将 `ffmpeg.exe` 和 `ffprobe.exe` 放入 `bin/`，或确保系统 `PATH` 可访问。
