"""
snapshot.py — 快照 JSON 读写，记录上次审计时的文件状态
"""
import json
import hashlib
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"last_audit_time": None, "files": {}}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Snapshot corrupted, resetting: %s", e)
        return {"last_audit_time": None, "files": {}}


def save(path: str, snapshot: dict):
    """原子写入：先写临时文件，再 rename"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        dir=str(p.parent), suffix=".tmp", prefix=".snapshot_",
        delete=False,
    ) as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        tmp_path = f.name
    os.replace(tmp_path, str(p))


def compute_hash_prefix(filepath: str, size: int = 65536) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read(size))
    return h.hexdigest()[:8]


def file_entry(filepath: str) -> dict:
    stat = os.stat(filepath)
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "hash_prefix": None,  # 仅在 SETTLED 阶段计算
    }


def enrich_hash(entry: dict, filepath: str) -> dict:
    entry["hash_prefix"] = compute_hash_prefix(filepath)
    return entry


def mark_audit_time(snapshot: dict) -> dict:
    snapshot["last_audit_time"] = datetime.now(timezone.utc).isoformat()
    return snapshot
