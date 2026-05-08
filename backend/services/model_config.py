"""Model configuration persistence service."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_config_dir() -> Path:
    config_dir = Path.home() / ".mediatools"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_config_file() -> Path:
    return _get_config_dir() / "model_config.json"


def load_model_config() -> dict[str, Any]:
    config_file = _get_config_file()
    if not config_file.exists():
        return {"baseUrl": "", "model": "", "apiKey": ""}
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "baseUrl": str(data.get("baseUrl", "")).strip(),
            "model": str(data.get("model", "")).strip(),
            "apiKey": str(data.get("apiKey", "")).strip(),
        }
    except Exception as exc:
        logger.warning(f"Failed to load model config: {exc}")
        return {"baseUrl": "", "model": "", "apiKey": ""}


def save_model_config(config: dict[str, Any]) -> dict[str, Any]:
    config_file = _get_config_file()
    normalized = {
        "baseUrl": str(config.get("baseUrl", "")).strip(),
        "model": str(config.get("model", "")).strip(),
        "apiKey": str(config.get("apiKey", "")).strip(),
    }
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    logger.info(f"Model config saved to {config_file}")
    return normalized


def clear_model_config() -> None:
    config_file = _get_config_file()
    if config_file.exists():
        config_file.unlink()
        logger.info(f"Model config cleared: {config_file}")
