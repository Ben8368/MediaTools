"""
从 EXE/ICO/DLL 文件中提取最高质量图标并保存为 PNG 文件。

用法:
    python extract_icon.py <exe_path> [output_png]

示例:
    python extract_icon.py AfterFX.exe
    python extract_icon.py AfterFX.exe output.png
    python extract_icon.py "C:\\Program Files\\app.exe" "C:\\output\\icon.png"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assets import extract_icon


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    exe_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在从 {exe_file} 提取图标...")
    result = extract_icon(exe_file, out_file)

    if result["ok"]:
        print(f"OK: {result['output']} ({result['method']}, {result['size']} bytes)")
        return 0
    else:
        print(f"FAIL: {result['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
