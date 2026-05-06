"""
modules.assets - 素材管理模块

扫描、索引和检索本地媒体素材文件，提供文件管理和预览功能。
"""

from .file_manager import FileManager
from .icon_extractor import extract_icon
from .library import AssetLibrary
from .preview import PreviewGenerator

__all__ = ["AssetLibrary", "extract_icon", "FileManager", "PreviewGenerator"]
