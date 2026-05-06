"""
文件管理器

提供文件系统操作功能：列出、创建、删除、重命名、复制、移动文件和目录。
"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class FileManager:
    """文件系统操作管理器"""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = (Path(base_dir) if base_dir else Path.cwd()).resolve()

    def _validate_path(self, path: str) -> Path:
        """验证路径安全性，防止路径遍历攻击"""
        raw_path = Path(path)
        target = raw_path if raw_path.is_absolute() else self.base_dir / raw_path
        target = target.resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            raise ValueError(f"Path {path} is outside base directory")
        return target

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.base_dir))

    def _validate_new_name(self, new_name: str) -> str:
        clean_name = (new_name or "").strip()
        if not clean_name or clean_name in {".", ".."}:
            raise ValueError("New name cannot be empty")
        if Path(clean_name).name != clean_name:
            raise ValueError("New name must not contain path separators")
        return clean_name

    def list_directory(self, directory: str = ".", show_hidden: bool = False) -> dict[str, Any]:
        """
        列出目录内容

        参数:
            directory: 目录路径（相对于base_dir）
            show_hidden: 是否显示隐藏文件

        返回:
            包含files和directories列表的字典
        """
        target_dir = self._validate_path(directory)

        if not target_dir.exists():
            raise FileNotFoundError(f"Directory {directory} does not exist")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"{directory} is not a directory")

        files = []
        directories = []

        for item in target_dir.iterdir():
            if not show_hidden and item.name.startswith('.'):
                continue

            stat = item.stat()
            info = {
                "name": item.name,
                "path": self._relative(item),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }

            if item.is_dir():
                info["type"] = "directory"
                directories.append(info)
            else:
                info["type"] = "file"
                info["extension"] = item.suffix.lower()
                files.append(info)

        return {
            "path": self._relative(target_dir),
            "files": sorted(files, key=lambda x: x["name"].lower()),
            "directories": sorted(directories, key=lambda x: x["name"].lower()),
        }

    def create_directory(self, path: str) -> dict[str, Any]:
        """创建目录"""
        target = self._validate_path(path)

        if target.exists():
            raise FileExistsError(f"Directory {path} already exists")

        target.mkdir(parents=True, exist_ok=False)
        return {"ok": True, "path": self._relative(target)}

    def delete(self, path: str, recursive: bool = False) -> dict[str, Any]:
        """
        删除文件或目录

        参数:
            path: 文件或目录路径
            recursive: 是否递归删除目录
        """
        target = self._validate_path(path)

        if not target.exists():
            raise FileNotFoundError(f"{path} does not exist")

        if target.is_dir():
            if not recursive:
                raise IsADirectoryError(f"{path} is a directory, use recursive=True")
            shutil.rmtree(target)
        else:
            target.unlink()

        return {"ok": True, "deleted": self._relative(target)}

    def rename(self, old_path: str, new_name: str) -> dict[str, Any]:
        """
        重命名文件或目录

        参数:
            old_path: 原路径
            new_name: 新名称（不是完整路径，只是名称）
        """
        source = self._validate_path(old_path)
        clean_name = self._validate_new_name(new_name)

        if not source.exists():
            raise FileNotFoundError(f"{old_path} does not exist")

        target = self._validate_path(str(source.parent / clean_name))
        if target.exists():
            raise FileExistsError(f"{clean_name} already exists in the same directory")

        source.rename(target)
        return {
            "ok": True,
            "old_path": self._relative(source),
            "new_path": self._relative(target),
        }

    def copy(self, source_path: str, dest_path: str) -> dict[str, Any]:
        """
        复制文件或目录

        参数:
            source_path: 源路径
            dest_path: 目标路径
        """
        source = self._validate_path(source_path)
        dest = self._validate_path(dest_path)

        if not source.exists():
            raise FileNotFoundError(f"{source_path} does not exist")
        if dest.exists():
            raise FileExistsError(f"{dest_path} already exists")

        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)

        return {
            "ok": True,
            "source": self._relative(source),
            "destination": self._relative(dest),
        }

    def move(self, source_path: str, dest_path: str) -> dict[str, Any]:
        """
        移动文件或目录

        参数:
            source_path: 源路径
            dest_path: 目标路径
        """
        source = self._validate_path(source_path)
        dest = self._validate_path(dest_path)

        if not source.exists():
            raise FileNotFoundError(f"{source_path} does not exist")
        if dest.exists():
            raise FileExistsError(f"{dest_path} already exists")

        shutil.move(str(source), str(dest))
        return {
            "ok": True,
            "source": self._relative(source),
            "destination": self._relative(dest),
        }

    def get_file_info(self, path: str) -> dict[str, Any]:
        """获取文件或目录详细信息"""
        target = self._validate_path(path)

        if not target.exists():
            raise FileNotFoundError(f"{path} does not exist")

        stat = target.stat()
        info = {
            "name": target.name,
            "path": self._relative(target),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "is_directory": target.is_dir(),
            "is_file": target.is_file(),
        }

        if target.is_file():
            info["extension"] = target.suffix.lower()

        return info
