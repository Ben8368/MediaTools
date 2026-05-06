"""
文件预览生成器

为图片、视频、音频生成预览缩略图。
"""
import base64
import subprocess
from pathlib import Path
from typing import Any

from adapters import FFmpegAdapter


class PreviewGenerator:
    """文件预览生成器"""

    def __init__(self):
        self.ffmpeg = FFmpegAdapter()

    def generate_image_preview(self, image_path: str, max_width: int = 400) -> dict[str, Any]:
        """
        生成图片预览（base64编码）

        参数:
            image_path: 图片路径
            max_width: 最大宽度（像素）

        返回:
            包含base64编码图片数据的字典
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image {image_path} does not exist")

        with open(path, "rb") as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        mime_type = self._get_mime_type(path.suffix.lower())

        return {
            "type": "image",
            "mime_type": mime_type,
            "data": f"data:{mime_type};base64,{base64_data}",
            "size": len(image_data),
        }

    def generate_video_thumbnail(
        self,
        video_path: str,
        timestamp: str = "00:00:01",
        output_path: str | None = None
    ) -> dict[str, Any]:
        """
        生成视频缩略图

        参数:
            video_path: 视频路径
            timestamp: 截取时间点（格式：HH:MM:SS）
            output_path: 输出路径（可选，默认生成临时文件）

        返回:
            包含缩略图路径和base64数据的字典
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video {video_path} does not exist")

        if not self.ffmpeg.get_info().get("installed"):
            raise RuntimeError("FFmpeg is not available")

        if output_path is None:
            output_path = str(path.parent / f"{path.stem}_thumb.jpg")

        ffmpeg_bin = self.ffmpeg.get_ffmpeg_path()
        cmd = [
            str(ffmpeg_bin),
            "-ss", timestamp,
            "-i", str(path),
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        with open(output_path, "rb") as f:
            thumb_data = f.read()

        base64_data = base64.b64encode(thumb_data).decode('utf-8')

        return {
            "type": "video_thumbnail",
            "thumbnail_path": output_path,
            "data": f"data:image/jpeg;base64,{base64_data}",
            "size": len(thumb_data),
        }

    def generate_audio_waveform(self, audio_path: str) -> dict[str, Any]:
        """
        生成音频波形图（简化版，返回基本信息）

        参数:
            audio_path: 音频路径

        返回:
            音频元数据
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio {audio_path} does not exist")

        if not self.ffmpeg.get_info().get("installed"):
            raise RuntimeError("FFmpeg is not available")

        ffprobe_bin = self.ffmpeg.get_ffprobe_path()
        cmd = [
            str(ffprobe_bin),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")

        import json
        metadata = json.loads(result.stdout)

        audio_stream = next(
            (s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"),
            {}
        )

        return {
            "type": "audio",
            "duration": float(metadata.get("format", {}).get("duration", 0)),
            "bit_rate": int(metadata.get("format", {}).get("bit_rate", 0)),
            "codec": audio_stream.get("codec_name", "unknown"),
            "sample_rate": int(audio_stream.get("sample_rate", 0)),
            "channels": int(audio_stream.get("channels", 0)),
        }

    def _get_mime_type(self, extension: str) -> str:
        """根据文件扩展名返回MIME类型"""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
        }
        return mime_types.get(extension.lower(), "application/octet-stream")

    def can_preview(self, file_path: str) -> dict[str, Any]:
        """
        检查文件是否可以预览

        返回:
            包含can_preview和preview_type的字典
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}
        audio_exts = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg"}

        if ext in image_exts:
            return {"can_preview": True, "preview_type": "image"}
        elif ext in video_exts:
            return {"can_preview": True, "preview_type": "video"}
        elif ext in audio_exts:
            return {"can_preview": True, "preview_type": "audio"}
        else:
            return {"can_preview": False, "preview_type": None}
