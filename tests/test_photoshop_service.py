"""Tests for Photoshop automation service."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from unittest.mock import Mock

import pytest

from modules.adobe.photoshop import service


@dataclass
class FakeScanRow:
    layer_id: int = 1
    artboard: str = "Board"
    layer_name: str = "Title"
    line_count: int = 2
    alignment: str = "center"
    font_size: float = 24.0
    tracking: int = 0
    width_px: int = 100
    height_px: int = 60
    source_font: str = "SourceFont"
    original_text: str = "Hello"


@dataclass
class FakeTicketTask:
    layer_id: int
    artboard_name: str
    layer_name: str
    output_name: str
    language: str
    line_count: int
    alignment: str
    font_size: float
    tracking: int
    width_px: int
    height_px: int
    source_psd: str
    source_font: str
    original_text: str
    target_text: str
    target_font: str
    status: str


@dataclass
class FakeTicketMeta:
    created_by: str
    source_psd: str


class FakeTicket:
    def __init__(self, meta: FakeTicketMeta, tasks: list[FakeTicketTask]):
        self.meta = meta
        self.tasks = tasks

    def to_dict(self):
        return {"meta": asdict(self.meta), "tasks": [asdict(task) for task in self.tasks]}


class FakePythonCom:
    def __init__(self):
        self.calls: list[str] = []

    def CoInitialize(self):
        self.calls.append("init")

    def CoUninitialize(self):
        self.calls.append("uninit")


class FakeDoc:
    FullName = "C:/design/source.psd"


class FakeDocuments:
    Count = 1


class FakeApp:
    Documents = FakeDocuments()
    ActiveDocument = FakeDoc()


class FakeConnector:
    instances: list[FakeConnector] = []

    def __init__(self):
        self.app = FakeApp()
        self.opened: list[str] = []
        self.closed: list[tuple[FakeDoc, bool]] = []
        self.connected = False
        self.disconnected = False
        FakeConnector.instances.append(self)

    def connect(self):
        self.connected = True

    def open_document(self, psd_path: str):
        self.opened.append(psd_path)
        return FakeDoc()

    def close_document(self, doc, save=False):
        self.closed.append((doc, save))

    def disconnect(self):
        self.disconnected = True


def workspace(tmp_path: Path) -> dict:
    return {
        "manifests_dir": str(tmp_path / "manifests"),
        "exports_dir": str(tmp_path / "exports"),
    }


def fake_runtime(rows: list[FakeScanRow] | None = None, pythoncom: FakePythonCom | None = None) -> dict:
    runtime = {
        "pythoncom": pythoncom or FakePythonCom(),
        "PhotoshopConnector": FakeConnector,
        "scan_document_for_ticket": Mock(return_value=rows if rows is not None else [FakeScanRow()]),
        "TicketTask": FakeTicketTask,
        "TicketMeta": FakeTicketMeta,
        "Ticket": FakeTicket,
        "save_ticket_json": Mock(side_effect=lambda ticket, path: Path(path).write_text(json.dumps(ticket.to_dict()), encoding="utf-8")),
    }
    return runtime


def patch_workspace(monkeypatch, tmp_path: Path):
    ws = workspace(tmp_path)

    def get_workspace_dir(kind, workspace_arg=None):
        source = workspace_arg or ws
        return Path(source[f"{kind}_dir"])

    monkeypatch.setattr(service, "get_workspace_dir", get_workspace_dir)
    return ws


def test_ticket_payload_validation_and_summary(tmp_path):
    valid = tmp_path / "ticket-1.json"
    valid.write_text(json.dumps({"meta": {"source_psd": "a.psd"}, "tasks": [{"status": "confirmed"}, {"status": "pending"}]}), encoding="utf-8")

    payload = service._load_ticket_payload(valid)
    summary = service._ticket_summary(valid, payload)

    assert summary["ticket_id"] == "ticket-1"
    assert summary["task_count"] == 2
    assert summary["confirmed_count"] == 1

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        service._load_ticket_payload(bad_json)

    non_object = tmp_path / "list.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        service._load_ticket_payload(non_object)

    bad_shape = tmp_path / "shape.json"
    bad_shape.write_text(json.dumps({"meta": [], "tasks": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid shape"):
        service._load_ticket_payload(bad_shape)

    with pytest.raises(ValueError, match="payload"):
        service._save_ticket_payload(tmp_path / "x.json", [])
    with pytest.raises(ValueError, match="meta"):
        service._save_ticket_payload(tmp_path / "x.json", {"meta": [], "tasks": []})
    with pytest.raises(ValueError, match="tasks"):
        service._save_ticket_payload(tmp_path / "x.json", {"meta": {}, "tasks": {}})


def test_status_ticket_crud_and_invalid_ticket_skip(tmp_path, monkeypatch):
    ws = patch_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(service._adapter, "get_status", lambda: {"connected": False})
    with service._execution_lock:
        service._executions.clear()
        service._executions["run-1"] = Mock(status="running")
        service._executions["done-1"] = Mock(status="completed")

    status = service.get_photoshop_status(ws)
    assert status["connected"] is False
    assert status["running_executions"] == 1
    assert Path(status["tickets_dir"]).exists()
    assert Path(status["exports_dir"]).exists()

    saved = service.save_photoshop_ticket("ticket-a", {"meta": {"source_psd": "a.psd"}, "tasks": [{"status": "confirmed"}]}, ws)
    assert saved["ticket_id"] == "ticket-a"
    assert service.get_photoshop_ticket("ticket-a", ws)["ticket"]["meta"]["source_psd"] == "a.psd"

    invalid = Path(status["tickets_dir"]) / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    tickets = service.list_photoshop_tickets(ws)
    assert [item["ticket_id"] for item in tickets] == ["ticket-a"]

    external = tmp_path / "external-ps-ticket.json"
    external.write_text(json.dumps({"meta": {"source_psd": "external.psd"}, "tasks": []}), encoding="utf-8")
    imported = service.import_photoshop_ticket(str(external), ws, "imported-ps")
    assert imported["ticket_id"] == "imported-ps"
    assert imported["imported_from"] == str(external.resolve())
    assert service.get_photoshop_ticket("imported-ps", ws)["ticket"]["meta"]["source_psd"] == "external.psd"

    deleted = service.delete_photoshop_ticket("ticket-a", ws)
    assert deleted["deleted"] is True
    service.delete_photoshop_ticket("imported-ps", ws)
    assert service.list_photoshop_tickets(ws) == []

    with pytest.raises(FileNotFoundError):
        service.get_photoshop_ticket("missing", ws)

    with pytest.raises(FileNotFoundError):
        service.delete_photoshop_ticket("missing", ws)


def test_build_ticket_expands_languages_and_defaults():
    runtime = fake_runtime()
    rows = [FakeScanRow(layer_id=10, artboard="A"), FakeScanRow(layer_id=11, artboard="B")]

    ticket = service._build_ticket(runtime, rows, "source.psd", ["zh", "en"])
    payload = ticket.to_dict()

    assert payload["meta"]["created_by"] == "mediatools_scan"
    assert len(payload["tasks"]) == 4
    assert {task["output_name"] for task in payload["tasks"]} == {"zh.psd", "en.psd"}

    no_lang_ticket = service._build_ticket(runtime, rows[:1], "source.psd", [])
    no_lang_task = no_lang_ticket.to_dict()["tasks"][0]
    assert no_lang_task["output_name"] == ""
    assert no_lang_task["language"] == ""


def test_scan_photoshop_document_success_opens_and_closes_doc(tmp_path, monkeypatch):
    ws = patch_workspace(monkeypatch, tmp_path)
    FakeConnector.instances.clear()
    runtime = fake_runtime(rows=[FakeScanRow(artboard="Board B"), FakeScanRow(layer_id=2, artboard="Board A")])
    monkeypatch.setattr(service, "_runtime", lambda: runtime)
    monkeypatch.setattr(service.uuid, "uuid4", lambda: "ticket-id")

    result = service.scan_photoshop_document(psd_path="C:/design/file.psd", languages=["zh"], timeout_sec=5, workspace=ws)

    assert result["ok"] is True
    assert result["ticket_id"] == "ticket-id"
    assert result["layer_count"] == 2
    assert result["artboards"] == ["Board A", "Board B"]
    assert Path(result["ticket_path"]).exists()
    connector = FakeConnector.instances[0]
    assert connector.opened == ["C:/design/file.psd"]
    assert connector.closed and connector.closed[0][1] is False
    assert connector.disconnected is True
    assert runtime["pythoncom"].calls == ["init", "uninit"]


def test_scan_photoshop_document_uses_active_document_and_reports_no_layers(tmp_path, monkeypatch):
    ws = patch_workspace(monkeypatch, tmp_path)
    runtime = fake_runtime(rows=[])
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    result = service.scan_photoshop_document(timeout_sec=5, workspace=ws)

    assert result == {"ok": False, "message": "No text layers found", "source_psd": "C:/design/source.psd"}


def test_scan_photoshop_document_reports_connector_errors_and_timeout(tmp_path, monkeypatch):
    patch_workspace(monkeypatch, tmp_path)

    class EmptyConnector(FakeConnector):
        def __init__(self):
            super().__init__()
            self.app.Documents.Count = 0

    runtime = fake_runtime()
    runtime["PhotoshopConnector"] = EmptyConnector
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    with pytest.raises(RuntimeError, match="No open Photoshop document"):
        service.scan_photoshop_document(timeout_sec=5)

    class NeverFinishesThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def join(self, timeout):
            pass

        def is_alive(self):
            return True

    monkeypatch.setattr(service.threading, "Thread", NeverFinishesThread)
    with pytest.raises(TimeoutError, match="timed out"):
        service.scan_photoshop_document(timeout_sec=0)


def test_task_helpers_and_start_execution_delegate(monkeypatch):
    assert service._default_output_name("C:/design/banner.psd") == "banner_photoshop.psd"

    tasks = [
        Mock(output_name="", status="skip", target_text="", target_font=""),
        Mock(output_name="a.psd", status="confirmed", target_text="", target_font=""),
        Mock(output_name="a.psd", status="pending", target_text="Hello", target_font=""),
        Mock(output_name="b.psd", status="pending", target_text="", target_font=""),
    ]
    assert service._should_execute_task(tasks[0]) is False
    assert service._should_execute_task(tasks[1]) is True
    assert service._should_execute_task(tasks[2]) is True
    assert service._should_execute_task(tasks[3]) is False
    assert set(service._group_tasks(tasks)) == {"", "a.psd", "b.psd"}

    delegate = Mock(return_value={"ok": True})
    fake_module = type("M", (), {"start_ticket_execution_impl": delegate})
    monkeypatch.setitem(__import__("sys").modules, "modules.adobe.photoshop.execution", fake_module)

    result = service.start_ticket_execution(
        "ticket-1",
        dry_run=True,
        selected_task_indexes=[1],
        workspace={"x": "y"},
        job_id="job-1",
        on_progress=lambda *_args: None,
        on_finish=lambda *_args: None,
    )

    assert result == {"ok": True}
    delegate.assert_called_once()
    assert delegate.call_args.args[0] == "ticket-1"
    assert delegate.call_args.kwargs["dry_run"] is True
