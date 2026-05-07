"""Stable adapters for external tool integrations."""

from __future__ import annotations

import platform
import subprocess
import time
from pathlib import Path

from core.ffmpeg import FFmpegManager
from modules.decryptor.wrapper import DecryptorWrapper
from modules.fetcher.ytdlp_manager import YtdlpManager
from patches import apply_command_patches

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


class YtdlpAdapter:
    """Adapter for the standalone yt-dlp binary."""

    tool_name = "ytdlp"

    def __init__(self, manager: YtdlpManager | None = None):
        self.manager = manager or YtdlpManager()
        self.bin_dir = self.manager.bin_dir
        self.binary = Path(self.manager.ytdlp_bin)

    def is_available(self) -> bool:
        return self.manager.is_installed()

    def get_status(self) -> dict:
        return self.manager.get_status()

    def get_version(self) -> str:
        return self.manager.get_version()

    def update(self) -> tuple[bool, str]:
        return self.manager.update()

    def download_latest(self) -> tuple[bool, str]:
        return self.manager.download_latest()

    def build_command(self, args: list[str], context: dict | None = None) -> list[str]:
        base_command = self.manager.command() if hasattr(self.manager, "command") else [str(self.binary)]
        if not isinstance(base_command, list):
            base_command = [str(self.binary)]
        return apply_command_patches(self.tool_name, base_command + list(args), context)

    def run(self, args: list[str], *, context: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "encoding": "utf-8",
            "errors": "replace",
        }
        defaults.update(kwargs)
        return subprocess.run(self.build_command(args, context), **defaults)


