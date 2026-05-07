# MediaTools

MediaTools is a web-based workstation for content creation and local media processing. It integrates video downloading, subtitle processing, AI analysis, FFmpeg transcoding/slicing, music decryption, asset management, file management, Adobe automation, and an executable AI assistant into a single project.

The main entry points are:

- Web server: `python app.py`
- Web frontend: Built version served directly by the backend; run independently under `frontend` during development
- CLI: `python main.py <module> ...`

## Current Capabilities

- Video probing, downloading, and subtitle extraction powered by `yt-dlp`
- Subtitle cleaning, VTT/SRT conversion, and AI segment analysis
- FFmpeg transcoding, audio extraction, single-segment slicing, and batch slicing
- Workspace management, asset scanning, asset previewing, and file browsing
- Music/media decryption via Unlock Music CLI
- Photoshop, After Effects, and other Adobe automation adapters
- Asset auditing, screenshot generation, WeChat moments image generation, and other auxiliary tools
- Task center, system status, log viewer, and AI assistant tool calling
- Experimental CapCut/capcut-mate integration

## Quick Start

### Requirements

- Python 3.11+
- Node.js 20+ (only needed for frontend development)
- Go 1.21+ (only needed to build `um-cli`)
- Windows: prefer the `.bat` launch scripts in the repository

### Install Dependencies

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Frontend development dependencies:

```powershell
cd frontend
npm install
```

### Configure Environment Variables

Copy `.env.example` to `.env` and customize as needed:

```powershell
Copy-Item .env.example .env
```

Common settings:

- `TEC_CHI_API_KEY`: API key for AI analysis and the AI assistant
- `OPENAI_BASE_URL`: OpenAI-compatible API base URL
- `ANALYSIS_MODEL`: default model for subtitle analysis/assistant
- `GUI_SERVER_NAME`, `GUI_SERVER_PORT`: backend listen address and port
- `API_SECRET_KEY`: recommended when binding to a non-localhost address
- `WORKSPACE_ALLOWED_ROOTS`: allowed workspace root directories

### Prepare External Tools

```powershell
python main.py fetcher ytdlp download
python main.py fetcher ytdlp status
```

FFmpeg/ffprobe should be placed in `bin/` or available in the system `PATH`. Unlock Music CLI can be placed in `bin/` via project scripts or manually.

### Launch

```powershell
python app.py
```

Default URLs:

- Web workstation: `http://127.0.0.1:7860`
- API docs: `http://127.0.0.1:7860/docs`

On Windows you can also double-click:

- `start_mediatools.bat`: normal launch
- `start_mediatools_dev.bat`: development launch

Backend hot-reload:

```powershell
python app.py --reload
```

Frontend development:

```powershell
cd frontend
npm run dev
```

## CLI Usage

```powershell
python main.py --help
python main.py fetcher --help
python main.py encoder --help
python main.py workbench --help
```

Canonical module names:

| Module | Purpose |
|---|---|
| `fetcher` | Media downloading, subtitle fetching, yt-dlp management |
| `encoder` | Transcoding, audio extraction, slicing |
| `decryptor` | Music/media decryption |
| `assets` | Asset scanning, searching, statistics |
| `workbench` | Subtitle analysis and segment export |
| `editor` | Experimental CapCut/capcut-mate adapter |
| `photoshop` | Photoshop automation |
| `auditor` | Asset auditing workflow |
| `generator` | Screenshot generation, WeChat moments images, and other generators |

Legacy aliases are still supported:

- `fetch` -> `fetcher`
- `encode` -> `encoder`
- `decrypt` -> `decryptor`
- `edit` -> `editor`

Examples:

```powershell
python main.py fetcher ytdlp status
python main.py fetcher download https://youtube.com/watch?v=xxxx --video --subtitles original_only
python main.py encoder to-h265 input.mp4 --crf 28
python main.py encoder slice input.mp4 --start 00:00:10 --end 00:00:25
python main.py decryptor run -i song.ncm
python main.py generator screenshot video.mp4 00:01:30 -o frame.jpg
```

## Recommended Workflow

1. Set the current project workspace in the web workstation.
2. Download videos and analyzable subtitles.
3. Use the AI assistant or workbench to analyze subtitles for highlight segments.
4. Auto-generate segment suggestions and export clips with FFmpeg.
5. Review and fine-tune results in the workbench; re-export if needed.
6. View final artifacts in asset management or file management.

The most stable production pipeline is `yt-dlp + subtitle analysis + FFmpeg slicing`. `capcut-mate` and some Adobe integrations are available but still require per-environment verification.

## Project Structure

```text
MediaTools/
├── app.py                    # Web service entry, starts backend/api/server.py
├── main.py                   # Unified CLI entry (proxies cli/main.py)
├── config.py                 # Environment and path configuration (proxies backend/config)
├── cli/                      # New CLI entry point
├── backend/                  # Backend code (API, services, agent, config)
├── frontend/                 # React + TypeScript + Vite frontend
├── modules/                  # CLI-callable functional modules
├── adapters/                 # External tool / runtime adapters
├── core/                     # General-purpose utilities
├── patches/                  # External tool patch rules
├── scripts/                  # Development and maintenance scripts
├── tests/                    # Python tests
├── vendor/                   # Third-party source or embedded tools
├── bin/                      # Local binaries, typically not committed
├── runtime/                  # Runtime state, typically not committed
└── projects/                 # Workspace data, typically not committed
```

## Documentation

- [Workflow](./WORKFLOW.md) | [中文](./WORKFLOW.zh.md)
- [Architecture](./ARCHITECTURE.md) | [中文](./ARCHITECTURE.zh.md)
- [Documentation Index](./docs/README.md)
- [API Overview](./docs/API_OVERVIEW.md) | [中文](./docs/API_OVERVIEW.zh.md)
- [Frontend Overview](./docs/FRONTEND_OVERVIEW.md) | [中文](./docs/FRONTEND_OVERVIEW.zh.md)
- [Directory Structure](./docs/DIRECTORY_STRUCTURE.md) | [中文](./docs/DIRECTORY_STRUCTURE.zh.md)
- [External Tools](./docs/EXTERNAL_TOOLS.md) | [中文](./docs/EXTERNAL_TOOLS.zh.md)
- [Task Center](./docs/TASK_QUEUE.md) | [中文](./docs/TASK_QUEUE.zh.md)
- [Patch System](./docs/PATCH_SYSTEM.md) | [中文](./docs/PATCH_SYSTEM.zh.md)
- [Vendor Organization](./docs/VENDOR_ORGANIZATION.md) | [中文](./docs/VENDOR_ORGANIZATION.zh.md)

> Chinese versions of all documents are available in `.zh.md` files (e.g., `README.zh.md`, `docs/API_OVERVIEW.zh.md`). The English docs are the primary source of truth.

## Development

```powershell
python -m pytest
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm test
npm run build
```

Code formatting and linting follow `pyproject.toml`, `.pre-commit-config.yaml`, and the frontend configuration.

## Known Limitations

- Some historical documents are design materials and may not reflect the current implementation. Always prioritize the root README, `WORKFLOW.md`, `ARCHITECTURE.md`, and `docs/README.md`.
- `capcut-mate`, Adobe automation, and asset auditing depend on local software, ports, plugins, and external tool versions.
- AI subtitle analysis quality depends on subtitle quality, model configuration, and API availability.
- `vendor/` contains third-party project documentation and is not part of the MediaTools own documentation.

## License

MIT License
