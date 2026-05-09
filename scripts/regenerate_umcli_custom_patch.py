#!/usr/bin/env python3
"""
根据 vendor/um-cli/patches/BASELINE.txt 指定的官方 tag，
将当前 vendor/um-cli/source 相对该 tag 的差异导出为
vendor/um-cli/patches/001-mediatools-customizations.patch

仅用于维护者更新补丁文件；输出补丁为 git 原生格式（含二进制），勿用 PowerShell 重定向写入。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_URL = "https://git.um-react.app/um/cli.git"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _sync_local_tree_into_repo(work: Path, local_source: Path) -> None:
    for child in list(work.iterdir()):
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for item in local_source.iterdir():
        dest = work / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def main() -> int:
    root = _project_root()
    patch_dir = root / "vendor" / "um-cli" / "patches"
    baseline_file = patch_dir / "BASELINE.txt"
    local_source = root / "vendor" / "um-cli" / "source"
    out_patch = patch_dir / "001-mediatools-customizations.patch"

    if not baseline_file.exists():
        print(f"[错误] 缺少基线文件: {baseline_file}", file=sys.stderr)
        return 1
    tag = baseline_file.read_text(encoding="utf-8").strip()
    if not tag:
        print("[错误] BASELINE.txt 为空", file=sys.stderr)
        return 1
    if not local_source.is_dir():
        print(f"[错误] 本地源码目录不存在: {local_source}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="umcli-patchgen-") as tmp:
        work = Path(tmp) / "work"
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", tag, UPSTREAM_URL, str(work)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"[错误] git clone 失败 (tag={tag}):\n{r.stderr}", file=sys.stderr)
            return 1
        _sync_local_tree_into_repo(work, local_source)
        r = subprocess.run(["git", "-C", str(work), "add", "-A"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[错误] git add 失败:\n{r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run(
            ["git", "-C", str(work), "diff", "HEAD", "--cached", "--binary", f"--output={out_patch}"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"[错误] git diff 失败:\n{r.stderr}", file=sys.stderr)
            return 1

    if not out_patch.is_file() or out_patch.stat().st_size == 0:
        print("[错误] 未生成补丁或补丁为空", file=sys.stderr)
        return 1
    print(f"[成功] 已写入 {out_patch} ({out_patch.stat().st_size} bytes)，基线 {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
