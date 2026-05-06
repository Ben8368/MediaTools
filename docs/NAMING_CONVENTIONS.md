# MediaTools Naming Conventions

This file defines the naming rules for MediaTools so new modules can be merged
without introducing mixed case, ambiguous aliases, or upstream names into the
main project surface.

## 1. Core rule

MediaTools uses two distinct naming domains:

1. Internal product names
2. Upstream vendor names

These two domains must not be mixed.

## 2. Internal product naming

Use internal names for all first-party project surfaces:

- module ids
- API routes
- Python service files
- adapter filenames
- frontend app ids
- workspace manifests

Rules:

- Use lowercase words for module ids: `fetcher`, `encoder`, `photoshop`
- Use `snake_case` for Python files when more than one word is needed:
  `editor_runtime.py`, `photoshop_runtime.py`
- Use lowercase route segments:
  `/api/photoshop/...`
- Use PascalCase only for Vue component filenames:
  `PhotoshopApp.vue`
- Use human-readable titles only in UI labels:
  `Photoshop 自动化`

## 3. Vendor naming

Third-party or upstream source bundles live under `vendor/`.

Rules:

- Vendor directory names use lowercase canonical slugs
- Preserve upstream identity in documentation, not in first-party module ids
- Version numbers should not appear in top-level project paths

Current vendor examples:

- `vendor/photoshop_auto`
- `vendor/capcut-mate`
- `vendor/unlock-music`
- `vendor/atom`
- `vendor/wechat_moments_source`
- `vendor/auditor_source`

## 4. Recommended naming by layer

### Modules

- Directory: `modules/photoshop`
- Public id: `photoshop`
- Do not use: `PhotoshopAuto`, `PhotoshopAuto-v2.0.1`

### Services

- File: `services/photoshop.py`
- File: `services/workspace.py`
- Prefer module-aligned facades when exposing shared module behavior:
  - `services/fetcher.py`
  - `services/encoder.py`
  - `services/decryptor.py`
- Legacy aggregator names should be treated as transitional and documented

### Adapters

- File: `adapters/photoshop_runtime.py`
- File: `adapters/external_tools.py`
- Adapter names should describe the capability boundary, not just the source repo

### Frontend

- App id: `photoshop`
- Component: `PhotoshopApp.vue`
- Registry title: `Photoshop 自动化`

### Launchers

- Canonical launcher script: `start_mediatools.bat`
- Do not add parallel launcher aliases unless they provide genuinely different behavior

### Executables in `bin/`

- Keep upstream executable names as-is:
  - `yt-dlp.exe`
  - `ffmpeg.exe`
  - `ffprobe.exe`
  - `um-cli.exe`
- Do not rename upstream binaries to internal module ids

## 5. Transitional exceptions

The following names still exist for backward-compatibility or legacy reasons and
should not be used as naming templates for new code:

- `services/media.py`
- `services/fetch.py`
- `modules/editor`
- `vendor/capcut-mate`
- `vendor/unlock-music`

These are tolerated for compatibility, but new modules should follow the rules
above.

## 6. Practical checklist for new modules

Before merging a new capability, verify:

1. The module id is lowercase and stable
2. The module directory matches the module id
3. The service filename uses lowercase or `snake_case`
4. The adapter filename describes runtime or integration responsibility
5. The vendor source lives under `vendor/`
6. Upstream names do not leak into API route names or frontend app ids

## 7. Current normalized examples

- Photoshop module:
  - internal id: `photoshop`
  - vendor source: `vendor/photoshop_auto`
  - adapter: `adapters/photoshop_runtime.py`

- WeChat moments module:
  - internal id: `wechat_moments`
  - vendor source: `vendor/wechat_moments_source`
  - adapter: `adapters/wechat_moments_runtime.py`

- Auditor module:
  - internal id: `auditor`
  - vendor source: `vendor/auditor_source`
  - adapter: `adapters/auditor_runtime.py`

- Atom bundle:
  - internal future integration id should be something like `aftereffects`
  - vendor source: `vendor/atom`
  - do not expose `Atom` as a first-party module id unless product naming is
    intentionally decided that way
