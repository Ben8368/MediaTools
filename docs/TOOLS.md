# External Tools and Patch System

> [中文版](./TOOLS.zh.md)

External tools that MediaTools depends on, and how they are managed.

## Tool Overview

| Tool | Purpose | Location | Status |
|---|---|---|---|
| `yt-dlp` | Video download, subtitle fetch | `bin/` or `vendor/yt-dlp/` | Core |
| `ffmpeg` / `ffprobe` | Transcode, audio extract, slice | `bin/` or system PATH | Core |
| `um-cli` | Music/media decryption | `bin/` | Optional |
| `capcut-mate` | CapCut experimental integration | `vendor/capcut-mate/` | Experimental |
| `filebrowser` | File browsing service | `vendor/filebrowser/` | Optional |
| Adobe automation | Photoshop/AE automation | `vendor/adobe/` + local software | Environment-dependent |
| auditor | Asset auditing | `vendor/auditor/` | Environment-dependent |

## Principles

1. Web and CLI must check tool availability; provide clear error messages
2. Resolve executables from `bin/` first, then system `PATH`
3. Upstream source code stays in `vendor/`; do not mix upstream docs into project documentation
4. Experimental tools must not be the sole production pipeline
5. Record tool versions when troubleshooting

## yt-dlp

- Video metadata probing, downloading, subtitle fetching
- Update frequently; platform rules change often
- Check status: `python -m cli.main fetcher ytdlp status`

## FFmpeg

- Transcoding, audio extraction, slicing, media info probing
- Verify: `ffmpeg -version` and `ffprobe -version`
- If not in PATH, place `ffmpeg.exe` and `ffprobe.exe` in `bin/`

## um-cli

- Upstream: <https://git.um-react.app/um/cli> · [Latest release](https://git.um-react.app/um/cli/releases/latest)
- Decrypt encrypted formats (e.g., `.ncm`)
- Requires Go for local compilation
- Use: `python -m cli.main decryptor run -i song.ncm`

## capcut-mate

- CapCut/JianYing automation (experimental)
- Depends on local services, ports, and upstream project
- Prefer FFmpeg for production exports
- Config: `CAPCUT_MATE_BASE_URL=http://localhost:30000`

## filebrowser

- Workspace file browsing
- Maintained in: `backend/services/runtime/filebrowser.py`, `backend/api/routes/filebrowser.py`

## Adobe Automation

- Photoshop and After Effects automation
- Depends on local software installation and permissions
- Implementation in: `modules/adobe/`, `backend/api/routes/adobe.py`, `backend/api/routes/photoshop.py`

## Patch System

Tool patches manage external tool and environment differences.

### Loading Order (later overrides earlier)

1. `patches/tool_patches.json` - Global project defaults
2. `runtime/tool_patches.json` - Machine-local temporary rules
3. `projects/<workspace>/manifests/tool_patches.json` - Workspace-specific preferences

### Guidelines

- Secrets that belong in `.env` should not be in patch files
- Global patches should be minimal
- Workspace patches should be documented by context
- When changing patch loading logic, update tests and this document

### Troubleshooting

If a tool behaves unexpectedly:
1. Check workspace `manifests/tool_patches.json`
2. Check `runtime/tool_patches.json`
3. Check `patches/tool_patches.json`
4. Verify resolved tool path via CLI or API status
