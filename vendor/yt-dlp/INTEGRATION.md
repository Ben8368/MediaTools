# yt-dlp Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Video metadata probing, downloading, and subtitle extraction.

## Status

**Core** - Required for media acquisition workflows.

## Maintenance

- Source: `vendor/yt-dlp/source/` (upstream)
- Executable: `bin/yt-dlp` (downloaded via `python -m cli.main fetcher ytdlp download`)
- Status check: `python -m cli.main fetcher ytdlp status`
- Code location: `modules/fetcher/`, `backend/services/fetcher.py`

## Upstream

- Official: https://github.com/yt-dlp/yt-dlp
- Platform rules change frequently; update when downloads fail
- Original docs: `vendor/yt-dlp/source/`

## Usage in MediaTools

| Feature | Module |
|---|---|
| Video info | `modules/fetcher` |
| Download | `backend/services/media/fetch.py` |
| Subtitle fetch | `modules/fetcher` |
| yt-dlp management | `modules/fetcher/ytdlp.py` |
