"""Tests for unlock-music CLI wrapper."""

import subprocess
from pathlib import Path

from modules.decryptor import wrapper as decryptor_wrapper


def make_binary(tmp_path: Path) -> Path:
    binary = tmp_path / "um-cli.exe"
    binary.write_bytes(b"exe")
    return binary


def test_get_umcli_bin_uses_platform_suffix(monkeypatch):
    monkeypatch.setattr(decryptor_wrapper.platform, "system", lambda: "Windows")
    assert decryptor_wrapper._get_umcli_bin().name == "um-cli.exe"

    monkeypatch.setattr(decryptor_wrapper.platform, "system", lambda: "Linux")
    assert decryptor_wrapper._get_umcli_bin().name == "um-cli"


def test_wrapper_availability_and_missing_binary_message(tmp_path):
    missing = tmp_path / "missing-um-cli.exe"
    wrapper = decryptor_wrapper.DecryptorWrapper(missing)

    assert wrapper.is_available() is False
    result = wrapper.decrypt("song.ncm")

    assert result["success"] is False
    assert str(missing) in result["error"]
    assert wrapper.decrypt_batch("album")["success"] is False
    assert wrapper.get_version() == "未安装"


def test_decrypt_builds_command_and_returns_success(tmp_path, monkeypatch):
    binary = make_binary(tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(decryptor_wrapper.subprocess, "run", fake_run)
    wrapper = decryptor_wrapper.DecryptorWrapper(binary)

    result = wrapper.decrypt("D:\\Music\\song.ncm", "D:\\Out", remove_source=True)

    assert result == {"success": True, "output": "ok", "error": ""}
    cmd, kwargs = calls[0]
    assert cmd == [str(binary), "-i", "D:\\Music\\song.ncm", "-o", "D:\\Out", "--remove-source"]
    assert kwargs["timeout"] == 300
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"


def test_decrypt_reports_nonzero_stderr_timeout_and_exception(tmp_path, monkeypatch):
    binary = make_binary(tmp_path)
    wrapper = decryptor_wrapper.DecryptorWrapper(binary)

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 2, stdout="partial", stderr="bad format"),
    )
    failed = wrapper.decrypt("song.ncm")
    assert failed == {"success": False, "output": "partial", "error": "bad format"}

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("um-cli", 300)),
    )
    assert wrapper.decrypt("song.ncm") == {"success": False, "output": "", "error": "解密超时（5分钟）"}

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert wrapper.decrypt("song.ncm") == {"success": False, "output": "", "error": "boom"}


def test_decrypt_batch_builds_command_and_handles_errors(tmp_path, monkeypatch):
    binary = make_binary(tmp_path)
    wrapper = decryptor_wrapper.DecryptorWrapper(binary)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="batch ok", stderr="")

    monkeypatch.setattr(decryptor_wrapper.subprocess, "run", fake_run)
    result = wrapper.decrypt_batch("D:\\Album", "D:\\Out", remove_source=True)

    assert result == {"success": True, "output": "batch ok", "error": ""}
    assert calls[0][0] == [str(binary), "-i", "D:\\Album", "-o", "D:\\Out", "--remove-source"]
    assert calls[0][1]["timeout"] == 1800

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("um-cli", 1800)),
    )
    assert wrapper.decrypt_batch("D:\\Album") == {"success": False, "output": "", "error": "批量解密超时（30分钟）"}

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    assert wrapper.decrypt_batch("D:\\Album") == {"success": False, "output": "", "error": "denied"}


def test_get_version_success_unknown_and_exception(tmp_path, monkeypatch):
    binary = make_binary(tmp_path)
    wrapper = decryptor_wrapper.DecryptorWrapper(binary)

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="um-cli 1.2.3\n", stderr=""),
    )
    assert wrapper.get_version() == "um-cli 1.2.3"

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="bad"),
    )
    assert wrapper.get_version() == "未知"

    monkeypatch.setattr(
        decryptor_wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert wrapper.get_version() == "未知"
