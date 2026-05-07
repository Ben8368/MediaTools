# MediaTools

> **[中文](./README.zh.md)** | English

MediaTools is a web-based workstation for content creation and local media processing. It integrates video downloading, subtitle processing, AI analysis, FFmpeg transcoding, asset management, Adobe automation, and an executable AI assistant.

## Entry Points

| Entry | Command |
|---|---|
| Web server | `python app.py` |
| CLI | `python -m cli.main <module> ...` |
| Frontend dev | `cd frontend && npm run dev` |

## Capabilities

| Category | Features |
|---|---|
| **Media Acquisition** | Video downloading and subtitle extraction via `yt-dlp` |
| **Subtitle Processing** | VTT/SRT conversion, AI segment analysis |
| **FFmpeg Operations** | Transcoding, audio extraction, single/batch slicing |
| **Workspace Management** | Asset scanning, previewing, file browsing |
| **Decryption** | Music/media decryption via Unlock Music CLI |
| **Adobe Automation** | Photoshop, After Effects automation |
| **Auxiliary Tools** | Asset auditing, screenshot generation, WeChat moments images |
| **AI Assistant** | Task center, system status, log viewer, tool calling |
| **Experimental** | CapCut/capcut-mate integration |

## Quick Start

### Requirements

- Python 3.11+
- Node.js 20+ (frontend development only)
- Windows: prefer `.bat` launch scripts

### Setup

```powershell
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
Copy-Item .env.example .env
# Edit .env: set TEC_CHI_API_KEY, adjust port if needed
```

### Prepare External Tools

```powershell
python -m cli.main fetcher ytdlp download
```

FFmpeg/ffprobe should be in `bin/` or system `PATH`.

### Launch

```powershell
python app.py
```

Default URLs:
- Web workstation: `http://127.0.0.1:7860`
- API docs: `http://127.0.0.1:7860/docs`

Windows users can double-click `start_mediatools.bat` (normal) or `start_mediatools_dev.bat` (development).

## CLI Reference

```powershell
python -m cli.main --help
python -m cli.main fetcher download <url>
python -m cli.main encoder to-h265 input.mp4 --crf 28
python -m cli.main decryptor run -i song.ncm
python -m cli.main generator screenshot video.mp4 00:01:30 -o frame.jpg
```

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
| `generator` | Screenshot generation, WeChat moments images |

## API Overview

FastAPI routes available at `http://127.0.0.1:7860/docs`.

| Group | Path Prefix | File |
|---|---|---|
| System | `/api/system`, `/api/modules` | `backend/api/routes/system.py` |
| Media | `/api/media` | `backend/api/routes/media.py` |
| Workspace | `/api/workspace` | `backend/api/routes/workspace.py` |
| Workbench | `/api/workbench` | `backend/api/routes/workbench.py` |
| Assets | `/api/assets` | `backend/api/routes/assets.py` |
| Files | `/api/files` | `backend/api/routes/files.py` |
| filebrowser | `/api/filebrowser` | `backend/api/routes/filebrowser.py` |
| Task center | `/api/tasks` | `backend/api/routes/task_center.py` |
| Logs | `/api/logs` | `backend/api/routes/log.py` |
| Photoshop | `/api/photoshop` | `backend/api/routes/photoshop.py` |
| Adobe/AE | `/api/adobe` | `backend/api/routes/adobe.py` |
| Auditor | `/api/auditor` | `backend/api/routes/auditor.py` |
| WeChat Moments | `/api/wechat_moments` | `backend/api/routes/wechat.py` |
| Browser control | `/api/browser` | `backend/api/routes/browser.py` |
| AI Assistant | `/api/agent/*` | `backend/agent/routes.py` |

Set `API_SECRET_KEY` when binding to non-localhost addresses.

## Project Structure

```
MediaTools/
├── app.py              # Web service entry
├── cli/                # CLI entry point
├── backend/            # Backend (API, services, agent, config)
│   ├── api/routes/     # API route files
│   ├── services/       # Business services
│   ├── agent/          # AI agent
│   └── config/         # Configuration
├── frontend/           # React + TypeScript + Vite
├── modules/            # CLI-callable modules
├── adapters/           # External tool adapters
├── core/               # General utilities
├── patches/            # Tool patch rules
├── vendor/             # Third-party source/embedded tools
├── docs/               # Project documentation
├── tests/              # Python tests
├── bin/                # Local binaries (not committed)
├── runtime/            # Runtime state (not committed)
└── projects/           # Workspace data (not committed)
```

## Documentation

- [Workflow](./WORKFLOW.md) | [中文](./WORKFLOW.zh.md)
- [Architecture](./ARCHITECTURE.md) | [中文](./ARCHITECTURE.zh.md)
- [Dependencies & Naming](./docs/DEPENDENCIES.md) | [中文](./docs/DEPENDENCIES.zh.md)
- [External Tools](./docs/TOOLS.md) | [中文](./docs/TOOLS.zh.md)

> `vendor/` contains third-party source code and embedded tools. Each tool has an `INTEGRATION.md` / `INTEGRATION.zh.md` documenting its role in MediaTools.

## Development

```powershell
python -m pytest
```

Frontend:

```powershell
cd frontend
npm run typecheck && npm test && npm run build
```

## Known Limitations

- `capcut-mate`, Adobe automation, and auditing depend on local software and environment
- AI analysis quality depends on subtitle quality and model configuration
- `vendor/` contains third-party documentation, not MediaTools documentation

## License

MIT License
