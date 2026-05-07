# Patch System

> [中文版](./PATCH_SYSTEM.zh.md) · Chinese

MediaTools uses patch configuration to manage external tool and local environment differences. The patch system's goal is to let the project stay aligned with upstream tool updates while retaining necessary local rules.

## Configuration Loading Order

Patch rules are typically loaded in the following order:

1. `patches/tool_patches.json`
2. `runtime/tool_patches.json`
3. `projects/<current-workspace>/manifests/tool_patches.json`

Later-loaded rules can override earlier ones.

## Use Cases

- Specifying external tool executable locations
- Overriding default parameters for a specific tool
- Adapting to local installation paths
- Temporarily working around upstream tool behavior changes
- Using different tool versions or parameters for a specific workspace

## Global Rules

Located in:

```text
patches/tool_patches.json
```

Suitable for project-level defaults. Example files can be placed at:

```text
patches/tool_patches.example.json
```

## Runtime Rules

Located in:

```text
runtime/tool_patches.json
```

Suitable for machine-local temporary rules. This directory is typically not committed.

## Workspace Rules

Located in:

```text
projects/<current-workspace>/manifests/tool_patches.json
```

Suitable for workspace-specific tool preferences, such as locking FFmpeg parameters to a specific production's requirements.

## Maintenance Guidelines

- Machine-private secrets that can go in `.env` should not be written to patch files.
- Global patches should be kept minimal, containing only stable rules that apply across developers.
- Workspace patches should be named and documented according to their workspace context, to remain understandable months later.
- When changing the patch loading logic, tests and this document must be updated.

## Related Code

- `patches/tool_patches.py`
- `tests/test_tool_patches.py`
- `docs/EXTERNAL_TOOLS.md`

## Troubleshooting

If a tool behaves unexpectedly:

1. Check the current workspace first.
2. Review the workspace `manifests/tool_patches.json`.
3. Review `runtime/tool_patches.json`.
4. Review `patches/tool_patches.json`.
5. Confirm the final resolved tool path and parameters via the CLI or API status interface.
