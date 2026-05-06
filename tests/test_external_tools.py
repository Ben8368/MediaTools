"""Tests for stable external-tool adapters."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from adapters.external_tools import FFmpegAdapter, UmcliAdapter, YtdlpAdapter
from adapters.photoshop_runtime import PhotoshopAutomationAdapter


class TestExternalToolAdapters(unittest.TestCase):
    def test_photoshop_adapter_discovers_nested_runtime_source(self):
        adapter = PhotoshopAutomationAdapter()
        self.assertTrue(adapter.root.as_posix().endswith("vendor/adobe/photoshop/com"))
        if adapter.root.exists():
            self.assertTrue((adapter.src_dir / "ps_connector.py").exists())
            self.assertTrue(adapter.get_status()["runtime_modules"])

    def test_ytdlp_adapter_delegates_manager_and_patches_command(self):
        manager = Mock()
        manager.bin_dir = Path("bin")
        manager.ytdlp_bin = Path("bin/yt-dlp.exe")
        manager.is_installed.return_value = True
        manager.get_status.return_value = {"installed": True}
        manager.get_version.return_value = "2026.01.01"
        manager.update.return_value = (True, "updated")
        manager.download_latest.return_value = (True, "downloaded")

        adapter = YtdlpAdapter(manager)
        with patch("adapters.external_tools.apply_command_patches", return_value=["patched"]):
            self.assertEqual(adapter.build_command(["--version"], {"operation": "status"}), ["patched"])
        with patch("adapters.external_tools.subprocess.run") as mock_run:
            adapter.run(["--version"], context={"operation": "status"}, capture_output=True)

        self.assertTrue(adapter.is_available())
        self.assertEqual(adapter.get_status(), {"installed": True})
        self.assertEqual(adapter.get_version(), "2026.01.01")
        self.assertEqual(adapter.update(), (True, "updated"))
        self.assertEqual(adapter.download_latest(), (True, "downloaded"))
        self.assertTrue(mock_run.called)

    def test_ffmpeg_adapter_delegates_and_rejects_missing_binary(self):
        manager = Mock()
        manager.bin_dir = Path("bin")
        manager.ffmpeg_bin = Path("bin/ffmpeg.exe")
        manager.ffprobe_bin = Path("bin/ffprobe.exe")
        manager.is_available.return_value = True
        manager.get_info.return_value = {"installed": True}
        manager.get_version.return_value = "7.0"
        manager.get_ffmpeg_location.return_value = "bin"

        adapter = FFmpegAdapter(manager)
        with patch("adapters.external_tools.apply_command_patches", return_value=["ffmpeg", "-version"]):
            self.assertEqual(adapter.build_command(["-version"], {}), ["ffmpeg", "-version"])
        with patch("adapters.external_tools.subprocess.run") as mock_run:
            adapter.run(["-version"], capture_output=True)

        self.assertTrue(adapter.is_available())
        self.assertEqual(adapter.get_info(), {"installed": True})
        self.assertEqual(adapter.get_version(), "7.0")
        self.assertEqual(adapter.get_ffmpeg_location(), "bin")
        self.assertTrue(mock_run.called)

        manager.is_available.return_value = False
        with self.assertRaises(RuntimeError):
            adapter.run(["-version"])

    def test_ffmpeg_adapter_run_with_progress_delegates_and_rejects_missing_binary(self):
        manager = Mock()
        manager.bin_dir = Path("bin")
        manager.ffmpeg_bin = Path("bin/ffmpeg.exe")
        manager.ffprobe_bin = Path("bin/ffprobe.exe")
        manager.is_available.return_value = True
        manager.run_with_progress.return_value = subprocess.CompletedProcess(["ffmpeg"], 0, "ok", "")

        adapter = FFmpegAdapter(manager)
        progress_callback = Mock()
        cancel_check = Mock(return_value=False)
        result = adapter.run_with_progress(
            ["-i", "in.mp4"],
            progress_callback=progress_callback,
            cancel_check=cancel_check,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0)
        manager.run_with_progress.assert_called_once_with(
            ["-i", "in.mp4"],
            progress_callback=progress_callback,
            cancel_check=cancel_check,
            timeout=30,
        )

        manager.is_available.return_value = False
        with self.assertRaises(RuntimeError):
            adapter.run_with_progress(["-version"])

    def test_umcli_adapter_status_and_command_building(self):
        wrapper = Mock()
        wrapper.umcli_bin = Path("bin/um-cli.exe")
        wrapper.is_available.return_value = True
        wrapper.get_version.return_value = "1.0"

        adapter = UmcliAdapter(wrapper)
        with patch("adapters.external_tools.apply_command_patches", return_value=["patched"]):
            self.assertEqual(adapter.build_command(["-i", "song.ncm"], {}), ["patched"])
        with patch("adapters.external_tools.subprocess.run") as mock_run:
            adapter.run(["--help"], capture_output=True)

        self.assertTrue(adapter.is_available())
        self.assertEqual(adapter.get_version(), "1.0")
        self.assertEqual(adapter.get_status()["installed"], True)
        self.assertTrue(mock_run.called)

    def test_umcli_decrypt_success_failure_and_timeout(self):
        wrapper = SimpleNamespace(umcli_bin=Path("bin/um-cli.exe"), is_available=lambda: True, get_version=lambda: "1.0")
        adapter = UmcliAdapter(wrapper)

        with patch.object(adapter, "run", return_value=SimpleNamespace(returncode=0, stdout="ok", stderr="")):
            result = adapter.decrypt("song.ncm", "out", remove_source=True)
        self.assertEqual(result, {"success": True, "output": "ok", "error": ""})

        with patch.object(adapter, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="bad")):
            result = adapter.decrypt_batch("input", "out")
        self.assertEqual(result, {"success": False, "output": "", "error": "bad"})

        with patch.object(adapter, "run", side_effect=subprocess.TimeoutExpired("um-cli", 1)):
            self.assertFalse(adapter.decrypt("song.ncm")["success"])
            self.assertFalse(adapter.decrypt_batch("input")["success"])

        with patch.object(adapter, "run", side_effect=RuntimeError("boom")):
            self.assertEqual(adapter.decrypt("song.ncm")["error"], "boom")
            self.assertEqual(adapter.decrypt_batch("input")["error"], "boom")

    def test_umcli_run_with_cancel_returns_completed_process_when_not_cancelled(self):
        wrapper = SimpleNamespace(umcli_bin=Path("bin/um-cli.exe"), is_available=lambda: True, get_version=lambda: "1.0")
        adapter = UmcliAdapter(wrapper)
        process = Mock()
        process.poll.return_value = 0
        process.returncode = 0
        process.communicate.return_value = ("stdout", "stderr")

        with patch.object(adapter, "build_command", return_value=["um-cli", "--help"]), patch(
            "adapters.external_tools.subprocess.Popen",
            return_value=process,
        ) as popen:
            result = adapter.run_with_cancel(["--help"], timeout=10)

        popen.assert_called_once()
        process.communicate.assert_called_once_with()
        self.assertEqual(result.args, ["um-cli", "--help"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "stdout")
        self.assertEqual(result.stderr, "stderr")

    def test_umcli_run_with_cancel_terminates_and_kills_stubborn_process(self):
        wrapper = SimpleNamespace(umcli_bin=Path("bin/um-cli.exe"), is_available=lambda: True, get_version=lambda: "1.0")
        adapter = UmcliAdapter(wrapper)
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("um-cli", 5), 0]
        process.stdout.read.return_value = "partial stdout"
        process.stderr.read.return_value = "partial stderr"

        with patch.object(adapter, "build_command", return_value=["um-cli", "-i", "song.ncm"]), patch(
            "adapters.external_tools.subprocess.Popen",
            return_value=process,
        ), patch("adapters.external_tools.time.sleep") as sleep:
            result = adapter.run_with_cancel(["-i", "song.ncm"], cancel_check=lambda: True)

        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        sleep.assert_not_called()
        self.assertEqual(result.returncode, -1)
        self.assertEqual(result.stdout, "partial stdout")
        self.assertEqual(result.stderr, "partial stderr")

    def test_umcli_decrypt_and_batch_report_cancelled_results(self):
        wrapper = SimpleNamespace(umcli_bin=Path("bin/um-cli.exe"), is_available=lambda: True, get_version=lambda: "1.0")
        adapter = UmcliAdapter(wrapper)
        cancelled = subprocess.CompletedProcess(["um-cli"], -1, "", "")

        with patch.object(adapter, "run_with_cancel", return_value=cancelled) as run_with_cancel:
            decrypt_result = adapter.decrypt("song.ncm", cancel_check=lambda: True)
            batch_result = adapter.decrypt_batch("album", "out", remove_source=True, cancel_check=lambda: True)

        self.assertEqual(decrypt_result, {"success": False, "output": "", "error": "Task cancelled"})
        self.assertEqual(batch_result, {"success": False, "output": "", "error": "Task cancelled"})
        self.assertEqual(run_with_cancel.call_count, 2)
