# Tool Routes and Integration Status

> [中文版](./TOOL_FACTIONS.zh.md) · Chinese

This document explains the positioning of several external tool routes within MediaTools. It is not a product roadmap commitment; it is used to determine which pipeline should be prioritized.

## Overview

| Route | Current Positioning | Stability | Primary Entry |
|---|---|---|---|
| FFmpeg + yt-dlp | Core production mainline | High | `fetcher`, `encoder`, `workbench` |
| AI subtitle analysis | Core enhancement capability | Medium-high, depends on model and subtitles | `backend/agent/`, `modules/fetcher/analyzer.py` |
| Adobe / Photoshop / After Effects | Professional software automation extension | Environment-dependent | `modules/adobe`, `backend/api/routes/adobe.py`, `backend/api/routes/photoshop.py` |
| capcut-mate / CapCut | Experimental editing integration | Medium-low | `modules/editor`, runtime service |
| auditor | Asset auditing extension | Environment-dependent | `modules/auditor`, `backend/services/auditor.py` |
| filebrowser | File management extension | Medium | `modules/filebrowser`, `backend/services/runtime/filebrowser.py` |

## Recommended Mainline

The pipeline that can be stably relied on day-to-day:

```text
yt-dlp downloading
-> Subtitle cleaning / analysis
-> FFmpeg slicing or transcoding
-> Workbench review
-> Workspace asset management
```

Advantages:

- Does not depend on large desktop applications
- Easy to test and troubleshoot
- Reused by both CLI and Web
- Failures are typically reproducible via logs and command-line

## Adobe Route

Suitable for:

- Photoshop batch processing
- After Effects project scanning, ticketized modifications, and execution
- Professional workflows where Adobe software is already installed and configured

Characteristics:

- Powerful but heavily depends on local software, permissions, plugins, and versions.
- COM/ExtendScript/CEP details should be isolated in Adobe modules and runtime services.
- Related specialized docs are in `docs/adobe/`.

Current primary code:

- `modules/adobe/`
- `modules/photoshop/`
- `backend/api/routes/adobe.py`
- `backend/api/routes/photoshop.py`
- `backend/services/photoshop.py`
- `backend/services/photoshop_state.py`

## CapCut / capcut-mate Route

Suitable for:

- Quick editing experiments
- Exploring CapCut / JianYing automation
- Auxiliary export paths outside the core production pipeline

Current limitations:

- Upstream interfaces and local environment change frequently.
- Automation stability is not as reliable as the FFmpeg mainline.
- Should not be the sole export path.

Current primary code:

- `modules/editor/`
- `vendor/capcut-mate/`

## Selection Guide

- Need downloading, analysis, and slicing only: Choose FFmpeg + yt-dlp.
- Need professional image or AE project processing: Choose the Adobe route.
- Need to explore CapCut integration: Use capcut-mate, but keep FFmpeg as a fallback.
- Need to audit material compliance or quality: Use the auditor.
- Need to browse, preview, and organize workspace files: Use built-in file management and filebrowser.

## Documentation Boundary

- Current implementation status is governed by `ARCHITECTURE.md` and the code.
- Third-party intrinsic capabilities are documented in `vendor/` upstream docs.
- This document only describes MediaTools' integration positioning of these tools.
