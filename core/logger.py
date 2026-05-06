"""Shared logging setup helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "mediatools",
    level: str = "INFO",
    log_file: Path | None = None,
    console: bool = True,
) -> logging.Logger:
    """Configure and return a logger with optional console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console or log_file:
        try:
            from services.log_buffer import attach_log_buffer

            attach_log_buffer(logger)
        except Exception:
            pass

    return logger


def get_logger(name: str = "mediatools") -> logging.Logger:
    """Return an existing configured logger or create a default console logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
