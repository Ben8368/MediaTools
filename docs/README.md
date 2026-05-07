# MediaTools Documentation Index

> [中文版](./README.zh.md) · English (this page)

Recommended reading order:

1. [Root README](../README.md): Purpose, installation, launching, and commands
2. [WORKFLOW](../WORKFLOW.md): Currently recommended workflows
3. [ARCHITECTURE](../ARCHITECTURE.md): Current code structure and maintenance boundaries
4. This document: Specialized document index and document status

## Current Maintained Documentation

These documents should be kept in sync with the current implementation; update these first when making changes:

| Document | Content |
|---|---|
| [API_OVERVIEW](./API_OVERVIEW.md) | FastAPI route groups and maintenance boundaries |
| [DIRECTORY_STRUCTURE](./DIRECTORY_STRUCTURE.md) | Directory structure and responsibility boundaries |
| [FRONTEND_OVERVIEW](./FRONTEND_OVERVIEW.md) | React frontend application structure |
| [MODULE_DEPENDENCIES](./MODULE_DEPENDENCIES.md) | Module layering and dependency relationships |
| [NAMING_CONVENTIONS](./NAMING_CONVENTIONS.md) | Naming conventions |
| [EXTERNAL_TOOLS](./EXTERNAL_TOOLS.md) | yt-dlp, FFmpeg, um-cli, and other external tools |
| [VENDOR_ORGANIZATION](./VENDOR_ORGANIZATION.md) | `vendor/` directory organization |
| [PATCH_SYSTEM](./PATCH_SYSTEM.md) | External tool patch system |
| [TASK_QUEUE](./TASK_QUEUE.md) | Built-in task center and long-running task mechanism |

## Design and Specialized Documents

These documents record design background, comparison analysis, or phase proposals. Cross-reference with current code to verify implementation status:

| Document | Status |
|---|---|
| [TOOL_FACTIONS](./TOOL_FACTIONS.md) | Adobe/剪映 and other tool route comparison materials |

## Adobe Topics

| Document | Content |
|---|---|
| [adobe/ATOM_INTEGRATION.zh](./adobe/ATOM_INTEGRATION.zh.md) | Atom plugin integration (Chinese only) |
| [adobe/ae_capability_comparison.zh](./adobe/ae_capability_comparison.zh.md) | After Effects capability comparison (Chinese only) |
| [adobe/com_vs_cep_technical_proof.zh](./adobe/com_vs_cep_technical_proof.zh.md) | COM vs CEP technical feasibility (Chinese only) |
| [adobe/atom_plugin_capabilities.zh](./adobe/atom_plugin_capabilities.zh.md) | Atom plugin capabilities (Chinese only) |

## Third-Party Documentation

Additional README, CHANGELOG, LICENSE, and upstream documentation exist under `vendor/`. These belong to third-party projects and are not included in the MediaTools document index. Check the corresponding directory when investigating an external tool.

Common third-party directories:

- `vendor/yt-dlp/`
- `vendor/filebrowser/`
- `vendor/capcut-mate/`
- `vendor/adobe/`
- `vendor/auditor/`

## Chinese Versions

All documents above have corresponding Chinese versions (`.zh.md` suffix). The English docs are the primary ones; if there is a discrepancy, the English document is authoritative.

| Chinese | English |
|---|---|
| [README.zh.md](../README.zh.md) | README.md |
| [WORKFLOW.zh.md](../WORKFLOW.zh.md) | WORKFLOW.md |
| [ARCHITECTURE.zh.md](../ARCHITECTURE.zh.md) | ARCHITECTURE.md |
| [CHANGELOG.zh.md](../CHANGELOG.zh.md) | CHANGELOG.md |
| [docs/API_OVERVIEW.zh.md](./API_OVERVIEW.zh.md) | API_OVERVIEW.md |
| [docs/FRONTEND_OVERVIEW.zh.md](./FRONTEND_OVERVIEW.zh.md) | FRONTEND_OVERVIEW.md |
| [docs/DIRECTORY_STRUCTURE.zh.md](./DIRECTORY_STRUCTURE.zh.md) | DIRECTORY_STRUCTURE.md |
| [docs/EXTERNAL_TOOLS.zh.md](./EXTERNAL_TOOLS.zh.md) | EXTERNAL_TOOLS.md |
| [docs/TASK_QUEUE.zh.md](./TASK_QUEUE.zh.md) | TASK_QUEUE.md |
| [docs/MODULE_DEPENDENCIES.zh.md](./MODULE_DEPENDENCIES.zh.md) | MODULE_DEPENDENCIES.md |
| [docs/NAMING_CONVENTIONS.zh.md](./NAMING_CONVENTIONS.zh.md) | NAMING_CONVENTIONS.md |
| [docs/VENDOR_ORGANIZATION.zh.md](./VENDOR_ORGANIZATION.zh.md) | VENDOR_ORGANIZATION.md |
| [docs/PATCH_SYSTEM.zh.md](./PATCH_SYSTEM.zh.md) | PATCH_SYSTEM.md |
| [docs/TOOL_FACTIONS.zh.md](./TOOL_FACTIONS.zh.md) | TOOL_FACTIONS.md |

## Documentation Maintenance Rules

- Quick user-facing instructions go in the root README.
- Operational procedures go in `WORKFLOW.md`.
- Code structure, boundaries, and data flows go in `ARCHITECTURE.md`.
- Specialized proposals go in `docs/` with status annotations.
- Third-party reference materials stay in `vendor/`; do not mix into the project's main documentation.
- If implementation conflicts with documentation, fix the documentation entry first, then decide whether to archive the old specialized document.
