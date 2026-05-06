"""Compatibility wrapper for legacy fetch service imports.

Keep older import paths working while the canonical implementation lives in
``services.media``. This avoids maintaining two download pipelines.
"""

from .media import (
    fetch_video_info,
    run_fetch_analyze_slice_job,
    run_fetch_batch,
    run_fetch_batch_stream,
)

__all__ = [
    "fetch_video_info",
    "run_fetch_analyze_slice_job",
    "run_fetch_batch",
    "run_fetch_batch_stream",
]
