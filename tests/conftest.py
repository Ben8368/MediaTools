"""Shared pytest test environment."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_DIR = PROJECT_ROOT / ".tmp-tests"
TEST_RUN_TEMP_DIR = TEST_TEMP_DIR / f"run-{os.getpid()}-{uuid.uuid4().hex}"


def _rmtree_retry(path: Path) -> None:
    for _ in range(5):
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            return
        time.sleep(0.1)


def _cleanup_test_runs(include_current: bool = False) -> None:
    """Best-effort cleanup for interrupted pytest runs from earlier sessions."""
    if not TEST_TEMP_DIR.exists():
        return
    for path in TEST_TEMP_DIR.glob("run-*"):
        if path == TEST_RUN_TEMP_DIR and not include_current:
            continue
        _rmtree_retry(path)


_cleanup_test_runs()
TEST_RUN_TEMP_DIR.mkdir(parents=True, exist_ok=True)

os.environ["TMP"] = str(TEST_RUN_TEMP_DIR)
os.environ["TEMP"] = str(TEST_RUN_TEMP_DIR)
os.environ["TMPDIR"] = str(TEST_RUN_TEMP_DIR)
tempfile.tempdir = str(TEST_RUN_TEMP_DIR)


def _workspace_mkdtemp(suffix: str | None = None, prefix: str | None = None, dir: str | None = None) -> str:
    """Create test temp dirs without Python 3.14's restrictive Windows ACLs."""
    base = Path(dir) if dir is not None else TEST_RUN_TEMP_DIR
    prefix = "tmp" if prefix is None else prefix
    suffix = "" if suffix is None else suffix
    base.mkdir(parents=True, exist_ok=True)

    for _ in range(100):
        path = base / f"{prefix}{uuid.uuid4().hex}{suffix}"
        try:
            path.mkdir()
            return str(path)
        except FileExistsError:
            continue
    raise FileExistsError(f"could not create a unique temporary directory in {base}")


if os.name == "nt":
    tempfile.mkdtemp = _workspace_mkdtemp


@pytest.fixture
def tmp_path() -> Path:
    """Use a plain workspace temp dir instead of pytest's Windows ACL temp factory."""
    path = Path(_workspace_mkdtemp(prefix="pytest-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus):
    """Remove this test session's scratch directory after pytest has finished."""
    _cleanup_test_runs(include_current=True)


def pytest_unconfigure(config):
    """Final cleanup after pytest plugins have finished their own teardown."""
    _cleanup_test_runs(include_current=True)


atexit.register(lambda: _cleanup_test_runs(include_current=True))
