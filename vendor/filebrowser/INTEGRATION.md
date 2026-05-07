# filebrowser Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Workspace file browsing and local file service.

## Status

**Optional** - Enhances file management experience.

## Maintenance

- Source: `vendor/filebrowser/` (upstream)
- Runtime: `backend/services/runtime/filebrowser.py`
- API: `backend/api/routes/filebrowser.py`
- CLI wrapper: `modules/filebrowser/`

## Upstream

- Official: https://github.com/filebrowser/filebrowser
- Docs: `vendor/filebrowser/www/docs/`
- MediaTools only wraps the runtime; does not modify upstream code

## Usage in MediaTools

- Provides file browsing for workspaces
- Integration isolated in runtime service layer
- Configuration managed via `.env` and workspace settings
