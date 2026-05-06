#!/usr/bin/env python3
"""
批量更新测试文件中的导入路径
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TESTS_DIR = ROOT / "tests"

# 导入替换规则
REPLACEMENTS = [
    (r'\bfrom services\.api_server import\b', 'from backend.api.server import'),
    (r'\bfrom services\.agent import\b', 'from backend.agent.service import'),
    (r'\bfrom services\.(\w+) import\b', r'from backend.services.\1 import'),
    (r'\bimport services\.(\w+)\b', r'import backend.services.\1'),
]

def update_file(file_path: Path) -> bool:
    """更新单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """批量更新所有测试文件"""
    updated = 0

    for py_file in TESTS_DIR.rglob("*.py"):
        if update_file(py_file):
            updated += 1
            print(f"Updated: {py_file.relative_to(ROOT)}")

    print(f"\nUpdated {updated} test files")

if __name__ == "__main__":
    main()
