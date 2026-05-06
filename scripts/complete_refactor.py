#!/usr/bin/env python3
"""
MediaTools 完整架构重构脚本

自动化执行完整的 backend/ 重构：
1. 创建目录结构
2. 移动所有文件
3. 更新所有导入
4. 创建兼容层
"""
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).parent.parent

# 文件移动映射
FILE_MOVES: Dict[str, str] = {
    # Agent 层
    "services/agent.py": "backend/agent/service.py",
    "services/agent_tools.py": "backend/agent/tools.py",
    "services/agent_tool_specs.py": "backend/agent/tool_specs.py",
    "services/agent_helpers.py": "backend/agent/helpers.py",
    "services/agent_direct_routes.py": "backend/agent/routes.py",

    # API 核心
    "services/api_server.py": "backend/api/server.py",
    "services/api_server_setup.py": "backend/api/setup.py",
    "services/api_server_runtime.py": "backend/api/runtime.py",
    "services/api_models.py": "backend/api/models.py",
    "services/api_modules.py": "backend/api/modules.py",

    # API 路由
    "services/api_media_routes.py": "backend/api/routes/media.py",
    "services/api_assets_routes.py": "backend/api/routes/assets.py",
    "services/api_files_routes.py": "backend/api/routes/files.py",
    "services/api_workspace_routes.py": "backend/api/routes/workspace.py",
    "services/api_workbench_routes.py": "backend/api/routes/workbench.py",
    "services/api_photoshop_routes.py": "backend/api/routes/photoshop.py",
    "services/api_adobe_routes.py": "backend/api/routes/adobe.py",
    "services/api_auditor_routes.py": "backend/api/routes/auditor.py",
    "services/api_wechat_routes.py": "backend/api/routes/wechat.py",
    "services/api_system_routes.py": "backend/api/routes/system.py",
    "services/api_filebrowser_routes.py": "backend/api/routes/filebrowser.py",
    "services/api_browser_routes.py": "backend/api/routes/browser.py",
    "services/api_path_picker_routes.py": "backend/api/routes/path_picker.py",
    "services/api_task_center.py": "backend/api/routes/task_center.py",
    "services/api_log_routes.py": "backend/api/routes/log.py",

    # 媒体服务
    "services/media.py": "backend/services/media/core.py",
    "services/media_fetch.py": "backend/services/media/fetch.py",
    "services/media_encoding.py": "backend/services/media/encoding.py",
    "services/media_decrypt.py": "backend/services/media/decrypt.py",
    "services/media_workflows.py": "backend/services/media/workflows.py",
    "services/media_helpers.py": "backend/services/media/helpers.py",

    # 运行时服务
    "services/editor_runtime.py": "backend/services/runtime/editor.py",
    "services/filebrowser_runtime.py": "backend/services/runtime/filebrowser.py",

    # 其他服务
    "services/workspace.py": "backend/services/workspace.py",
    "services/workbench.py": "backend/services/workbench.py",
    "services/path_picker.py": "backend/services/path_picker.py",
    "services/photoshop.py": "backend/services/photoshop.py",
    "services/photoshop_state.py": "backend/services/photoshop_state.py",
    "services/auditor.py": "backend/services/auditor.py",
    "services/wechat_moments.py": "backend/services/wechat_moments.py",
    "services/system_monitor.py": "backend/services/system_monitor.py",
    "services/system_fonts.py": "backend/services/system_fonts.py",
    "services/browser_manager.py": "backend/services/browser_manager.py",
    "services/task_center.py": "backend/services/task_center.py",
    "services/log_buffer.py": "backend/services/log_buffer.py",
    "services/fetcher.py": "backend/services/fetcher.py",
    "services/encoder.py": "backend/services/encoder.py",
    "services/decryptor.py": "backend/services/decryptor.py",

    # CLI
    "main.py": "cli/main.py",
}

