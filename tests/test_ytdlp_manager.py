import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from modules.fetcher.ytdlp_manager import YtdlpManager


def _binary_name() -> str:
    suffix = ".exe" if __import__("platform").system() == "Windows" else ""
    return f"yt-dlp{suffix}"


class TestYtdlpManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bin_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _install_fake_binary(self):
        (self.bin_dir / _binary_name()).write_bytes(b"yt-dlp")

    def test_get_version_missing_and_installed(self):
        manager = YtdlpManager(self.bin_dir)
        self.assertEqual(manager.get_version(), "not installed")

        self._install_fake_binary()
        with patch("modules.fetcher.ytdlp_manager.subprocess.run", return_value=Mock(returncode=0, stdout="2026.01.01\n")):
            self.assertEqual(manager.get_version(), "2026.01.01")

        with patch("modules.fetcher.ytdlp_manager.subprocess.run", return_value=Mock(returncode=1, stdout="")):
            self.assertEqual(manager.get_version(), "unknown")

        with patch("modules.fetcher.ytdlp_manager.subprocess.run", side_effect=RuntimeError("boom")):
            self.assertEqual(manager.get_version(), "unknown")

    def test_update_downloads_when_missing(self):
        manager = YtdlpManager(self.bin_dir)
        with patch.object(manager, "download_latest", return_value=(True, "downloaded")):
            self.assertEqual(manager.update(), (True, "downloaded"))

    def test_update_reports_timeout(self):
        self._install_fake_binary()
        manager = YtdlpManager(self.bin_dir)
        with patch.object(manager, "get_version", return_value="old"):
            with patch("modules.fetcher.ytdlp_manager.subprocess.run", side_effect=subprocess.TimeoutExpired("yt-dlp", 120)):
                self.assertEqual(manager.update(), (False, "yt-dlp update timed out after 120 seconds"))

    def test_update_reports_changed_unchanged_failed_and_exception(self):
        self._install_fake_binary()
        manager = YtdlpManager(self.bin_dir)

        versions = iter(["old", "new"])
        with patch.object(manager, "get_version", side_effect=lambda: next(versions)):
            with patch("modules.fetcher.ytdlp_manager.subprocess.run", return_value=Mock(returncode=0, stderr="")):
                self.assertEqual(manager.update(), (True, "Updated yt-dlp from old to new"))

        with patch.object(manager, "get_version", return_value="same"):
            with patch("modules.fetcher.ytdlp_manager.subprocess.run", return_value=Mock(returncode=0, stderr="")):
                self.assertEqual(manager.update(), (True, "yt-dlp is already up to date: same"))

        with patch.object(manager, "get_version", return_value="old"):
            with patch(
                "modules.fetcher.ytdlp_manager.subprocess.run",
                return_value=Mock(returncode=1, stderr="bad update" * 50),
            ):
                ok, message = manager.update()
        self.assertFalse(ok)
        self.assertIn("yt-dlp update failed", message)
        self.assertLessEqual(len(message), len("yt-dlp update failed: ") + 300)

        with patch.object(manager, "get_version", return_value="old"):
            with patch("modules.fetcher.ytdlp_manager.subprocess.run", side_effect=RuntimeError("process failed")):
                self.assertEqual(manager.update(), (False, "yt-dlp update failed: process failed"))

    def test_download_latest_network_error(self):
        manager = YtdlpManager(self.bin_dir)
        with patch("modules.fetcher.ytdlp_manager.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            ok, message = manager.download_latest()

        self.assertFalse(ok)
        self.assertIn("network error", message)

    def test_download_latest_unsupported_system(self):
        manager = YtdlpManager(self.bin_dir)

        with patch("modules.fetcher.ytdlp_manager.platform.system", return_value="Haiku"):
            ok, message = manager.download_latest()

        self.assertFalse(ok)
        self.assertIn("Unsupported system: Haiku", message)

    def test_download_latest_success_writes_binary_and_sets_executable_on_posix(self):
        manager = YtdlpManager(self.bin_dir)
        chmod_calls = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"binary"

        with (
            patch("modules.fetcher.ytdlp_manager.platform.system", return_value="Linux"),
            patch("modules.fetcher.ytdlp_manager.urllib.request.urlopen", return_value=FakeResponse()) as urlopen,
            patch.object(manager, "get_version", return_value="2026.01.01"),
            patch.object(Path, "chmod", lambda self, mode: chmod_calls.append((self, mode))),
        ):
            ok, message = manager.download_latest()

        self.assertTrue(ok)
        self.assertEqual(message, "Downloaded yt-dlp version 2026.01.01")
        self.assertEqual(manager.ytdlp_bin.read_bytes(), b"binary")
        self.assertEqual(chmod_calls, [(manager.ytdlp_bin, 0o755)])
        urlopen.assert_called_once()

    def test_download_latest_removes_unusable_binary(self):
        manager = YtdlpManager(self.bin_dir)

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"broken"

        with (
            patch("modules.fetcher.ytdlp_manager.platform.system", return_value="Windows"),
            patch("modules.fetcher.ytdlp_manager.urllib.request.urlopen", return_value=FakeResponse()),
            patch.object(manager, "get_version", return_value="unknown"),
        ):
            ok, message = manager.download_latest()

        self.assertFalse(ok)
        self.assertEqual(message, "Downloaded yt-dlp binary could not be executed")
        self.assertFalse(manager.ytdlp_bin.exists())

    def test_download_latest_reports_generic_failure(self):
        manager = YtdlpManager(self.bin_dir)

        with (
            patch("modules.fetcher.ytdlp_manager.platform.system", return_value="Windows"),
            patch("modules.fetcher.ytdlp_manager.urllib.request.urlopen", side_effect=RuntimeError("disk full")),
        ):
            ok, message = manager.download_latest()

        self.assertFalse(ok)
        self.assertEqual(message, "yt-dlp download failed: disk full")

    def test_ensure_available(self):
        manager = YtdlpManager(self.bin_dir)
        with patch.object(manager, "download_latest", return_value=(True, "downloaded")):
            self.assertTrue(manager.ensure_available())

        self._install_fake_binary()
        self.assertTrue(manager.ensure_available())

    def test_ensure_available_false_and_status(self):
        manager = YtdlpManager(self.bin_dir)
        with patch.object(manager, "download_latest", return_value=(False, "failed")):
            self.assertFalse(manager.ensure_available())

        with patch.object(manager, "is_installed", return_value=True), patch.object(manager, "get_version", return_value="1.0"):
            self.assertEqual(
                manager.get_status(),
                {"installed": True, "version": "1.0", "path": str(manager.ytdlp_bin)},
            )


if __name__ == "__main__":
    unittest.main()
