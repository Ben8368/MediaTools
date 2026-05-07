# capcut-mate Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Experimental CapCut (剪映) automation integration.

## Status

**Experimental** - Not recommended as sole production export path.

## Maintenance

- Source: `vendor/capcut-mate/` (upstream)
- Adapter: `modules/editor/`
- Runtime: `backend/services/runtime/editor.py`
- Config: `CAPCUT_MATE_BASE_URL=http://localhost:30000`

## Upstream

- Project: `vendor/capcut-mate/`
- Interfaces and local environment change frequently
- Automation stability less reliable than FFmpeg pipeline

## Usage in MediaTools

- Provides alternative export path to CapCut
- Prefer FFmpeg for stable, reproducible exports
- Verify local environment before use
