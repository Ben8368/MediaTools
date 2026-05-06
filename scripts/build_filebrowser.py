"""Build filebrowser.exe from vendor/filebrowser source."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "vendor" / "filebrowser"
OUTPUT = ROOT / "bin" / "filebrowser.exe"


def main() -> int:
    if not SOURCE_DIR.exists():
        print(f"Source not found: {SOURCE_DIR}")
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["go", "build", "-o", str(OUTPUT), "."]
    try:
        subprocess.run(cmd, cwd=str(SOURCE_DIR), check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Build failed with exit code {exc.returncode}")
        return exc.returncode
    except FileNotFoundError:
        print("Go toolchain not found in PATH")
        return 1

    print(f"Built: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