class FFmpegAdapter:
    """Adapter for ffmpeg and ffprobe binaries."""

    tool_name = "ffmpeg"

    def __init__(self, manager: FFmpegManager | None = None):
        self.manager = manager or FFmpegManager()
        self.bin_dir = self.manager.bin_dir
        self.ffmpeg_bin = Path(self.manager.ffmpeg_bin)
        self.ffprobe_bin = Path(self.manager.ffprobe_bin)

    def is_available(self) -> bool:
        return self.manager.is_available()

    def get_info(self) -> dict:
        return self.manager.get_info()

    def get_version(self) -> str:
        return self.manager.get_version()

    def get_ffmpeg_location(self) -> str:
        return self.manager.get_ffmpeg_location()

    def build_command(self, args: list[str], context: dict | None = None) -> list[str]:
        return apply_command_patches(self.tool_name, [self.manager.get_ffmpeg_path()] + list(args), context)

    def run(self, args: list[str], *, context: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
        if not self.is_available():
            raise RuntimeError(f"FFmpeg was not found. Place ffmpeg and ffprobe in {self.bin_dir}.")
        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "timeout": 3600,
            "encoding": "utf-8",
            "errors": "replace",
        }
        defaults.update(kwargs)
        return subprocess.run(self.build_command(args, context), **defaults)

    def run_with_progress(
        self,
        args: list[str],
        *,
        context: dict | None = None,
        progress_callback=None,
        cancel_check=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        if not self.is_available():
            raise RuntimeError(f"FFmpeg was not found. Place ffmpeg and ffprobe in {self.bin_dir}.")
        return self.manager.run_with_progress(
            args,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
            **kwargs,
        )


class UmcliAdapter:
    """Adapter for Unlock Music CLI."""

    tool_name = "umcli"

    def __init__(self, wrapper: DecryptorWrapper | None = None):
        self.wrapper = wrapper or DecryptorWrapper()
        self.bin_dir = Path(self.wrapper.umcli_bin).parent
        self.binary = Path(self.wrapper.umcli_bin)

    def is_available(self) -> bool:
        return self.wrapper.is_available()

    def get_version(self) -> str:
        return self.wrapper.get_version()

    def get_status(self) -> dict:
        source_available_fn = getattr(self.wrapper, "source_available", None)
        source_available = bool(source_available_fn()) if callable(source_available_fn) else False
        source_dir = getattr(self.wrapper, "source_dir", self.binary)
        return {
            "installed": self.is_available(),
            "version": self.get_version(),
            "path": str(self.binary if self.binary.exists() or not source_available else source_dir),
            "runtime": "binary" if self.binary.exists() else "source" if source_available else "missing",
        }

    def build_command(self, args: list[str], context: dict | None = None) -> list[str]:
        base_command = self.wrapper.command() if hasattr(self.wrapper, "command") else [str(self.binary)]
        if not isinstance(base_command, list):
            base_command = [str(self.binary)]
        return apply_command_patches(self.tool_name, base_command + list(args), context)

    def run(self, args: list[str], *, context: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "encoding": "utf-8",
            "errors": "replace",
        }
        command_cwd = getattr(self.wrapper, "command_cwd", None)
        cwd = command_cwd() if callable(command_cwd) else None
        if cwd:
            defaults["cwd"] = cwd
        defaults.update(kwargs)
        return subprocess.run(self.build_command(args, context), **defaults)

    def run_with_cancel(
        self,
        args: list[str],
        *,
        context: dict | None = None,
        cancel_check=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        defaults = {
            "creationflags": _SUBPROCESS_FLAGS,
            "encoding": "utf-8",
            "errors": "replace",
        }
        command_cwd = getattr(self.wrapper, "command_cwd", None)
        cwd = command_cwd() if callable(command_cwd) else None
        if cwd:
            defaults["cwd"] = cwd
        defaults.update(kwargs)

        cmd = self.build_command(args, context)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **defaults,
        )

        cancelled = False
        while process.poll() is None:
            if cancel_check and cancel_check():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                cancelled = True
                break
            time.sleep(0.5)

        stdout, stderr = process.communicate() if not cancelled else (process.stdout.read(), process.stderr.read())
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1 if cancelled else process.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def decrypt(
        self,
        input_path: str,
        output_dir: str | None = None,
        remove_source: bool = False,
        cancel_check=None,
    ) -> dict:
        cmd = ["-i", input_path]
        if output_dir:
            cmd += ["-o", output_dir]
        if remove_source:
            cmd.append("--remove-source")
        try:
            if cancel_check:
                result = self.run_with_cancel(
                    cmd,
                    cancel_check=cancel_check,
                    context={
                        "operation": "decrypt",
                        "input_path": input_path,
                        "output_dir": output_dir or "",
                        "remove_source": remove_source,
                    },
                )
            else:
                result = self.run(
                    cmd,
                    timeout=300,
                    context={
                        "operation": "decrypt",
                        "input_path": input_path,
                        "output_dir": output_dir or "",
                        "remove_source": remove_source,
                    },
                )

            if result.returncode == -1:
                return {"success": False, "output": "", "error": "Task cancelled"}
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Decrypt timed out after 5 minutes"}
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc)}

    def decrypt_batch(
        self,
        input_dir: str,
        output_dir: str | None = None,
        remove_source: bool = False,
        cancel_check=None,
    ) -> dict:
        cmd = ["-i", input_dir]
        if output_dir:
            cmd += ["-o", output_dir]
        if remove_source:
            cmd.append("--remove-source")
        try:
            if cancel_check:
                result = self.run_with_cancel(
                    cmd,
                    cancel_check=cancel_check,
                    context={
                        "operation": "decrypt_batch",
                        "input_path": input_dir,
                        "output_dir": output_dir or "",
                        "remove_source": remove_source,
                    },
                )
            else:
                result = self.run(
                    cmd,
                    timeout=1800,
                    context={
                        "operation": "decrypt_batch",
                        "input_path": input_dir,
                        "output_dir": output_dir or "",
                        "remove_source": remove_source,
                    },
                )

            if result.returncode == -1:
                return {"success": False, "output": "", "error": "Task cancelled"}
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Batch decrypt timed out after 30 minutes"}
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc)}
