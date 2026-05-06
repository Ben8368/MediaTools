"""
媒体转码器

封装常用的 FFmpeg 转码操作。
"""
import re
from pathlib import Path

from adapters import FFmpegAdapter


class Transcoder:
    """媒体转码器"""

    def __init__(self):
        self.ffmpeg = FFmpegAdapter()

    def transcode(self, input_path: str, output_path: str, progress_callback=None, cancel_check=None, **options) -> dict:
        """
        通用转码接口。

        参数:
            input_path: 输入文件
            output_path: 输出文件
            progress_callback: 进度回调函数，接收 0-100 的进度百分比
            cancel_check: 取消检查函数，返回 True 表示应该取消任务
            **options: FFmpeg 参数（如 vcodec="libx265", crf=23）

        返回:
            {"success": bool, "output_path": str, "error": str}
        """
        if not self.ffmpeg.is_available():
            return {
                "success": False,
                "output_path": "",
                "error": f"FFmpeg 未安装，请放置于: {self.ffmpeg.bin_dir}"
            }

        args = ["-y", "-i", input_path]

        # 构建 FFmpeg 参数
        if options.get("no_video"):
            args += ["-vn"]
        elif "vcodec" in options:
            args += ["-c:v", options["vcodec"]]
        if "acodec" in options:
            args += ["-c:a", options["acodec"]]
        if "crf" in options:
            args += ["-crf", str(options["crf"])]
        if "preset" in options:
            args += ["-preset", options["preset"]]
        if "bitrate" in options:
            args += ["-b:v", options["bitrate"]]

        args.append(output_path)

        try:
            if progress_callback or cancel_check:
                result = self.ffmpeg.run_with_progress(
                    args,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                    context={
                        "operation": "transcode",
                        "input_path": input_path,
                        "output_path": output_path,
                    },
                )
            else:
                result = self.ffmpeg.run(
                    args,
                    capture_output=True,
                    text=True,
                    context={
                        "operation": "transcode",
                        "input_path": input_path,
                        "output_path": output_path,
                    },
                )

            # 检查是否被取消
            if result.returncode == -1:
                return {"success": False, "output_path": "", "error": "任务已取消"}

            if result.returncode == 0:
                return {"success": True, "output_path": output_path, "error": ""}
            else:
                return {"success": False, "output_path": "", "error": result.stderr[:500]}
        except Exception as e:
            return {"success": False, "output_path": "", "error": str(e)}

    def to_h265(self, input_path: str, output_path: str = None, crf: int = 23, progress_callback=None, cancel_check=None) -> dict:
        """转换为 H.265/HEVC 编码"""
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".h265.mp4"))
        return self.transcode(input_path, output_path, progress_callback=progress_callback, cancel_check=cancel_check, vcodec="libx265", crf=crf, preset="medium")

    def to_h264(self, input_path: str, output_path: str = None, crf: int = 23, progress_callback=None, cancel_check=None) -> dict:
        """转换为 H.264/AVC 编码"""
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".h264.mp4"))
        return self.transcode(input_path, output_path, progress_callback=progress_callback, cancel_check=cancel_check, vcodec="libx264", crf=crf, preset="medium")

    def extract_audio(self, input_path: str, output_path: str = None, progress_callback=None, cancel_check=None) -> dict:
        """提取音频"""
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".mp3"))
        return self.transcode(input_path, output_path, progress_callback=progress_callback, cancel_check=cancel_check, no_video=True, acodec="libmp3lame")

    def _build_subtitle_filter(self, subtitle_path: str) -> str:
        subtitle_file = Path(subtitle_path).resolve().as_posix()
        subtitle_file = subtitle_file.replace(":", r"\:").replace("'", r"\'")
        return f"subtitles='{subtitle_file}'"

    def slice_video(self, input_path: str, start_time: str, end_time: str, output_path: str = None, accurate: bool = True, subtitle_path: str = None, burn_subtitles: bool = False) -> dict:
        """按时间区间切片，默认使用精确切片（重编码）。"""
        if not self.ffmpeg.is_available():
            return {
                "success": False,
                "output_path": "",
                "error": f"FFmpeg 未安装，请放置于: {self.ffmpeg.bin_dir}",
            }

        input_file = Path(input_path)
        if not input_file.exists():
            return {"success": False, "output_path": "", "error": f"输入文件不存在: {input_path}"}

        if output_path is None:
            output_path = str(input_file.with_name(f"{input_file.stem}_{self._safe_time_tag(start_time)}_{self._safe_time_tag(end_time)}.mp4"))

        if burn_subtitles and subtitle_path:
            subtitle_file = Path(subtitle_path)
            if not subtitle_file.exists():
                return {"success": False, "output_path": "", "error": f"字幕文件不存在: {subtitle_path}"}

        try:
            if accurate:
                args = [
                    "-y",
                    "-i", input_path,
                    "-ss", start_time,
                    "-to", end_time,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-preset", "medium",
                    "-crf", "23",
                ]
                if burn_subtitles and subtitle_path:
                    args += ["-vf", self._build_subtitle_filter(subtitle_path)]
                args.append(output_path)
            else:
                args = [
                    "-y",
                    "-ss", start_time,
                    "-to", end_time,
                    "-i", input_path,
                ]
                if burn_subtitles and subtitle_path:
                    args += [
                        "-vf", self._build_subtitle_filter(subtitle_path),
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        "-preset", "medium",
                        "-crf", "23",
                    ]
                else:
                    args += ["-c", "copy"]
                args.append(output_path)

            result = self.ffmpeg.run(
                args,
                capture_output=True,
                text=True,
                context={
                    "operation": "slice",
                    "input_path": input_path,
                    "output_path": output_path,
                    "accurate": accurate,
                    "burn_subtitles": burn_subtitles,
                },
            )
            if result.returncode == 0:
                return {"success": True, "output_path": output_path, "error": ""}
            return {"success": False, "output_path": "", "error": result.stderr[:500]}
        except Exception as e:
            return {"success": False, "output_path": "", "error": str(e)}

    def _safe_time_tag(self, value: str) -> str:
        return re.sub(r"[^0-9]", "", value)[:12] or "clip"
