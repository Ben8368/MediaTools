#!/usr/bin/env python3
"""
移除兼容层并迁移所有代码到新的导入路径

此脚本将：
1. 更新所有 services/ 中的文件导入
2. 更新 adapters/ 中的文件导入
3. 更新 core/ 中的文件导入
4. 更新 patches/ 中的文件导入
5. 删除兼容层文件
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# 导入替换规则
IMPORT_REPLACEMENTS = [
    # Config
    (r'\bfrom config import\b', 'from backend.config import'),
    (r'\bimport config\b', 'import backend.config as config'),

    # Services -> Backend.services (保持通用规则在最后)
    (r'\bfrom services\.agent import\b', 'from backend.agent.service import'),
    (r'\bfrom services\.agent_tools import\b', 'from backend.agent.tools import'),
    (r'\bfrom services\.agent_tool_specs import\b', 'from backend.agent.tool_specs import'),
    (r'\bfrom services\.agent_helpers import\b', 'from backend.agent.helpers import'),
    (r'\bfrom services\.agent_direct_routes import\b', 'from backend.agent.routes import'),

    # API
    (r'\bfrom services\.api_server import\b', 'from backend.api.server import'),
    (r'\bfrom services\.api_server_setup import\b', 'from backend.api.setup import'),
    (r'\bfrom services\.api_server_runtime import\b', 'from backend.api.runtime import'),
    (r'\bfrom services\.api_models import\b', 'from backend.api.models import'),

    # Media
    (r'\bfrom services\.media import\b', 'from backend.services.media.core import'),
    (r'\bfrom services\.media_fetch import\b', 'from backend.services.media.fetch import'),
    (r'\bfrom services\.media_encoding import\b', 'from backend.services.media.encoding import'),
    (r'\bfrom services\.media_decrypt import\b', 'from backend.services.media.decrypt import'),
    (r'\bfrom services\.media_workflows import\b', 'from backend.services.media.workflows import'),
    (r'\bfrom services\.media_helpers import\b', 'from backend.services.media.helpers import'),

    # Runtime
    (r'\bfrom services\.editor_runtime import\b', 'from backend.services.runtime.editor import'),
    (r'\bfrom services\.filebrowser_runtime import\b', 'from backend.services.runtime.filebrowser import'),

    # Other services (通用规则)
    (r'\bfrom services\.(\w+) import\b', r'from backend.services.\1 import'),
    (r'\bimport services\.(\w+)\b', r'import backend.services.\1'),
]

def update_file(file_path: Path) -> bool:
    """更新单个文件中的导入"""
    try:
        # 处理不同编码
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding='utf-16')
            except (UnicodeDecodeError, OSError):
                print(f"Skipping {file_path}: encoding error")
                return False

        original = content

        # 应用所有导入替换规则
        for pattern, replacement in IMPORT_REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """批量更新所有文件"""
    updated_files = []

    # 需要更新的目录
    directories = [
        ROOT / "services",
        ROOT / "adapters",
        ROOT / "core",
        ROOT / "patches",
    ]

    for directory in directories:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            if update_file(py_file):
                updated_files.append(py_file.relative_to(ROOT))
                print(f"Updated: {py_file.relative_to(ROOT)}")

    print(f"\nTotal updated: {len(updated_files)} files")

    if updated_files:
        print("\nUpdated files:")
        for f in updated_files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()
