import subprocess

from services import filebrowser_runtime as runtime


def test_filebrowser_loopback_detection():
    assert runtime._is_loopback_host("127.0.0.1")
    assert runtime._is_loopback_host("localhost")
    assert not runtime._is_loopback_host("0.0.0.0")
    assert not runtime._is_loopback_host("192.168.1.5")


def test_filebrowser_status_masks_dead_pid(tmp_path, monkeypatch):
    pid_file = tmp_path / "filebrowser.pid"
    pid_file.write_text("999999", encoding="utf-8")
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", tmp_path / "filebrowser.log")
    monkeypatch.setattr(runtime, "FILEBROWSER_BINARY", tmp_path / "filebrowser.exe")
    monkeypatch.setattr(runtime, "FILEBROWSER_DB_PATH", tmp_path / "filebrowser.db")
    monkeypatch.setattr(runtime, "WORKSPACE_ALLOWED_ROOTS", [tmp_path])
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    monkeypatch.setattr(runtime, "_process_exists", lambda _pid: False)

    status = runtime.get_filebrowser_status()

    assert status["running"] is False
    assert status["pid"] is None
    assert status["root"] == str(tmp_path)


def test_filebrowser_health_and_pid_helpers(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "FILEBROWSER_BASE_URL", "http://127.0.0.1:9999/")
    assert runtime._base_url() == "http://127.0.0.1:9999"
    assert runtime._health_url() == "http://127.0.0.1:9999/health"

    monkeypatch.setattr(runtime.requests, "get", lambda *_args, **_kwargs: type("Resp", (), {"status_code": 200})())
    assert runtime.is_filebrowser_running()

    def raise_request(*_args, **_kwargs):
        raise runtime.requests.RequestException("offline")

    monkeypatch.setattr(runtime.requests, "get", raise_request)
    assert runtime.is_filebrowser_running() is False

    pid_file = tmp_path / "filebrowser.pid"
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    assert runtime._read_pid() is None
    pid_file.write_text("not-int", encoding="utf-8")
    assert runtime._read_pid() is None
    runtime._write_pid(321)
    assert runtime._read_pid() == 321
    runtime._clear_pid()
    assert not pid_file.exists()


def test_process_exists_handles_invalid_and_os_errors(monkeypatch):
    assert runtime._process_exists(0) is False

    monkeypatch.setattr(runtime.os, "kill", lambda *_args: None)
    assert runtime._process_exists(123) is True

    def missing_process(*_args):
        raise OSError("missing")

    monkeypatch.setattr(runtime.os, "kill", missing_process)
    assert runtime._process_exists(123) is False


def test_start_filebrowser_rejects_non_loopback(monkeypatch):
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    monkeypatch.setattr(runtime, "FILEBROWSER_HOST", "0.0.0.0")

    result = runtime.start_filebrowser_service()

    assert result["ok"] is False
    assert "127.0.0.1" in result["message"]


def test_start_filebrowser_rejects_missing_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    monkeypatch.setattr(runtime, "FILEBROWSER_HOST", "127.0.0.1")
    monkeypatch.setattr(runtime, "FILEBROWSER_BINARY", tmp_path / "missing.exe")

    result = runtime.start_filebrowser_service()

    assert result["ok"] is False
    assert "binary" in result["message"].lower()


def test_start_filebrowser_returns_when_already_running(monkeypatch):
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: True)

    result = runtime.start_filebrowser_service()

    assert result["ok"] is True
    assert "已在运行" in result["message"]


def test_start_filebrowser_success_writes_pid_and_command(tmp_path, monkeypatch):
    binary = tmp_path / "filebrowser.exe"
    binary.write_bytes(b"exe")
    log_file = tmp_path / "filebrowser.log"
    pid_file = tmp_path / "filebrowser.pid"
    db_file = tmp_path / "filebrowser.db"
    root = tmp_path / "root"
    root.mkdir()
    calls = {"health": 0}
    popen_calls = []

    class FakeProcess:
        pid = 456

        def poll(self):
            return None

    def fake_running(*_args, **_kwargs):
        calls["health"] += 1
        return calls["health"] >= 2

    def fake_popen(cmd, **kwargs):
        popen_calls.append((cmd, kwargs))
        return FakeProcess()

    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", log_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_BINARY", binary)
    monkeypatch.setattr(runtime, "FILEBROWSER_DB_PATH", db_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_HOST", "127.0.0.1")
    monkeypatch.setattr(runtime, "FILEBROWSER_PORT", 7777)
    monkeypatch.setattr(runtime, "FILEBROWSER_BASE_URL", "http://127.0.0.1:7777")
    monkeypatch.setattr(runtime, "WORKSPACE_ALLOWED_ROOTS", [root])
    monkeypatch.setattr(runtime, "BASE_DIR", tmp_path)
    monkeypatch.setattr(runtime, "is_filebrowser_running", fake_running)
    monkeypatch.setattr(runtime.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runtime.time, "sleep", lambda *_args: None)

    result = runtime.start_filebrowser_service(wait_seconds=1)

    assert result["ok"] is True
    assert "PID 456" in result["message"]
    assert pid_file.read_text(encoding="utf-8") == "456"
    cmd = popen_calls[0][0]
    assert cmd[:2] == [str(binary), "--address"]
    assert "--noauth" in cmd
    assert str(root) in cmd


def test_start_filebrowser_reports_exited_process(tmp_path, monkeypatch):
    binary = tmp_path / "filebrowser.exe"
    binary.write_bytes(b"exe")
    pid_file = tmp_path / "filebrowser.pid"
    log_file = tmp_path / "filebrowser.log"

    class ExitedProcess:
        pid = 999

        def poll(self):
            return 1

    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", log_file)
    monkeypatch.setattr(runtime, "FILEBROWSER_BINARY", binary)
    monkeypatch.setattr(runtime, "FILEBROWSER_HOST", "127.0.0.1")
    monkeypatch.setattr(runtime, "WORKSPACE_ALLOWED_ROOTS", [tmp_path])
    monkeypatch.setattr(runtime, "BASE_DIR", tmp_path)
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *_args, **_kwargs: ExitedProcess())

    result = runtime.start_filebrowser_service(wait_seconds=0)

    assert result["ok"] is False
    assert "进程已退出" in result["message"]
    assert not pid_file.exists()


