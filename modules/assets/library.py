"""
素材库

扫描并索引本地媒体素材（视频、音频、图片、字幕）。
"""
from datetime import datetime
from pathlib import Path

# 支持的媒体文件扩展名
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".ts"}
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".wma", ".ape"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
SUBTITLE_EXTS = {".srt", ".vtt", ".ass", ".ssa"}

ALL_MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS | IMAGE_EXTS | SUBTITLE_EXTS


def _get_file_type(ext: str) -> str:
    ext = ext.lower()
    if ext in VIDEO_EXTS:
        return "video"
    elif ext in AUDIO_EXTS:
        return "audio"
    elif ext in IMAGE_EXTS:
        return "image"
    elif ext in SUBTITLE_EXTS:
        return "subtitle"
    return "other"


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT_ROOT = PROJECT_ROOT / "projects" / "default"


class AssetLibrary:
    """本地素材库"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = str(DEFAULT_PROJECT_ROOT)
        self.base_dir = Path(base_dir)
        self._index: list[dict] = []
        self.truncated = False

    def scan(self, directory: str = None, max_files: int | None = None) -> list[dict]:
        """
        扫描目录，构建素材索引。

        参数:
            directory: 要扫描的目录（默认为 base_dir）

        返回:
            素材信息列表
        """
        scan_dir = Path(directory) if directory else self.base_dir
        if not scan_dir.exists():
            return []
        if not scan_dir.is_dir():
            return []

        self._index = []
        self.truncated = False
        for path in scan_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in ALL_MEDIA_EXTS:
                if max_files is not None and len(self._index) >= max_files:
                    self.truncated = True
                    break
                stat = path.stat()
                self._index.append({
                    "path": str(path),
                    "name": path.name,
                    "stem": path.stem,
                    "ext": path.suffix.lower(),
                    "type": _get_file_type(path.suffix),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "directory": str(path.parent),
                })

        return self._index

    def list_assets(self, asset_type: str = None) -> list[dict]:
        """
        列出素材，可按类型过滤。

        参数:
            asset_type: "video" | "audio" | "image" | "subtitle" | None（全部）
        """
        if not self._index:
            self.scan()
        if asset_type:
            return [a for a in self._index if a["type"] == asset_type]
        return self._index

    def search(self, keyword: str) -> list[dict]:
        """按文件名关键词搜索素材"""
        if not self._index:
            self.scan()
        keyword_lower = keyword.lower()
        return [a for a in self._index if keyword_lower in a["name"].lower()]

    def get_stats(self) -> dict:
        """获取素材库统计信息"""
        if not self._index:
            self.scan()
        stats: dict = {"total": len(self._index), "by_type": {}}
        for asset in self._index:
            t = asset["type"]
            if t not in stats["by_type"]:
                stats["by_type"][t] = {"count": 0, "total_size_mb": 0.0}
            stats["by_type"][t]["count"] += 1
            stats["by_type"][t]["total_size_mb"] = round(
                stats["by_type"][t]["total_size_mb"] + asset["size_mb"], 2
            )
        return stats
