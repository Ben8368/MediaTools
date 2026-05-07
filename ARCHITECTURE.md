# MediaTools Architecture

> [中文版](./ARCHITECTURE.zh.md)

## Overview

```
Entry Layer
├── app.py              # Web service (FastAPI + Uvicorn)
├── cli/main.py         # CLI dispatcher
└── backend/agent/      # AI agent

Backend Layer
├── backend/api/routes/ # API routes (request/response only)
├── backend/services/   # Business logic and workflows
├── backend/config/     # Configuration
└── modules/            # CLI-callable capability modules

Infrastructure
├── adapters/           # External tool adapters
├── core/               # Utilities (auth, logging, ffmpeg)
└── patches/            # Tool patch rules

Frontend
└── frontend/           # React + TypeScript + Vite
```

## Design Principles

1. **Routes handle requests only** - no complex business logic
2. **Services orchestrate workflows** - cross-module logic in `backend/services/`
3. **Modules are independently callable** - CLI, API, and agent reuse the same modules
4. **Adapter isolates external tools** - platform differences contained in `adapters/`
5. **Frontend communicates via HTTP API only**

## Backend Structure

```
backend/
├── api/
│   ├── server.py       # FastAPI app
│   ├── setup.py        # Route registration
│   ├── models.py       # Pydantic models
│   └── routes/         # Route files by domain
├── services/
│   ├── media/          # Media workflows (fetch, encode, decrypt)
│   ├── runtime/        # External tool runtimes
│   ├── workspace.py    # Workspace management
│   ├── workbench.py    # Workbench service
│   └── task_center.py  # Long-running tasks
├── agent/
│   ├── service.py      # Agent service
│   ├── tools.py        # Agent tools
│   ├── tool_specs.py   # Tool definitions
│   └── routes.py       # Agent API routes
└── config/
    └── settings.py     # Global configuration
```

## Frontend Structure

```
frontend/src/
├── apps/               # Desktop-style application windows
│   ├── DownloaderApp.tsx
│   ├── WorkbenchApp.tsx
│   ├── FileManagerApp.tsx
│   ├── BrowserApp.tsx
│   ├── AIAssistantApp.tsx
│   ├── PhotoshopApp.tsx
│   ├── AEApp.tsx
│   └── AuditorApp.tsx
├── api.ts              # API calls
├── store.ts            # Global state (Zustand)
└── windowStore.ts      # Window state
```

## Main Data Flows

### Download → Analyze → Slice

```
Frontend / CLI / Agent
→ backend/api/routes/media.py
→ backend/services/media/workflows.py
→ modules/fetcher → modules/encoder
→ projects/<workspace>/clips
```

### AI Assistant

```
Frontend AI Assistant
→ backend/agent/routes.py
→ backend/agent/service.py
→ backend/services/* → modules/*
```

## Configuration

In `backend/config/settings.py`, override via `.env`:

```
TEC_CHI_API_KEY=your_api_key
GUI_SERVER_PORT=7860
WORKSPACE_ALLOWED_ROOTS=/path/to/projects
```

## Compatibility

- `config.py` → proxies `backend.config`
- `main.py` → proxies `cli.main`
- These show DeprecationWarning; new code should use new paths

## Development Guidelines

1. New business logic → `backend/services/`
2. Reusable capabilities → `modules/` (CLI-testable)
3. External tool differences → `adapters/` or `backend/services/runtime/`
4. Long-running tasks → integrate with `task_center`
5. File paths → always validate against allowed roots

## Testing

```powershell
python -m pytest
cd frontend && npm run typecheck && npm test
```

## Boundaries

- Web service is the most complete entry; CLI for batch/auxiliary tasks
- Asset management is a workspace indexer, not a full database
- CapCut, Adobe, and auditing depend on local environment
- `vendor/` is third-party code, not project business layer
