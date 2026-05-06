"""Patch registry and JSON loader for external tool adapters."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from config import BASE_DIR

CommandPatch = Callable[[list[str], dict], list[str]]

_MANUAL_COMMAND_PATCHES: dict[str, list[CommandPatch]] = defaultdict(list)
_FILE_COMMAND_PATCHES: dict[str, list[CommandPatch]] = defaultdict(list)
_LOADED_PATCH_FILES: list[str] = []
_LOAD_ERRORS: dict[str, str] = {}
_DEFAULT_LOAD_SIGNATURE: tuple[tuple[str, int, int, int], ...] | None = None
_EXTRA_PATCH_PATHS: list[Path] = []


def register_command_patch(tool_name: str, patch: CommandPatch) -> None:
    """Register a command patch for an external tool adapter."""
    _MANUAL_COMMAND_PATCHES[tool_name].append(patch)


def _normalize_args(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item)]
    text = str(value).strip()
    return [text] if text else []


def _normalize_values(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _context_matches(match: dict[str, Any], command: list[str], context: dict[str, Any]) -> bool:
    if not match:
        return True

    for key, expected in match.items():
        if key == "command_contains":
            tokens = [str(item) for item in _normalize_values(expected)]
            if not all(token in command for token in tokens):
                return False
            continue
        if key == "url_contains":
            url = str(context.get("url", ""))
            snippets = [str(item) for item in _normalize_values(expected)]
            if not any(snippet in url for snippet in snippets):
                return False
            continue
        actual = context.get(key)
        candidates = _normalize_values(expected)
        if not any(actual == candidate for candidate in candidates):
            return False
    return True


def _insert_args(command: list[str], target: str, values: list[str], *, after: bool) -> list[str]:
    if not values:
        return list(command)

    current = list(command)
    try:
        index = current.index(target)
    except ValueError:
        if current:
            return [current[0], *values, *current[1:]]
        return list(values)

    insert_at = index + 1 if after else index
    return current[:insert_at] + values + current[insert_at:]


def _patch_from_spec(spec: dict[str, Any]) -> CommandPatch:
    match = dict(spec.get("match") or {})
    prepend_args = _normalize_args(spec.get("prepend_args"))
    append_args = _normalize_args(spec.get("append_args"))
    remove_args = set(_normalize_args(spec.get("remove_args")))
    replace_binary = spec.get("replace_binary")
    insert_before = spec.get("insert_before")
    insert_after = spec.get("insert_after")

    def patch(command: list[str], context: dict) -> list[str]:
        if spec.get("enabled", True) is False:
            return list(command)
        if not _context_matches(match, command, context):
            return list(command)

        current = list(command)
        if replace_binary and current:
            current[0] = str(replace_binary)
        if remove_args:
            current = [arg for arg in current if arg not in remove_args]
        if prepend_args and current:
            current = [current[0], *prepend_args, *current[1:]]
        if isinstance(insert_before, dict):
            current = _insert_args(
                current,
                str(insert_before.get("arg", "")),
                _normalize_args(insert_before.get("args")),
                after=False,
            )
        if isinstance(insert_after, dict):
            current = _insert_args(
                current,
                str(insert_after.get("arg", "")),
                _normalize_args(insert_after.get("args")),
                after=True,
            )
        current.extend(append_args)
        return current

    return patch


def register_command_patch_spec(tool_name: str, spec: dict[str, Any], *, source: str = "manual") -> None:
    """Register a declarative patch spec from code or a JSON file."""
    patch = _patch_from_spec(dict(spec))
    if source == "file":
        _FILE_COMMAND_PATCHES[tool_name].append(patch)
    else:
        _MANUAL_COMMAND_PATCHES[tool_name].append(patch)


def _workspace_root() -> Path:
    workspace_file = BASE_DIR / "runtime" / "workspace.json"
    default_root = BASE_DIR / "projects" / "default"
    if not workspace_file.exists():
        return default_root
    try:
        payload = json.loads(workspace_file.read_text(encoding="utf-8"))
        root = payload.get("project_root")
        return Path(root).resolve() if root else default_root
    except Exception:
        return default_root


def get_default_patch_config_paths() -> list[Path]:
    workspace_root = _workspace_root()
    paths = [
        BASE_DIR / "patches" / "tool_patches.json",
        BASE_DIR / "runtime" / "tool_patches.json",
        workspace_root / "manifests" / "tool_patches.json",
    ]
    for path in _EXTRA_PATCH_PATHS:
        if path not in paths:
            paths.append(path)
    return paths


def _load_patch_specs(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Patch config must be a JSON object.")

    tools = payload.get("tools", {})
    if not isinstance(tools, dict):
        raise ValueError("Patch config 'tools' must be an object.")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for tool_name, specs in tools.items():
        if isinstance(specs, dict):
            specs = [specs]
        if not isinstance(specs, list):
            raise ValueError(f"Patch specs for '{tool_name}' must be a list or object.")
        normalized[tool_name] = [dict(spec) for spec in specs if isinstance(spec, dict)]
    return normalized


def _load_command_patch_file(path: str | Path) -> None:
    """Load declarative patches from a JSON config file into the active registry."""
    file_path = Path(path)
    specs_by_tool = _load_patch_specs(file_path)
    for tool_name, specs in specs_by_tool.items():
        for spec in specs:
            register_command_patch_spec(tool_name, spec, source="file")
    _LOADED_PATCH_FILES.append(str(file_path.resolve()))


def load_command_patch_file(path: str | Path) -> None:
    """Load declarative patches from a JSON file and keep it in the active config set."""
    file_path = Path(path).resolve()
    if file_path not in _EXTRA_PATCH_PATHS:
        _EXTRA_PATCH_PATHS.append(file_path)
    ensure_default_patch_configs_loaded(force=True)


def _current_load_signature(paths: list[Path]) -> tuple[tuple[str, int, int, int], ...]:
    signature: list[tuple[str, int, int, int]] = []
    for path in paths:
        try:
            stat = path.stat()
            signature.append((str(path.resolve()), 1, stat.st_mtime_ns, stat.st_size))
        except FileNotFoundError:
            signature.append((str(path.resolve()), 0, 0, 0))
    return tuple(signature)


def ensure_default_patch_configs_loaded(force: bool = False) -> None:
    """Reload default JSON patch configs when files or workspace selection change."""
    global _DEFAULT_LOAD_SIGNATURE

    candidate_paths = get_default_patch_config_paths()
    signature = _current_load_signature(candidate_paths)
    if not force and signature == _DEFAULT_LOAD_SIGNATURE:
        return

    _FILE_COMMAND_PATCHES.clear()
    _LOADED_PATCH_FILES.clear()
    _LOAD_ERRORS.clear()

    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            _load_command_patch_file(path)
        except Exception as exc:
            _LOAD_ERRORS[str(path.resolve())] = str(exc)

    _DEFAULT_LOAD_SIGNATURE = signature


def apply_command_patches(tool_name: str, command: list[str], context: dict | None = None) -> list[str]:
    """Apply all registered command patches to a tool invocation."""
    ensure_default_patch_configs_loaded()

    current = list(command)
    patch_context = dict(context or {})
    for patch in _FILE_COMMAND_PATCHES.get(tool_name, []):
        updated = patch(list(current), patch_context)
        if updated:
            current = list(updated)
    for patch in _MANUAL_COMMAND_PATCHES.get(tool_name, []):
        updated = patch(list(current), patch_context)
        if updated:
            current = list(updated)
    return current


def list_command_patches(tool_name: str | None = None) -> dict[str, int]:
    """Expose patch counts for diagnostics and future admin UI."""
    ensure_default_patch_configs_loaded()

    names = {tool_name} if tool_name else set(_FILE_COMMAND_PATCHES) | set(_MANUAL_COMMAND_PATCHES)
    return {
        name: len(_FILE_COMMAND_PATCHES.get(name, [])) + len(_MANUAL_COMMAND_PATCHES.get(name, []))
        for name in sorted(names)
    }


def get_patch_diagnostics() -> dict[str, Any]:
    """Return patch loader diagnostics for backend status and debugging."""
    ensure_default_patch_configs_loaded()
    return {
        "counts": list_command_patches(),
        "loaded_files": list(_LOADED_PATCH_FILES),
        "errors": dict(_LOAD_ERRORS),
    }
