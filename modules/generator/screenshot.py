"""截图生成器

从视频中提取关键帧作为素材。
"""
from pathlib import Path

from adapters import FFmpegAdapter
from core.logger import get_logger

logger = get_logger(__name__)


class ScreenshotGenerator:
    """视频截图生成器"""

    def __init__(self):
        self.ffmpeg = FFmpegAdapter()

    def extract_frame(
        self,
        video_path: str,
        timestamp: str,
        output_path: str,
        quality: int = 2,
    ) -> dict:
        """
        从视频中提取单帧截图。

        参数:
            video_path: 视频文件路径
            timestamp: 时间戳 (格式: HH:MM:SS 或秒数)
            output_path: 输出图片路径
            quality: 图片质量 (1-31, 数字越小质量越高)

        返回:
            {"success": bool, "output_path": str, "error": str}
        """
        if not self.ffmpeg.is_available():
            return {
                "success": False,
                "output_path": "",
                "error": f"FFmpeg 未安装，请放置于: {self.ffmpeg.bin_dir}",
            }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        args = [
            "-ss", timestamp,
            "-i", video_path,
            "-vframes", "1",
            "-q:v", str(quality),
            "-y",
            output_path,
        ]

        try:
            result = self.ffmpeg.run(
                args,
                capture_output=True,
                text=True,
                context={
                    "operation": "screenshot",
                    "input_path": video_path,
                    "timestamp": timestamp,
                },
            )
            if result.returncode == 0:
                logger.info(f"截图成功: {output_path}")
                return {"success": True, "output_path": output_path, "error": ""}
            else:
                error_msg = result.stderr[:500]
                logger.error(f"截图失败: {error_msg}")
                return {"success": False, "output_path": "", "error": error_msg}
        except Exception as e:
            logger.error(f"截图异常: {e}", exc_info=True)
            return {"success": False, "output_path": "", "error": str(e)}

    def extract_multiple_frames(
        self,
        video_path: str,
        timestamps: list[str],
        output_dir: str,
        name_template: str = "frame_{index:04d}.jpg",
        quality: int = 2,
    ) -> dict:
        """
        批量提取多个时间点的截图。

        参数:
            video_path: 视频文件路径
            timestamps: 时间戳列表
            output_dir: 输出目录
            name_template: 文件名模板
            quality: 图片质量

        返回:
            {"success": bool, "output_paths": list[str], "errors": list[str]}
        """
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        output_paths = []
        errors = []

        for idx, timestamp in enumerate(timestamps, 1):
            output_name = name_template.format(index=idx, timestamp=timestamp.replace(":", "-"))
            output_path = str(output_dir_path / output_name)

            result = self.extract_frame(video_path, timestamp, output_path, quality)
            if result["success"]:
                output_paths.append(result["output_path"])
            else:
                errors.append(f"{timestamp}: {result['error']}")

        return {
            "success": len(errors) == 0,
            "output_paths": output_paths,
            "errors": errors,
        }