def test_start_filebrowser_reports_timeout(tmp_path, monkeypatch):
    binary = tmp_path / "filebrowser.exe"
    binary.write_bytes(b"exe")

    class RunningProcess:
        pid = 888

        def poll(self):
            return None

    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", tmp_path / "filebrowser.pid")
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", tmp_path / "filebrowser.log")
    monkeypatch.setattr(runtime, "FILEBROWSER_BINARY", binary)
    monkeypatch.setattr(runtime, "FILEBROWSER_HOST", "127.0.0.1")
    monkeypatch.setattr(runtime, "WORKSPACE_ALLOWED_ROOTS", [tmp_path])
    monkeypatch.setattr(runtime, "BASE_DIR", tmp_path)
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *_args, **_kwargs: RunningProcess())

    result = runtime.start_filebrowser_service(wait_seconds=0)

    assert result["ok"] is False
    assert "启动超时" in result["message"]


def test_stop_filebrowser_uses_pid_and_clears_file(tmp_path, monkeypatch):
    pid_file = tmp_path / "filebrowser.pid"
    pid_file.write_text("123", encoding="utf-8")
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "_process_exists", lambda pid: pid == 123)
    monkeypatch.setattr(runtime, "_stop_pid", lambda _pid: None)
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)

    result = runtime.stop_filebrowser_service()

    assert result["ok"] is True
    assert not pid_file.exists()


def test_stop_filebrowser_falls_back_to_process_name(tmp_path, monkeypatch):
    pid_file = tmp_path / "filebrowser.pid"
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: True)
    calls = []
    monkeypatch.setattr(runtime.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    result = runtime.stop_filebrowser_service()

    assert result["ok"] is True
    assert calls


def test_stop_filebrowser_reports_stop_error(tmp_path, monkeypatch):
    pid_file = tmp_path / "filebrowser.pid"
    pid_file.write_text("123", encoding="utf-8")
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "_process_exists", lambda _pid: True)

    def fail_stop(_pid: int) -> None:
        raise subprocess.SubprocessError("boom")

    monkeypatch.setattr(runtime, "_stop_pid", fail_stop)

    result = runtime.stop_filebrowser_service()

    assert result["ok"] is False
    assert "boom" in result["message"]


def test_stop_filebrowser_timeout_and_not_running_paths(tmp_path, monkeypatch):
    pid_file = tmp_path / "filebrowser.pid"
    pid_file.write_text("123", encoding="utf-8")
    monkeypatch.setattr(runtime, "FILEBROWSER_PID_FILE", pid_file)
    monkeypatch.setattr(runtime, "_process_exists", lambda _pid: True)
    monkeypatch.setattr(runtime, "_stop_pid", lambda _pid: None)
    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: True)
    monkeypatch.setattr(runtime.time, "sleep", lambda *_args: None)
    times = iter([0, 9])
    monkeypatch.setattr(runtime.time, "time", lambda: next(times))

    result = runtime.stop_filebrowser_service()

    assert result["ok"] is False
    assert "可能仍未完全退出" in result["message"]
    assert not pid_file.exists()

    monkeypatch.setattr(runtime, "is_filebrowser_running", lambda *_, **__: False)
    result = runtime.stop_filebrowser_service()
    assert result == {"ok": True, "message": "filebrowser 当前未运行"}


def test_read_filebrowser_log_tail(tmp_path, monkeypatch):
    log_file = tmp_path / "filebrowser.log"
    log_file.write_text("one\ntwo\nthree\n", encoding="utf-8")
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", log_file)

    assert runtime.read_filebrowser_log(2) == "two\nthree"


def test_read_filebrowser_log_missing_empty_and_error(tmp_path, monkeypatch):
    log_file = tmp_path / "filebrowser.log"
    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", log_file)

    assert runtime.read_filebrowser_log() == "暂无日志"
    log_file.write_text("", encoding="utf-8")
    assert runtime.read_filebrowser_log() == "暂无日志"

    class BadPath:
        def exists(self):
            return True

        def read_text(self, **_kwargs):
            raise OSError("denied")

    monkeypatch.setattr(runtime, "FILEBROWSER_LOG_FILE", BadPath())
    assert runtime.read_filebrowser_log().startswith("读取日志失败: denied")


def test_restart_filebrowser_delegates_stop_then_start(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime, "stop_filebrowser_service", lambda: calls.append("stop") or {"ok": True})
    monkeypatch.setattr(runtime, "start_filebrowser_service", lambda: calls.append("start") or {"ok": True, "message": "started"})
    monkeypatch.setattr(runtime.time, "sleep", lambda *_args: calls.append("sleep"))

    result = runtime.restart_filebrowser_service()

    assert result == {"ok": True, "message": "started"}
    assert calls == ["stop", "sleep", "start"]
