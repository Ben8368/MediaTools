"""After Effects 服务层单元测试（COM 方案）"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.adobe.after_effects.service import (
    _ae_root,
    _build_ticket_from_layers,
    _load_ticket_payload,
    _save_ticket_payload,
    _should_execute_task,
    _ticket_summary,
    delete_ae_ticket,
    get_ae_status,
    get_ae_ticket,
    import_ae_ticket,
    list_ae_fonts,
    list_ae_tickets,
    save_ae_ticket,
    scan_ae_project,
    start_ae_ticket_execution,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> dict:
    for folder in ("manifests", "exports"):
        (tmp_path / folder).mkdir()
    return {
        "project_root": str(tmp_path),
        "manifests_dir": str(tmp_path / "manifests"),
        "exports_dir": str(tmp_path / "exports"),
    }


@pytest.fixture()
def mock_runtime():
    """Mock AE COM runtime，避免测试时需要真实 AE 安装"""
    mock_connector_cls = MagicMock()
    mock_connector = MagicMock()
    mock_connector_cls.return_value = mock_connector

    # scan 返回两个文本图层
    mock_connector.scan_project_for_text_layers.return_value = [
        {
            "comp_name": "Main Comp",
            "comp_index": 1,
            "layer_name": "Title",
            "layer_index": 1,
            "original_text": "Hello World",
            "source_font": "Arial-Regular",
            "font_size": 48.0,
            "tracking": 0,
        },
        {
            "comp_name": "Main Comp",
            "comp_index": 1,
            "layer_name": "Subtitle",
            "layer_index": 2,
            "original_text": "Subtitle text",
            "source_font": "Arial-Regular",
            "font_size": 24.0,
            "tracking": 0,
        },
    ]

    # apply_text_changes 返回成功
    mock_connector.apply_text_changes.return_value = [
        {"comp_index": 1, "layer_index": 1, "ok": True, "msg": "ok"},
        {"comp_index": 1, "layer_index": 2, "ok": True, "msg": "ok"},
    ]

    mock_pythoncom = MagicMock()

    runtime = {
        "AfterEffectsConnector": mock_connector_cls,
        "pythoncom": mock_pythoncom,
    }
    return runtime, mock_connector


@pytest.fixture()
def sample_ticket(tmp_workspace: dict, mock_runtime) -> dict:
    """通过 mock runtime 扫描生成工单"""
    runtime, _ = mock_runtime
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = scan_ae_project(project_path="/fake/project.aep", workspace=tmp_workspace)
    return result


# ---------------------------------------------------------------------------
# 目录管理
# ---------------------------------------------------------------------------

def test_ae_root_creates_directory(tmp_workspace: dict) -> None:
    root = _ae_root("manifests", tmp_workspace)
    assert root.exists()
    assert root.name == "after_effects"


# ---------------------------------------------------------------------------
# 工单 CRUD
# ---------------------------------------------------------------------------

def test_load_save_ticket_payload(tmp_path: Path) -> None:
    path = tmp_path / "ticket.json"
    payload = {"meta": {"source_project": "test.aep"}, "tasks": [{"layer_id": "1:1", "status": "pending"}]}
    _save_ticket_payload(path, payload)
    loaded = _load_ticket_payload(path)
    assert loaded["meta"]["source_project"] == "test.aep"
    assert len(loaded["tasks"]) == 1


def test_load_ticket_payload_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        _load_ticket_payload(path)


def test_load_ticket_payload_defaults(tmp_path: Path) -> None:
    path = tmp_path / "minimal.json"
    path.write_text("{}", encoding="utf-8")
    payload = _load_ticket_payload(path)
    assert payload["meta"] == {}
    assert payload["tasks"] == []


def test_ticket_summary(tmp_path: Path) -> None:
    path = tmp_path / "abc123.json"
    payload = {
        "meta": {"source_project": "test.aep", "created_at": "2024-01-01"},
        "tasks": [{"status": "confirmed"}, {"status": "pending"}],
    }
    _save_ticket_payload(path, payload)
    summary = _ticket_summary(path, payload)
    assert summary["ticket_id"] == "abc123"
    assert summary["task_count"] == 2
    assert summary["confirmed_count"] == 1


# ---------------------------------------------------------------------------
# get_ae_status
# ---------------------------------------------------------------------------

def test_get_ae_status_structure(tmp_workspace: dict) -> None:
    status = get_ae_status(tmp_workspace)
    assert "available" in status
    assert status["platform"] == "com"
    assert "tickets_dir" in status
    assert "exports_dir" in status
    assert isinstance(status["running_executions"], int)


# ---------------------------------------------------------------------------
# list / get / save tickets
# ---------------------------------------------------------------------------

def test_list_ae_tickets_empty(tmp_workspace: dict) -> None:
    assert list_ae_tickets(tmp_workspace) == []


def test_save_and_list_ae_ticket(tmp_workspace: dict) -> None:
    payload = {"meta": {"source_project": "test.aep"}, "tasks": []}
    result = save_ae_ticket("ticket-001", payload, tmp_workspace)
    assert result["ticket_id"] == "ticket-001"
    tickets = list_ae_tickets(tmp_workspace)
    assert len(tickets) == 1
    assert tickets[0]["ticket_id"] == "ticket-001"


def test_import_ae_ticket_file(tmp_workspace: dict, tmp_path: Path) -> None:
    source = tmp_path / "external-ae-ticket.json"
    source.write_text(json.dumps({"meta": {"source_project": "external.aep"}, "tasks": []}), encoding="utf-8")
    result = import_ae_ticket(str(source), tmp_workspace, "imported-ae")
    assert result["ticket_id"] == "imported-ae"
    assert result["imported_from"] == str(source.resolve())
    assert get_ae_ticket("imported-ae", tmp_workspace)["ticket"]["meta"]["source_project"] == "external.aep"


def test_delete_ae_ticket(tmp_workspace: dict) -> None:
    payload = {"meta": {"source_project": "test.aep"}, "tasks": []}
    save_ae_ticket("ticket-delete", payload, tmp_workspace)

    result = delete_ae_ticket("ticket-delete", tmp_workspace)
    assert result["deleted"] is True
    assert list_ae_tickets(tmp_workspace) == []

    with pytest.raises(FileNotFoundError):
        delete_ae_ticket("ticket-delete", tmp_workspace)


def test_get_ae_ticket_not_found(tmp_workspace: dict) -> None:
    with pytest.raises(FileNotFoundError):
        get_ae_ticket("nonexistent", tmp_workspace)


def test_get_ae_ticket_found(tmp_workspace: dict) -> None:
    payload = {"meta": {"source_project": "test.aep"}, "tasks": []}
    save_ae_ticket("ticket-002", payload, tmp_workspace)
    result = get_ae_ticket("ticket-002", tmp_workspace)
    assert result["ticket_id"] == "ticket-002"
    assert result["ticket"]["meta"]["source_project"] == "test.aep"


# ---------------------------------------------------------------------------
# scan_ae_project（mock COM）
# ---------------------------------------------------------------------------

def test_scan_ae_project_missing_path(tmp_workspace: dict) -> None:
    result = scan_ae_project(project_path="", workspace=tmp_workspace)
    assert result["ok"] is False
    assert "required" in result["error"]


def test_scan_ae_project_success(tmp_workspace: dict, mock_runtime) -> None:
    runtime, _ = mock_runtime
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = scan_ae_project(project_path="/fake/project.aep", workspace=tmp_workspace)

    assert result["ok"] is True
    assert result["ticket_id"]
    assert result["layer_count"] == 2
    assert result["comp_count"] == 1
    assert result["ticket"]["meta"]["tool"] == "after_effects"
    assert result["ticket"]["meta"]["platform"] == "com"


def test_scan_ae_project_creates_ticket_file(tmp_workspace: dict, mock_runtime) -> None:
    runtime, _ = mock_runtime
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = scan_ae_project(project_path="/fake/project.aep", workspace=tmp_workspace)

    assert result["ok"] is True
    ticket_path = Path(result["ticket_path"])
    assert ticket_path.exists()
    payload = json.loads(ticket_path.read_text(encoding="utf-8"))
    assert "meta" in payload
    assert "tasks" in payload
    assert len(payload["tasks"]) == 2
    # 确认 layer_id 格式为 comp_index:layer_index
    assert payload["tasks"][0]["layer_id"] == "1:1"


def test_scan_ae_project_connector_error(tmp_workspace: dict, mock_runtime) -> None:
    runtime, mock_connector = mock_runtime
    mock_connector.connect.side_effect = ConnectionError("AE not found")
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = scan_ae_project(project_path="/fake/project.aep", workspace=tmp_workspace)

    assert result["ok"] is False
    assert "AE not found" in result["error"]


def test_scan_ae_project_timeout(tmp_workspace: dict, mock_runtime) -> None:
    runtime, _ = mock_runtime

    class HangingThread:
        def __init__(self, target, daemon=False):
            self.target = target
            self.daemon = daemon

        def start(self):
            return None

        def join(self, timeout=None):
            return None

        def is_alive(self):
            return True

    with (
        patch("modules.adobe.after_effects.service._adapter") as mock_adapter,
        patch("modules.adobe.after_effects.scan.threading.Thread", HangingThread),
    ):
        mock_adapter.load_runtime.return_value = runtime
        result = scan_ae_project(project_path="/fake/project.aep", workspace=tmp_workspace)

    assert result == {"ok": False, "error": "AE scan timed out after 120 seconds"}


def test_list_ae_fonts_success(tmp_workspace: dict, mock_runtime) -> None:
    runtime, mock_connector = mock_runtime
    mock_connector.get_available_fonts.return_value = ["Arial", "Noto Sans"]

    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = list_ae_fonts(query="sans", limit=10, workspace=tmp_workspace)

    assert result == {
        "ok": True,
        "fonts": ["Arial", "Noto Sans"],
        "count": 2,
        "query": "sans",
        "limit": 10,
    }
    mock_connector.get_available_fonts.assert_called_once_with(query="sans", limit=10)


def test_list_ae_fonts_connector_error(tmp_workspace: dict, mock_runtime) -> None:
    runtime, mock_connector = mock_runtime
    mock_connector.get_available_fonts.side_effect = RuntimeError("font scan failed")

    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = list_ae_fonts(query="", limit=200, workspace=tmp_workspace)

    assert result["ok"] is False
    assert result["fonts"] == []
    assert result["error"] == "font scan failed"


def test_list_ae_fonts_timeout(tmp_workspace: dict, mock_runtime) -> None:
    runtime, _ = mock_runtime

    class HangingThread:
        def __init__(self, target, daemon=False):
            self.target = target
            self.daemon = daemon

        def start(self):
            return None

        def join(self, timeout=None):
            return None

        def is_alive(self):
            return True

    with (
        patch("modules.adobe.after_effects.service._adapter") as mock_adapter,
        patch("modules.adobe.after_effects.scan.threading.Thread", HangingThread),
    ):
        mock_adapter.load_runtime.return_value = runtime
        result = list_ae_fonts(query="", limit=200, workspace=tmp_workspace)

    assert result == {"ok": False, "error": "Font enumeration timed out", "fonts": []}


# ---------------------------------------------------------------------------
# _should_execute_task
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task,expected", [
    ({"status": "skip"}, False),
    ({"status": "confirmed"}, True),
    ({"status": "ready"}, True),
    ({"status": "approved"}, True),
    ({"status": "pending", "target_text": "Hello"}, True),
    ({"status": "pending", "target_font": "NotoSans-Bold"}, True),
    ({"status": "pending", "target_text": ""}, False),
    ({"status": "pending"}, False),
])
def test_should_execute_task(task: dict, expected: bool) -> None:
    assert _should_execute_task(task) == expected


# ---------------------------------------------------------------------------
# start_ae_ticket_execution（mock COM）
# ---------------------------------------------------------------------------

def test_start_ae_ticket_execution_not_found(tmp_workspace: dict) -> None:
    with pytest.raises(FileNotFoundError):
        start_ae_ticket_execution("nonexistent", workspace=tmp_workspace, job_id="job-001")


def test_start_ae_ticket_execution_dry_run(tmp_workspace: dict, sample_ticket: dict, mock_runtime) -> None:
    assert sample_ticket["ok"] is True
    ticket_id = sample_ticket["ticket_id"]

    # 标记任务为 confirmed
    ticket = sample_ticket["ticket"]
    for task in ticket.get("tasks", []):
        task["status"] = "confirmed"
        task["target_text"] = "New text"
    save_ae_ticket(ticket_id, ticket, tmp_workspace)

    done_event = threading.Event()
    finish_result: dict = {}

    def _on_finish(success: bool, payload: dict) -> None:
        finish_result["success"] = success
        finish_result["payload"] = payload
        done_event.set()

    runtime, _ = mock_runtime
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = start_ae_ticket_execution(
            ticket_id,
            dry_run=True,
            workspace=tmp_workspace,
            job_id="job-dry-001",
            on_finish=_on_finish,
        )
        done_event.wait(timeout=10)

    assert result["ok"] is True
    assert finish_result.get("payload", {}).get("dry_run") is True


def test_start_ae_ticket_execution_no_executable_tasks(tmp_workspace: dict, sample_ticket: dict, mock_runtime) -> None:
    ticket_id = sample_ticket["ticket_id"]
    done_event = threading.Event()
    finish_result: dict = {}

    def _on_finish(success: bool, payload: dict) -> None:
        finish_result["success"] = success
        finish_result["payload"] = payload
        done_event.set()

    runtime, _ = mock_runtime
    with patch("modules.adobe.after_effects.service._adapter") as mock_adapter:
        mock_adapter.load_runtime.return_value = runtime
        result = start_ae_ticket_execution(
            ticket_id,
            workspace=tmp_workspace,
            job_id="job-empty-001",
            on_finish=_on_finish,
        )
        done_event.wait(timeout=10)

    assert result["ok"] is True
    assert finish_result.get("success") is False
    assert "No executable" in finish_result.get("payload", {}).get("error", "")


# ---------------------------------------------------------------------------
# _build_ticket_from_layers
# ---------------------------------------------------------------------------

def test_build_ticket_from_layers() -> None:
    layers = [
        {
            "layer_id": "1:1", "comp_name": "Main", "comp_index": 1,
            "layer_name": "Title", "layer_index": 1, "layer_type": "text",
            "original_text": "Hello", "source_font": "Arial", "font_size": 48.0,
            "tracking": 0, "target_text": "", "target_font": "",
            "output_name": "output.aep", "status": "pending",
        },
    ]
    ticket = _build_ticket_from_layers(layers, "test.aep")
    assert ticket["meta"]["source_project"] == "test.aep"
    assert ticket["meta"]["tool"] == "after_effects"
    assert ticket["meta"]["platform"] == "com"
    assert len(ticket["tasks"]) == 1