# 导入替换规则（按顺序应用）
IMPORT_REPLACEMENTS: List[Tuple[str, str]] = [
    # Config
    (r'\bfrom config import\b', 'from backend.config import'),
    (r'\bimport config\b', 'import backend.config as config'),

    # Agent
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
    (r'\bfrom services\.api_modules import\b', 'from backend.api.modules import'),

    # API Routes
    (r'\bfrom services\.api_media_routes import\b', 'from backend.api.routes.media import'),
    (r'\bfrom services\.api_assets_routes import\b', 'from backend.api.routes.assets import'),
    (r'\bfrom services\.api_files_routes import\b', 'from backend.api.routes.files import'),
    (r'\bfrom services\.api_workspace_routes import\b', 'from backend.api.routes.workspace import'),
    (r'\bfrom services\.api_workbench_routes import\b', 'from backend.api.routes.workbench import'),
    (r'\bfrom services\.api_photoshop_routes import\b', 'from backend.api.routes.photoshop import'),
    (r'\bfrom services\.api_adobe_routes import\b', 'from backend.api.routes.adobe import'),
    (r'\bfrom services\.api_auditor_routes import\b', 'from backend.api.routes.auditor import'),
    (r'\bfrom services\.api_wechat_routes import\b', 'from backend.api.routes.wechat import'),
    (r'\bfrom services\.api_system_routes import\b', 'from backend.api.routes.system import'),
    (r'\bfrom services\.api_filebrowser_routes import\b', 'from backend.api.routes.filebrowser import'),
    (r'\bfrom services\.api_browser_routes import\b', 'from backend.api.routes.browser import'),
    (r'\bfrom services\.api_path_picker_routes import\b', 'from backend.api.routes.path_picker import'),
    (r'\bfrom services\.api_task_center import\b', 'from backend.api.routes.task_center import'),
    (r'\bfrom services\.api_log_routes import\b', 'from backend.api.routes.log import'),

    # Media services
    (r'\bfrom services\.media import\b', 'from backend.services.media.core import'),
    (r'\bfrom services\.media_fetch import\b', 'from backend.services.media.fetch import'),
    (r'\bfrom services\.media_encoding import\b', 'from backend.services.media.encoding import'),
    (r'\bfrom services\.media_decrypt import\b', 'from backend.services.media.decrypt import'),
    (r'\bfrom services\.media_workflows import\b', 'from backend.services.media.workflows import'),
    (r'\bfrom services\.media_helpers import\b', 'from backend.services.media.helpers import'),

    # Runtime services
    (r'\bfrom services\.editor_runtime import\b', 'from backend.services.runtime.editor import'),
    (r'\bfrom services\.filebrowser_runtime import\b', 'from backend.services.runtime.filebrowser import'),

    # Other services (keep in backend.services)
    (r'\bfrom services\.(\w+) import\b', r'from backend.services.\1 import'),
]


def create_directories():
    """创建所有必要的目录"""
    dirs = [
        "backend",
        "backend/config",
        "backend/api",
        "backend/api/routes",
        "backend/agent",
        "backend/services",
        "backend/services/media",
        "backend/services/runtime",
        "cli",
    ]
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "__init__.py").touch()
    print(f"Created {len(dirs)} directories")


def move_files():
    """移动所有文件到新位置"""
    moved = 0
    for src, dst in FILE_MOVES.items():
        src_path = ROOT / src
        dst_path = ROOT / dst
        if src_path.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            moved += 1
            print(f"Moved: {src} -> {dst}")
    print(f"Moved {moved} files")


def update_imports_in_file(file_path: Path) -> bool:
    """更新单个文件中的导入"""
    try:
        # 处理 UTF-16 编码的文件
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='utf-16')

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


def update_all_imports():
    """更新所有 Python 文件中的导入"""
    updated = 0

    # 更新 backend/ 中的文件
    for py_file in (ROOT / "backend").rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if update_imports_in_file(py_file):
            updated += 1
            print(f"Updated imports: {py_file.relative_to(ROOT)}")

    # 更新 cli/ 中的文件
    for py_file in (ROOT / "cli").rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if update_imports_in_file(py_file):
            updated += 1
            print(f"Updated imports: {py_file.relative_to(ROOT)}")

    # 更新 modules/ 中的文件
    for py_file in (ROOT / "modules").rglob("*.py"):
        if update_imports_in_file(py_file):
            updated += 1
            print(f"Updated imports: {py_file.relative_to(ROOT)}")

    print(f"Updated {updated} files")


