# FFmpeg Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Video transcoding, audio extraction, slicing, and media info probing.

## Status

**Core** - Required for media processing workflows.

## Maintenance

- Location: `bin/` or system `PATH`
- Verify: `ffmpeg -version` and `ffprobe -version`
- Code: `core/ffmpeg.py`, `modules/encoder/`, `backend/services/media/encoding.py`

## Usage in MediaTools

| Feature | Module |
|---|---|
| Transcoding | `modules/encoder/transcoder.py` |
| Audio extraction | `modules/encoder/` |
| Slicing | `modules/encoder/` |
| Media info | `core/ffmpeg.py` |

## Installation

Place `ffmpeg.exe` and `ffprobe.exe` in `bin/`, or ensure system `PATH` can access them.
