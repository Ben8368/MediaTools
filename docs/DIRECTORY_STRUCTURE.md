# Directory Structure

> [中文版](./DIRECTORY_STRUCTURE.zh.md) · Chinese

This document describes the current directory responsibilities in MediaTools. Third-party project directory structures are documented in their respective upstream docs under `vendor/`.

## Root Directory

```text
MediaTools/
├── app.py                    # Web service entry
├── main.py                   # Unified CLI entry
├── config.py                 # Configuration reading and defaults
├── cli/                      # New CLI entry point
├── backend/                  # Backend code (API, services, Agent, config)
├── frontend/                 # React + TypeScript frontend
├── modules/                  # CLI-callable functional modules
├── adapters/                 # External tool and local software adapters
├── core/                     # General-purpose utilities
├── patches/                  # Tool patch configuration and loading logic
├── scripts/                  # Development, build, and maintenance scripts
├── tests/                    # Python tests
├── docs/                     # Project-owned documentation
├── LICENSES/                 # Third-party license files
├── vendor/                   # Third-party source or embedded tools
├── bin/                      # Local binaries, typically not committed
├── runtime/                  # Runtime state, typically not committed
└── projects/                 # User workspaces and artifacts, typically not committed
```

## Entry Files

- `app.py`: Starts uvicorn, loads `backend/api/server.py`.
- `cli/main.py`: Dispatches CLI commands to `modules/*/cli.py`; `main.py` is a compatibility proxy.
- `backend/config/`: Centralized `.env` and environment variable reading; root `config.py` is a compatibility proxy.

## `backend/`

The main backend maintenance layer, structured as follows.

### `backend/api/`

| Subdirectory / File | Responsibility |
|---|---|
| `server.py` | FastAPI application creation, static assets, route mounting |
| `setup.py` | Route registration configuration |
| `models.py` | Pydantic data models |
| `runtime.py` | Runtime management |
| `routes/` | All route files (16): system, media, workspace, workbench, assets, files, filebrowser, task_center, log, path_picker, photoshop, adobe, auditor, wechat, browser |

### `backend/services/`

| File / Directory | Responsibility |
|---|---|
| `media/` | Media services (fetch, encoding, decrypt, workflows) |
| `runtime/` | External tool runtimes (editor, filebrowser) |
| `workspace.py` | Workspace management |
| `workbench.py` | Workbench service |
| `task_center.py` | Long-running task state and logs |
| `photoshop.py` | Photoshop service |
| `photoshop_state.py` | Photoshop state management |
| `auditor.py` | Auditing service |
| `fetcher.py` | Video and subtitle fetching |
| `encoder.py` | Transcoding and slicing |
| `decryptor.py` | Decryption service |
| `browser_manager.py` | Browser control session management |
| `system_fonts.py` | System font scanning |
| `system_monitor.py` | System monitoring |
| `log_buffer.py` | Log buffering |
| `wechat_moments.py` | WeChat Moments image generation |

### `backend/agent/`

| File | Responsibility |
|---|---|
| `service.py` | AI Agent service |
| `tools.py` | Agent tool implementations |
| `tool_specs.py` | Tool specification definitions |
| `helpers.py` | Helper functions |
| `routes.py` | AI assistant direct routes |

### `backend/config/`

| File | Responsibility |
|---|---|
| `settings.py` | Global configuration |
| `__init__.py` | Re-exports config for compatibility with old imports |

## `frontend/`

Frontend workbench, built with React, TypeScript, and Vite.

Common subdirectories:

- `frontend/src/apps/`: Desktop-style application windows, e.g., Downloader, Workbench, File Manager, AI Assistant, Browser.
- `frontend/src/apps/mediatools/`: MediaTools shared components and automation task UI.
- `frontend/src/apps/downloader/`: Downloader split components.
- `frontend/src/apps/file-manager/`: File manager split components.
- `frontend/public/`: Static assets and multilingual text.
- `frontend/dist/`: Production build output, served by the backend.

## `modules/`

Underlying capability modules, typically with their own `cli.py`.

| Module | Responsibility |
|---|---|
| `fetcher` | Video downloading, subtitle processing, yt-dlp management |
| `encoder` | FFmpeg transcoding, audio extraction, slicing |
| `decryptor` | Decryption utility |
| `assets` | Asset scanning, searching, previewing, file operations |
| `workbench` | Subtitle analysis and segment export CLI |
| `editor` | capcut-mate adapter |
| `adobe` | Adobe general, Photoshop, After Effects automation |
| `photoshop` | Photoshop CLI entry |
| `auditor` | Asset auditing entry |
| `generator` | Screenshot generation, WeChat moments images, and other generators |
| `filebrowser` | filebrowser service wrapper |

## `adapters/`

Isolates external tool, local software, and third-party runtime differences. Service layers should call external capabilities through adapters or runtime services, avoiding scattering platform details in routes.

## `core/`

General-purpose utilities, such as:

- `ffmpeg.py`
- `logger.py`
- `auth.py`
- `validation.py`

## `patches/`

Maintains external tool patch rules. Global rules go here; runtime overrides go in `runtime/` or workspace `manifests/`.

## `vendor/`

Third-party projects and embedded tools directory. README, CHANGELOG, and LICENSE files here mostly belong to upstream projects and are not considered main MediaTools documentation.

## `bin/`

Local executable tool directory. Common files include `ffmpeg`, `ffprobe`, `yt-dlp`, `um-cli`. This directory is environment-specific and should not assume every developer has an identical setup.

## `runtime/`

Runtime state directory. Common contents:

- Current workspace configuration
- External process PIDs
- Runtime logs
- Temporary state files

## `projects/`

User workspace directory, storing download, subtitle, analysis, slicing, decryption, and export artifacts.

Recommended structure is documented in [WORKFLOW](../WORKFLOW.md).

## `services/` (Legacy)

The old `services/` directory is retained for backward compatibility. All current backend code resides under `backend/services/` and `backend/api/`.