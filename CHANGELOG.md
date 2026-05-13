# Changelog

> [中文版](./CHANGELOG.zh.md) · Chinese

All significant changes are documented here. For upstream tool changes, refer to each tool's CHANGELOG in `vendor/`.

## 2026-05-13

### Photoshop Algorithm Enhancement

- Ported PSA reference project's mature adaptive text-fitting algorithms into the PS module
- **Method A (Calibration):** New calibration step measures original text in lab document, computes scale factor (`real_h / lab_h`), and uses calibrated target height — eliminates systematic errors caused by font metric differences between lab and real PSD
- **Method B (Verify+Refine):** New post-apply verification measures real rendered height and iteratively refines font size (up to 5 rounds for faux-bold, 3 for normal) until converged within 2-6px tolerance
- **SO Boundary Protection:** Smart Object canvas automatically expanded after modification (1.2x–3.0x based on size ratio) to prevent text clipping
- Fixed hardcoded values in `text_modifier.py`: `dpi` now read from active document, `auto_leading` and `leading_pt` read from actual TextItem properties
- Added optional `font_index` parameter to `modify_text_layer()` to avoid rebuilding font index per layer
- Added `so_chain` field to `TicketScanRow` for multi-level smart object navigation
- New file `psa_applier.py` replaces empty `workorder_applier.py` with core processing functions
- Verified with 52-layer debug.psd: 100% convergence, 0 errors

## 2026-05-07

### BrowserApp UI and FontPicker

- Redesigned BrowserApp with browser type sidebar, address bar, and status panel
- Added FontPicker component for structured font selection in Photoshop/After Effects workflows
- Improved file manager disk drive tracking and selection logic
- Refined After Effects and Photoshop task card layouts and option styling
- Fixed startup scripts for proper browser opening and process detection
- Unified confirm button labels across dialogs

## 2026-05-06

### Documentation Reorganization

- Rewrote root `README.md`, removing broken badges, garbled text, and deprecated Gradio entry instructions.
- Rewrote `WORKFLOW.md` to clarify the recommended production pipeline: workspace setup, downloading, subtitle analysis, FFmpeg slicing, workbench review.
- Rewrote `ARCHITECTURE.md` to match the current FastAPI + React + services/modules structure.
- Rewrote `docs/README.md` to clearly separate owned documentation, specialized documents, and third-party documentation.
- Cleaned up and rewrote core technical documents:
  - `docs/API_OVERVIEW.md`
  - `docs/DIRECTORY_STRUCTURE.md`
  - `docs/MODULE_DEPENDENCIES.md`
  - `docs/NAMING_CONVENTIONS.md`
  - `docs/EXTERNAL_TOOLS.md`
  - `docs/FRONTEND_OVERVIEW.md`
  - `docs/VENDOR_ORGANIZATION.md`
  - `docs/PATCH_SYSTEM.md`
  - `docs/TASK_QUEUE.md`
  - `docs/TOOL_FACTIONS.md`
- Rewrote `docs/adobe/` Atom, AE, and COM/CEP topics, documenting current integration state and reference boundaries.

## 2026-04-24

### Security and Service Entry

- Default service binding adjusted to localhost.
- Added `API_SECRET_KEY` configuration for API protection when binding to non-localhost addresses.
- Enhanced input validation, error handling, and logging.

### Functional Modules

- Added `modules/generator` for video screenshots and image generation capabilities.
- Confirmed and organized Photoshop, auditor, and WeChat moments extension entry points.
- Extended media downloading, subtitle processing, analysis, and slicing pipelines.

### Testing

- Added test coverage in `tests/` for API, media services, workspace, transcoding, tool patches, and more.

### Ongoing Maintenance Directions

- Continue converging Web and CLI capability boundaries.
- Keep the FFmpeg pipeline stable; experimental CapCut/capcut-mate integration is maintained as an extended capability.
- Continue building out external tool status checks, task center integration, and automated testing.
