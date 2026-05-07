"""Manage the standalone yt-dlp binary."""

from __future__ import annotations

import platform
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

_DOWNLOAD_URLS = {
    "Windows": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
    "Linux": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
    "Darwin": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
}


def _get_bin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "bin"


def _get_vendor_entrypoint() -> Path:
    return Path(__file__).parent.parent.parent / "vendor" / "yt-dlp" / "source" / "yt_dlp" / "__main__.py"


class YtdlpManager:
    def __init__(self, bin_dir: Path | None = None):
        self.allow_source_fallback = bin_dir is None
        self.bin_dir = Path(bin_dir) if bin_dir is not None else _get_bin_dir()
        suffix = ".exe" if platform.system() == "Windows" else ""
        self.ytdlp_bin = self.bin_dir / f"yt-dlp{suffix}"
        self.vendor_entrypoint = _get_vendor_entrypoint()

    def is_installed(self) -> bool:
        return self.ytdlp_bin.exists() or self.source_available()

    def source_available(self) -> bool:
        return self.allow_source_fallback and self.vendor_entrypoint.exists()

    def command(self) -> list[str]:
        if self.ytdlp_bin.exists():
            return [str(self.ytdlp_bin)]
        if self.source_available():
            return [sys.executable, str(self.vendor_entrypoint)]
        return [str(self.ytdlp_bin)]

    def get_version(self) -> str:
        if not self.is_installed():
            return "not installed"
        try:
            result = subprocess.run(
                self.command() + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def update(self) -> tuple[bool, str]:
        if not self.is_installed():
            return self.download_latest()

        before = self.get_version()
        try:
            result = subprocess.run(
                self.command() + ["-U"],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=_SUBPROCESS_FLAGS,
            )
            after = self.get_version()
            if result.returncode == 0:
                if before != after:
                    return True, f"Updated yt-dlp from {before} to {after}"
                return True, f"yt-dlp is already up to date: {after}"
            return False, f"yt-dlp update failed: {result.stderr[:300]}"
        except subprocess.TimeoutExpired:
            return False, "yt-dlp update timed out after 120 seconds"
        except Exception as exc:
            return False, f"yt-dlp update failed: {exc}"

    def download_latest(self) -> tuple[bool, str]:
        system = platform.system()
        url = _DOWNLOAD_URLS.get(system)
        if not url:
            return False, f"Unsupported system: {system}; manually place yt-dlp in {self.bin_dir}"

        self.bin_dir.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(url, timeout=300) as response:
                self.ytdlp_bin.write_bytes(response.read())
            if system != "Windows":
                self.ytdlp_bin.chmod(0o755)

            version = self.get_version()
            if version in {"unknown", "not installed"}:
                self.ytdlp_bin.unlink(missing_ok=True)
                return False, "Downloaded yt-dlp binary could not be executed"

            return True, f"Downloaded yt-dlp version {version}"
        except urllib.error.URLError as exc:
            return False, f"yt-dlp download failed due to a network error: {exc}"
        except Exception as exc:
            return False, f"yt-dlp download failed: {exc}"

    def ensure_available(self) -> bool:
        if self.is_installed():
            return True
        success, _message = self.download_latest()
        return success

    def get_status(self) -> dict:
        path = self.vendor_entrypoint if self.source_available() and not self.ytdlp_bin.exists() else self.ytdlp_bin
        runtime = "binary" if self.ytdlp_bin.exists() else "source" if self.source_available() else "missing"
        status = {
            "installed": self.is_installed(),
            "version": self.get_version(),
            "path": str(path),
        }
        if runtime != "missing":
            status["runtime"] = runtime
        return status