def create_config_files():
    """创建配置相关文件"""
    # 移动 config.py
    shutil.copy2(ROOT / "config.py", ROOT / "backend/config/settings.py")

    # 更新 BASE_DIR
    settings_path = ROOT / "backend/config/settings.py"
    content = settings_path.read_text(encoding='utf-8')
    content = content.replace(
        'BASE_DIR = Path(__file__).parent',
        '# 注意：此文件位于 backend/config/，需要向上两级到达项目根目录\nBASE_DIR = Path(__file__).parent.parent.parent'
    )
    settings_path.write_text(content, encoding='utf-8')

    # 创建 backend/config/__init__.py
    (ROOT / "backend/config/__init__.py").write_text(
        '"""Backend configuration module."""\n'
        'from backend.config.settings import *  # noqa: F401, F403\n',
        encoding='utf-8'
    )

    # 创建兼容层 config.py
    (ROOT / "config.py").write_text(
        '"""\n'
        'DEPRECATED: This module has moved to backend.config\n\n'
        'Please update your imports:\n'
        '    from backend.config import *\n'
        '"""\n'
        'import warnings\n'
        'warnings.warn(\n'
        '    "Importing from \'config\' is deprecated. Use \'backend.config\' instead.",\n'
        '    DeprecationWarning,\n'
        '    stacklevel=2,\n'
        ')\n'
        'from backend.config import *  # noqa: F401, F403\n',
        encoding='utf-8'
    )
    print("Created config files")


def create_compatibility_layers():
    """创建兼容层文件"""
    # main.py 兼容层
    (ROOT / "main.py").write_text(
        '"""\n'
        'DEPRECATED: This module has moved to cli.main\n\n'
        'Please run:\n'
        '    python -m cli.main\n'
        '"""\n'
        'import warnings\n'
        'warnings.warn(\n'
        '    "Running \'python main.py\' is deprecated. Use \'python -m cli.main\' instead.",\n'
        '    DeprecationWarning,\n'
        '    stacklevel=2,\n'
        ')\n'
        'from cli.main import main\n\n'
        'if __name__ == "__main__":\n'
        '    main()\n',
        encoding='utf-8'
    )
    print("Created compatibility layers")


def update_app_py():
    """更新 app.py"""
    app_path = ROOT / "app.py"
    content = app_path.read_text(encoding='utf-8')

    # 更新导入
    content = content.replace(
        'from config import',
        'from backend.config import'
    )

    # 更新 uvicorn.run
    content = content.replace(
        '"api_server:app"',
        '"backend.api.server:app"'
    )
    content = content.replace(
        'app_dir=str(root_dir / "services"),',
        ''
    )

    app_path.write_text(content, encoding='utf-8')
    print("Updated app.py")


def main():
    """执行完整重构"""
    print("=" * 60)
    print("MediaTools 完整架构重构")
    print("=" * 60)

    print("\n[1/7] 创建目录结构...")
    create_directories()

    print("\n[2/7] 创建配置文件...")
    create_config_files()

    print("\n[3/7] 移动文件...")
    move_files()

    print("\n[4/7] 更新导入...")
    update_all_imports()

    print("\n[5/7] 创建兼容层...")
    create_compatibility_layers()

    print("\n[6/7] 更新 app.py...")
    update_app_py()

    print("\n[7/7] 完成!")
    print("\n" + "=" * 60)
    print("重构完成！请运行以下命令测试：")
    print("  python -c \"from backend.config import BASE_DIR; print(BASE_DIR)\"")
    print("  python app.py --help")
    print("=" * 60)


if __name__ == "__main__":
    main()
