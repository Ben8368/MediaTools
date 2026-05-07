# Module Dependencies

> [中文版](./MODULE_DEPENDENCIES.zh.md) · Chinese

This document describes the currently recommended dependency direction, used to determine where code should be placed during maintenance.

## Layering

```text
frontend
  -> backend/api/routes/
  -> backend/services/
  -> modules/
  -> adapters/core/vendor/bin
```

CLI path:

```text
cli/main.py
  -> modules/*/cli.py
  -> modules/* or backend/services/
```

Dependency principles:

- The frontend only calls APIs; it does not directly understand Python module structure.
- API routes handle request/response; they should not carry complex business logic.
- Cross-module workflows go in `backend/services/`.
- Single capabilities go in `modules/`.
- External tool details go in `adapters/`, `core/`, or `backend/services/runtime/`.

## Main Module Relationships

| Capability | Primary Service | Underlying Module / Tool |
|---|---|---|
| Downloading and subtitles | `backend/services/fetcher.py` | `modules/fetcher`, `yt-dlp` |
| Transcoding and slicing | `backend/services/encoder.py` | `modules/encoder`, `FFmpeg` |
| Download-analyze-slice | `backend/services/media/workflows.py` | `fetcher`, `encoder`, AI API |
| Decryption | `backend/services/decryptor.py` | `modules/decryptor`, `um-cli` |
| Workspace | `backend/services/workspace.py` | filesystem |
| Workbench | `backend/services/workbench.py` | `fetcher`, `encoder`, AI API |
| Asset scanning | API routes / assets services | `modules/assets` |
| AI Assistant | `backend/agent/` | media/workspace/assets services |
| Photoshop | `backend/services/photoshop.py` | `modules/adobe`, Adobe runtime |
| After Effects | `backend/api/routes/adobe.py` | `modules/adobe`, Adobe runtime |
| Auditing | `backend/services/auditor.py` | `modules/auditor`, `vendor/auditor` |
| filebrowser | `backend/services/runtime/filebrowser.py` | `modules/filebrowser`, `vendor/filebrowser` |
| Browser control | `backend/services/browser_manager.py` | CDP, system browser |

## Recommended Placement

### New API

1. Add routes in `backend/api/routes/` and register in `setup.py`.
2. Place request/response models in `backend/api/models.py` or the relevant domain module.
3. Push complex logic down to service functions.
4. Connect long-running tasks to `backend/services/task_center.py`.

### New Media Workflows

1. Single-step capabilities go in `modules/`.
2. Multi-step orchestration goes in `backend/services/media/workflows.py` or a similar service file.
3. Output paths must go through workspace and path validation utilities.
4. Web and AI assistant should reuse the same service function.

### New External Tools

1. Tool discovery, version checking, and command execution go in `backend/services/runtime/` or an adapter.
2. CLI wrappers go in `modules/<tool>/cli.py`.
3. Web routes should only expose status, start/stop, and task results.
4. Write relevant notes in `docs/EXTERNAL_TOOLS.md`.

## Dependencies to Avoid

- `frontend/` should not depend on Python file paths.
- `backend/api/routes/` should not concatenate complex shell commands.
- `modules/` should not depend on frontend concepts.
- Upstream code in `vendor/` should not reverse-depend on project services.
- External tool paths should not be scattered across multiple business files.

## Testing Boundaries

- Module-level logic: Write `tests/test_<module>.py`.
- API routes: Write `tests/test_api_*routes.py`.
- Long-running tasks and workspaces: Cover state, paths, security validation, and failure branches.
- External tools: Prefer mocking adapters/runtime to avoid testing that is strongly dependent on local software.
