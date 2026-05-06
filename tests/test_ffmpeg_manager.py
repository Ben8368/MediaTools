import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.ffmpeg import FFmpegManager


def _binary_names() -> tuple[str, str]:
    suffix = ".exe" if __import__("platform").system() == "Windows" else ""
    return f"ffmpeg{suffix}", f"ffprobe{suffix}"


class TestFFmpegManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bin_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _install_fake_binaries(self):
        ffmpeg_name, ffprobe_name = _binary_names()
        (self.bin_dir / ffmpeg_name).write_bytes(b"ffmpeg")
        (self.bin_dir / ffprobe_name).write_bytes(b"ffprobe")

    def test_unavailable_manager_reports_missing(self):
        manager = FFmpegManager(self.bin_dir)

        self.assertFalse(manager.is_available())
        self.assertEqual(manager.get_version(), "not installed")
        self.assertEqual(manager.get_ffmpeg_location(), "")
        self.assertFalse(manager.get_info()["installed"])
        with self.assertRaises(RuntimeError):
            manager.run(["-version"])

    def test_available_manager_paths_and_info(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)

        with patch("core.ffmpeg.subprocess.run", return_value=Mock(stdout="ffmpeg version 7.0\n", returncode=0)):
            info = manager.get_info()
            version = manager.get_version()

        self.assertTrue(manager.is_available())
        self.assertEqual(version, "7.0")
        self.assertEqual(manager.get_ffmpeg_location(), str(self.bin_dir))
        self.assertTrue(info["installed"])

    def test_get_duration_parses_ffprobe_output(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="12.5\n", stderr="")

        with patch("core.ffmpeg.subprocess.run", return_value=completed):
            self.assertEqual(manager.get_duration("video.mp4"), 12.5)

    def test_get_duration_returns_none_on_bad_output(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="bad\n", stderr="")

        with patch("core.ffmpeg.subprocess.run", return_value=completed):
            self.assertIsNone(manager.get_duration("video.mp4"))

    def test_paths_run_and_version_error_branches(self):
        manager = FFmpegManager(self.bin_dir)
        self.assertEqual(manager.get_ffmpeg_path(), "")
        self.assertEqual(manager.get_ffprobe_path(), "")

        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        self.assertTrue(manager.get_ffmpeg_path().endswith(_binary_names()[0]))
        self.assertTrue(manager.get_ffprobe_path().endswith(_binary_names()[1]))

        with patch("core.ffmpeg.subprocess.run", side_effect=RuntimeError("boom")):
            self.assertEqual(manager.get_version(), "unknown")

        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with patch("core.ffmpeg.subprocess.run", return_value=completed) as mock_run:
            result = manager.run(["-version"], capture_output=True)
        self.assertIs(result, completed)
        self.assertEqual(mock_run.call_args.args[0], [str(manager.ffmpeg_bin), "-version"])
        self.assertEqual(mock_run.call_args.kwargs["timeout"], 3600)

    def test_get_duration_unavailable_nonzero_and_exception(self):
        manager = FFmpegManager(self.bin_dir)
        self.assertIsNone(manager.get_duration("video.mp4"))

        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        with patch("core.ffmpeg.subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="12.5", stderr="bad")):
            self.assertIsNone(manager.get_duration("video.mp4"))

        with patch("core.ffmpeg.subprocess.run", side_effect=OSError("denied")):
            self.assertIsNone(manager.get_duration("video.mp4"))

    def test_run_with_progress_rejects_missing_binary(self):
        manager = FFmpegManager(self.bin_dir)
        with self.assertRaises(RuntimeError):
            manager.run_with_progress(["-i", "in.mp4", "out.mp4"])

    def test_run_with_progress_without_duration_reads_all_stderr(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)

        class FakePipe:
            def readlines(self):
                return ["line one\n", "line two\n"]

            def read(self):
                return "stdout text"

        class FakeProcess:
            stdout = FakePipe()
            stderr = FakePipe()
            returncode = 2

            def wait(self, timeout=None):
                return self.returncode

        with patch("core.ffmpeg.subprocess.Popen", return_value=FakeProcess()) as mock_popen:
            result = manager.run_with_progress(["-version"])

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "stdout text")
        self.assertEqual(result.stderr, "line one\nline two\n")
        self.assertEqual(mock_popen.call_args.args[0], [str(manager.ffmpeg_bin), "-version"])

    def test_run_with_progress_parses_time_lines(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        progress_values = []

        class FakeStderr:
            def __init__(self):
                self.lines = iter([
                    "frame=1 time=00:00:05.00 bitrate=1kbits/s\n",
                    "frame=2 time=00:00:12.00 bitrate=1kbits/s\n",
                    "",
                ])

            def readline(self):
                return next(self.lines)

        class FakeStdout:
            def read(self):
                return ""

        class FakeProcess:
            stdout = FakeStdout()
            stderr = FakeStderr()
            returncode = 0

            def wait(self, timeout=None):
                return self.returncode

        with (
            patch.object(manager, "get_duration", return_value=10.0),
            patch("core.ffmpeg.subprocess.Popen", return_value=FakeProcess()),
        ):
            result = manager.run_with_progress(
                ["-i", "input.mp4", "out.mp4"],
                progress_callback=progress_values.append,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(progress_values, [50.0, 99.0])
        self.assertIn("time=00:00:12.00", result.stderr)

    def test_run_with_progress_cancel_terminates_process(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        calls = []

        class FakeStderr:
            def readline(self):
                return "frame=1 time=00:00:01.00 bitrate=1kbits/s\n"

        class FakeStdout:
            def read(self):
                return ""

        class FakeProcess:
            stdout = FakeStdout()
            stderr = FakeStderr()
            returncode = 0

            def terminate(self):
                calls.append("terminate")

            def wait(self, timeout=None):
                calls.append(("wait", timeout))
                return 0

            def kill(self):
                calls.append("kill")

        with (
            patch.object(manager, "get_duration", return_value=10.0),
            patch("core.ffmpeg.subprocess.Popen", return_value=FakeProcess()),
        ):
            result = manager.run_with_progress(
                ["-i", "input.mp4", "out.mp4"],
                progress_callback=lambda _value: None,
                cancel_check=lambda: True,
            )

        self.assertEqual(result.returncode, -1)
        self.assertEqual(calls, ["terminate", ("wait", 5)])

    def test_run_with_progress_cancel_kills_after_timeout(self):
        self._install_fake_binaries()
        manager = FFmpegManager(self.bin_dir)
        calls = []

        class FakeStderr:
            def readline(self):
                return "frame=1 time=00:00:01.00 bitrate=1kbits/s\n"

        class FakeStdout:
            def read(self):
                return ""

        class FakeProcess:
            stdout = FakeStdout()
            stderr = FakeStderr()
            returncode = 0
            wait_calls = 0

            def terminate(self):
                calls.append("terminate")

            def wait(self, timeout=None):
                self.wait_calls += 1
                calls.append(("wait", timeout))
                if self.wait_calls == 1:
                    raise subprocess.TimeoutExpired("ffmpeg", timeout)
                return 0

            def kill(self):
                calls.append("kill")

        with (
            patch.object(manager, "get_duration", return_value=10.0),
            patch("core.ffmpeg.subprocess.Popen", return_value=FakeProcess()),
        ):
            result = manager.run_with_progress(
                ["-i", "input.mp4", "out.mp4"],
                progress_callback=lambda _value: None,
                cancel_check=lambda: True,
            )

        self.assertEqual(result.returncode, -1)
        self.assertEqual(calls, ["terminate", ("wait", 5), "kill", ("wait", None)])


if __name__ == "__main__":
    unittest.main()
