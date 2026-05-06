"""Patch registries and config loaders for external tool adapters."""

from .tool_patches import (
    apply_command_patches,
    ensure_default_patch_configs_loaded,
    get_default_patch_config_paths,
    get_patch_diagnostics,
    list_command_patches,
    load_command_patch_file,
    register_command_patch,
    register_command_patch_spec,
)

__all__ = [
    "apply_command_patches",
    "ensure_default_patch_configs_loaded",
    "get_default_patch_config_paths",
    "get_patch_diagnostics",
    "list_command_patches",
    "load_command_patch_file",
    "register_command_patch",
    "register_command_patch_spec",
]
