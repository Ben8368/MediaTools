"""FFmpeg and FFprobe binary management."""

from __future__ import annotations

import platform
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


def _get_bin_dir() -> Path:
    return Path(__file__).parent.parent / "bin"


class FFmpegManager:
    def __init__(self, bin_dir: Path | None = None):
        self.bin_dir = Path(bin_dir) if bin_dir is not None else _get_bin_dir()
        suffix = ".exe" if platform.system() == "Windows" else ""
        self.ffmpeg_bin = self.bin_dir / f"ffmpeg{suffix}"
        self.ffprobe_bin = self.bin_dir / f"ffprobe{suffix}"

    def is_available(self) -> bool:
        return self.ffmpeg_bin.exists() and self.ffprobe_bin.exists()

    def get_version(self) -> str:
        if not self.is_available():
            return "not installed"
        try:
            result = subprocess.run(
                [str(self.ffmpeg_bin), "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=_SUBPROCESS_FLAGS,
            )
            first_line = result.stdout.split("\n")[0]
            return first_line.replace("ffmpeg version", "").strip()
        except Exception:
            return "unknown"

    def get_ffmpeg_location(self) -> str:
        return str(self.bin_dir) if self.is_available() else ""

    def get_ffmpeg_path(self) -> str:
        return str(self.ffmpeg_bin) if self.ffmpeg_bin.exists() else ""

    def get_ffprobe_path(self) -> str:
        return str(self.ffprobe_bin) if self.ffprobe_bin.exists() else ""

    def get_info(self) -> dict:
        if not self.is_available():
            return {"installed": False, "bin_dir": str(self.bin_dir)}
        return {
            "installed": True,
            "version": self.get_version(),
            "ffmpeg_path": str(self.ffmpeg_bin),
            "ffprobe_path": str(self.ffprobe_bin),
            "ffmpeg_size_mb": round(self.ffmpeg_bin.stat().st_size / (1024 * 1024), 2),
            "ffprobe_size_mb": round(self.ffprobe_bin.stat().st_size / (1024 * 1024), 2),
        }

    def run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        if not self.is_available():
            raise RuntimeError(f"FFmpeg was not found. Place ffmpeg and ffprobe in {self.bin_dir}.")
        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "timeout": 3600,
            "encoding": "utf-8",
            "errors": "replace",
        }
        defaults.update(kwargs)
        return subprocess.run([str(self.ffmpeg_bin)] + args, **defaults)

    def get_duration(self, input_path: str) -> float | None:
        if not self.is_available():
            return None
        try:
            result = subprocess.run(
                [
                    str(self.ffprobe_bin),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    input_path,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            return None
        return None

    def run_with_progress(
        self,
        args: list[str],
        progress_callback: Callable[[float], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        if not self.is_available():
            raise RuntimeError(f"FFmpeg was not found. Place ffmpeg and ffprobe in {self.bin_dir}.")

        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "encoding": "utf-8",
            "errors": "replace",
        }
        defaults.update(kwargs)

        input_path = None
        duration = None
        for index, arg in enumerate(args):
            if arg == "-i" and index + 1 < len(args):
                input_path = args[index + 1]
                break

        if input_path and progress_callback:
            duration = self.get_duration(input_path)

        process = subprocess.Popen(
            [str(self.ffmpeg_bin)] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **defaults,
        )

        stderr_output: list[str] = []
        cancelled = False

        if progress_callback and duration:
            while True:
                if cancel_check and cancel_check():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    cancelled = True
                    break

                line = process.stderr.readline()
                if not line:
                    break
                stderr_output.append(line)

                match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                if match:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress_callback(min((current_time / duration) * 100, 99.0))
        else:
            stderr_output = process.stderr.readlines()

        stdout_output = process.stdout.read()
        if not cancelled:
            process.wait()

        return subprocess.CompletedProcess(
            args=[str(self.ffmpeg_bin)] + args,
            returncode=-1 if cancelled else process.returncode,
            stdout=stdout_output,
            stderr="".join(stderr_output),
        )
