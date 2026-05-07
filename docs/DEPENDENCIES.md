# Dependencies and Naming Conventions

> [中文版](./DEPENDENCIES.zh.md)

Rules for code placement and naming across CLI, API, services, and frontend.

## Dependency Direction

```
frontend
  → HTTP API only
  → No Python file dependencies

cli/main.py
  → modules/*/cli.py
  → modules/* or backend/services/
```

## Placement Rules

| Code Type | Location |
|---|---|
| New API routes | `backend/api/routes/<domain>.py` |
| Business workflows | `backend/services/` |
| Reusable capabilities | `modules/` (CLI-testable) |
| External tool details | `adapters/`, `core/`, or `backend/services/runtime/` |
| Request/response models | `backend/api/models.py` |
| Long-running tasks | Integrate with `backend/services/task_center.py` |

## Module Reference

| Capability | Service | Underlying Module |
|---|---|---|
| Download/subtitles | `backend/services/fetcher.py` | `modules/fetcher`, `yt-dlp` |
| Transcode/slice | `backend/services/encoder.py` | `modules/encoder`, `FFmpeg` |
| Workflow (download→slice) | `backend/services/media/workflows.py` | `fetcher`, `encoder`, AI |
| Decryption | `backend/services/decryptor.py` | `modules/decryptor`, `um-cli` |
| Workspace | `backend/services/workspace.py` | filesystem |
| AI Assistant | `backend/agent/` | media/workspace services |

## Avoid These

- Frontend depending on Python file paths
- Routes concatenating complex shell commands
- Modules depending on frontend concepts
- `vendor/` code reverse-depending on project services
- External tool paths scattered across business files

## Naming

| Context | Convention |
|---|---|
| Python files | `snake_case.py` |
| Python functions | `snake_case` |
| Python classes | `PascalCase` |
| Constants | `UPPER_SNAKE_CASE` |
| React components | `PascalCase.tsx` |
| React hooks | `useSomething.ts` |
| App windows | `<Name>App.tsx` |
| Workspace dirs | lowercase plural (`downloads/`, `clips/`) |
| CLI modules | `fetcher`, `encoder`, `decryptor`, `assets`, `workbench`, `editor`, `photoshop`, `auditor`, `generator` |

## Testing

| Scope | Location |
|---|---|
| Module logic | `tests/test_<module>.py` |
| API routes | `tests/test_api_*routes.py` |
| External tools | Mock adapters/runtime |
