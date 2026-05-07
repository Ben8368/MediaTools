# Adobe Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Photoshop and After Effects automation for professional workflows.

## Status

**Environment-dependent** - Requires local Adobe software installation.

## Maintenance

- Source: `vendor/adobe/` (bridging materials)
- Photoshop: `modules/adobe/`, `backend/api/routes/photoshop.py`, `backend/services/photoshop.py`
- After Effects: `modules/adobe/`, `backend/api/routes/adobe.py`
- Frontend: `frontend/src/apps/PhotoshopApp.tsx`, `frontend/src/apps/AEApp.tsx`

## Upstream

- Adobe COM/CEP/ExtendScript integration
- Depends on local software, permissions, and plugins
- Heavily environment-specific

## Usage in MediaTools

| Feature | Entry Point |
|---|---|
| Photoshop automation | `backend/services/photoshop.py` |
| After Effects | `backend/api/routes/adobe.py` |
| State management | `backend/services/photoshop_state.py` |

## Notes

- Verify software installed and automation allowed
- Check ports and permissions
- COM/ExtendScript/CEP details isolated in Adobe modules
