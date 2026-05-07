# auditor Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Asset auditing workflow for material compliance and quality checks.

## Status

**Environment-dependent** - Requires local software setup.

## Maintenance

- Source: `vendor/auditor/` (upstream)
- Service: `backend/services/auditor.py`
- API: `backend/api/routes/auditor.py`
- CLI wrapper: `modules/auditor/`
- Frontend: `frontend/src/apps/AuditorApp.tsx`

## Upstream

- Project: `vendor/auditor/`
- Depends on local configuration
- Original docs: `vendor/auditor/src/README.md`

## Usage in MediaTools

- Provides material compliance checking
- Integration through service layer and API routes
- Verify local environment before use
