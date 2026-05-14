"""Tests for Photoshop automation service."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
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
    raw_text: str = "Hello"
    layer_obj: object | None = None
    smart_object_layer_id: int = 0
    smart_object_name: str = ""
    smart_object_inner_layer_name: str = ""


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
    notes: str = ""
    layer_kind: str = "text"
    smart_object_layer_id: int = 0
    smart_object_name: str = ""
    smart_object_inner_layer_name: str = ""
    preserve_copy: bool = False
    so_chain: list = None

    def __post_init__(self):
        if self.so_chain is None:
            self.so_chain = []


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


class FakeConnector:
    instances: list[FakeConnector] = []

    def __init__(self):
        self.layers = {
            1: SimpleNamespace(name="Title"),
            210: SimpleNamespace(id=210, ID=210, Name="Card", Kind=17, identity="smart:card"),
            211: SimpleNamespace(id=211, ID=211, Name="Card", Kind=17, identity="smart:card"),
        }
        self.app = SimpleNamespace(Documents=SimpleNamespace(Count=1), ActiveDocument=FakeDoc())
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

    def find_layer_by_id(self, _doc, layer_id: int):
        return self.layers.get(int(layer_id or 0))

    def get_layer_id(self, layer):
        return int(getattr(layer, "id", getattr(layer, "ID", 0)) or 0)

    def is_smart_object_layer(self, layer):
        return int(getattr(layer, "Kind", 0) or 0) == 17

    def collect_artboards(self, _doc):
        return []

    def collect_smart_object_layers(self, _container):
        return [layer for layer in self.layers.values() if self.is_smart_object_layer(layer)]

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
        "modify_smart_object_text_layer": Mock(),
        "TicketTask": FakeTicketTask,
        "TicketMeta": FakeTicketMeta,
        "Ticket": FakeTicket,
        "save_ticket_json": Mock(
            side_effect=lambda ticket, path: Path(path).write_text(json.dumps(ticket.to_dict()), encoding="utf-8")
        ),
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
    valid.write_text(
        json.dumps({"meta": {"source_psd": "a.psd"}, "tasks": [{"status": "confirmed"}, {"status": "pending"}]}),
        encoding="utf-8",
    )

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

    saved = service.save_photoshop_ticket(
        "ticket-a", {"meta": {"source_psd": "a.psd"}, "tasks": [{"status": "confirmed"}]}, ws
    )
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
    rows = [
        FakeScanRow(layer_id=10, artboard="A"),
        FakeScanRow(
            layer_id=11,
            artboard="B",
            layer_name="Card / Price",
            smart_object_layer_id=210,
            smart_object_name="Card",
            smart_object_inner_layer_name="Price",
        ),
    ]

    ticket = service._build_ticket(runtime, rows, "source.psd", ["zh", "en"])
    payload = ticket.to_dict()

    assert payload["meta"]["created_by"] == "mediatools_scan"
    assert len(payload["tasks"]) == 4
    assert {task["output_name"] for task in payload["tasks"]} == {"source_zh.psd", "source_en.psd"}
    smart_tasks = [task for task in payload["tasks"] if task["layer_kind"] == "smart_object_text"]
    assert len(smart_tasks) == 2
    assert {task["smart_object_layer_id"] for task in smart_tasks} == {210}
    assert {task["smart_object_name"] for task in smart_tasks} == {"Card"}
    assert {task["smart_object_inner_layer_name"] for task in smart_tasks} == {"Price"}

    no_lang_ticket = service._build_ticket(runtime, rows[:1], "source.psd", [])
    no_lang_task = no_lang_ticket.to_dict()["tasks"][0]
    assert no_lang_task["output_name"] == ""
    assert no_lang_task["language"] == ""
    assert no_lang_task["layer_kind"] == "text"


def test_ticket_task_from_dict_accepts_missing_smart_fields():
    spec = importlib.util.spec_from_file_location(
        "ps_ticket_json",
        Path("vendor/adobe/photoshop/com/src/ticket_json.py"),
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    task = module.TicketTask.from_dict(
        {
            "layer_id": 1,
            "artboard_name": "Board",
            "layer_name": "Title",
            "output_name": "",
            "language": "",
            "source_psd": "source.psd",
            "original_text": "Hello",
        }
    )

    assert task.layer_kind == "text"
    assert task.smart_object_layer_id == 0
    assert task.smart_object_name == ""


def test_scan_photoshop_document_success_opens_and_closes_doc(tmp_path, monkeypatch):
    ws = patch_workspace(monkeypatch, tmp_path)
    FakeConnector.instances.clear()
    runtime = fake_runtime(
        rows=[
            FakeScanRow(artboard="Board B"),
            FakeScanRow(
                layer_id=2,
                artboard="Board A",
                layer_name="Card / Price",
                smart_object_layer_id=210,
                smart_object_name="Card",
                smart_object_inner_layer_name="Price",
            ),
        ]
    )
    monkeypatch.setattr(service, "_runtime", lambda: runtime)
    monkeypatch.setattr(service.uuid, "uuid4", lambda: "ticket-id")

    result = service.scan_photoshop_document(
        psd_path="C:/design/file.psd", languages=["zh"], timeout_sec=5, workspace=ws
    )

    assert result["ok"] is True
    assert result["ticket_id"] == "ticket-id"
    assert result["layer_count"] == 2
    assert result["normal_text_layer_count"] == 1
    assert result["smart_text_layer_count"] == 1
    assert result["smart_object_count"] == 1
    assert result["skipped_smart_object_count"] == 0
    assert result["scan_warnings"] == []
    assert result["artboards"] == ["Board A", "Board B"]
    assert Path(result["ticket_path"]).exists()
    connector = FakeConnector.instances[0]
    assert connector.opened == ["C:/design/file.psd"]
    assert connector.closed and connector.closed[0][1] is False
    assert connector.disconnected is True
    assert runtime["pythoncom"].calls == ["init", "uninit"]


def test_scan_photoshop_document_reports_progress_counts(tmp_path, monkeypatch):
    ws = patch_workspace(monkeypatch, tmp_path)
    rows = [
        FakeScanRow(),
        FakeScanRow(
            layer_id=2,
            layer_name="Card / Price",
            smart_object_layer_id=210,
            smart_object_name="Card",
            smart_object_inner_layer_name="Price",
        ),
    ]
    runtime = fake_runtime(rows=rows)

    def scan_with_progress(_connector, _doc, _source_path, progress_callback=None, cancel_check=None):
        if progress_callback:
            progress_callback(
                {
                    "stage": "已发现 2 个文字层",
                    "layer_count": 2,
                    "normal_text_layer_count": 1,
                    "smart_text_layer_count": 1,
                    "smart_object_count": 1,
                    "skipped_smart_object_count": 0,
                }
            )
        return rows

    runtime["scan_document_for_ticket"] = Mock(side_effect=scan_with_progress)
    monkeypatch.setattr(service, "_runtime", lambda: runtime)
    monkeypatch.setattr(service.uuid, "uuid4", lambda: "ticket-id")
    progress_events: list[dict] = []

    service.scan_photoshop_document(
        psd_path="C:/design/file.psd",
        languages=[],
        timeout_sec=5,
        workspace=ws,
        progress_callback=progress_events.append,
    )

    assert progress_events[0]["stage"] == "正在连接 Photoshop 并读取文档"
    assert progress_events[-1]["layer_count"] == 2
    assert progress_events[-1]["smart_text_layer_count"] == 1


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


def test_start_ticket_execution_distinguishes_normal_and_smart_rows(tmp_path, monkeypatch):
    from modules.adobe.photoshop import execution

    ws = patch_workspace(monkeypatch, tmp_path)
    ticket_id = "ticket-exec"
    service._ticket_path(ticket_id, ws).write_text("{}", encoding="utf-8")
    with service._execution_lock:
        service._executions.clear()

    normal_task = FakeTicketTask(
        layer_id=1,
        artboard_name="Board",
        layer_name="Title",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="Hello",
        target_text="你好",
        target_font="",
        status="confirmed",
        layer_kind="text",
    )
    smart_task = FakeTicketTask(
        layer_id=99,
        artboard_name="Board",
        layer_name="Card / Price",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="Price",
        target_text="价格",
        target_font="",
        status="confirmed",
        layer_kind="smart_object_text",
        smart_object_layer_id=210,
        smart_object_name="Card",
        smart_object_inner_layer_name="Price",
    )
    ticket = FakeTicket(FakeTicketMeta(created_by="test", source_psd="C:/design/source.psd"), [normal_task, smart_task])
    modify_text_layer = Mock(return_value=SimpleNamespace(success=True, message="normal"))
    modify_smart_object_text_layer = Mock(return_value=SimpleNamespace(success=True, message="smart"))
    runtime = fake_runtime(
        rows=[
            FakeScanRow(layer_id=1, layer_name="Title", original_text="Hello", raw_text="Hello", layer_obj=object()),
            FakeScanRow(
                layer_id=2,
                layer_name="Card / Price",
                original_text="Price",
                raw_text="Price",
                smart_object_layer_id=210,
                smart_object_name="Card",
                smart_object_inner_layer_name="Price",
            ),
        ]
    )
    runtime.update(
        {
            "load_ticket_json": Mock(return_value=ticket),
            "save_ticket_json": Mock(),
            "TextMapping": lambda **kwargs: SimpleNamespace(**kwargs),
            "AdjustParams": lambda **kwargs: SimpleNamespace(**kwargs),
            "modify_text_layer": modify_text_layer,
            "modify_smart_object_text_layer": modify_smart_object_text_layer,
        }
    )
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    class ImmediateThread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(execution.threading, "Thread", ImmediateThread)
    finished: list[tuple[bool, dict]] = []

    result = execution.start_ticket_execution_impl(
        ticket_id,
        dry_run=True,
        workspace=ws,
        job_id="job-1",
        on_finish=lambda ok, payload: finished.append((ok, payload)),
    )

    assert result["ok"] is True
    execution_state = service._executions[ticket_id]
    assert execution_state.error == ""
    runtime["scan_document_for_ticket"].assert_not_called()
    modify_text_layer.assert_called_once()
    modify_smart_object_text_layer.assert_called_once()
    assert normal_task.status == "done"
    assert smart_task.status == "done"
    assert finished == [(
        True,
        {
            "status": "done",
            "output_paths": [],
            "ticket_id": ticket_id,
            "dry_run": True,
            "successful_tasks": 2,
            "failed_tasks": 0,
            "skipped_tasks": 0,
            "layer_results": [
                {
                    "layer_name": "Title", "original_text": "", "new_text": "",
                    "original_font_size": 0, "final_font_size": 0,
                    "original_font": "", "new_font": "",
                    "converged": False, "skipped": False,
                    "message": "normal", "fit_status": "", "log_path": "",
                },
                {
                    "layer_name": "Card / Price", "original_text": "", "new_text": "",
                    "original_font_size": 0, "final_font_size": 0,
                    "original_font": "", "new_font": "",
                    "converged": False, "skipped": False,
                    "message": "smart", "fit_status": "", "log_path": "",
                },
            ],
            "log_paths": [],
        },
    )]


def test_start_ticket_execution_applies_smart_object_tasks_individually(tmp_path, monkeypatch):
    from modules.adobe.photoshop import execution

    ws = patch_workspace(monkeypatch, tmp_path)
    ticket_id = "ticket-shared-smart"
    service._ticket_path(ticket_id, ws).write_text("{}", encoding="utf-8")
    with service._execution_lock:
        service._executions.clear()

    first_task = FakeTicketTask(
        layer_id=99,
        artboard_name="Hero",
        layer_name="Card / Price",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="Price",
        target_text="价格",
        target_font="",
        status="confirmed",
        layer_kind="smart_object_text",
        smart_object_layer_id=210,
        smart_object_name="Card",
        smart_object_inner_layer_name="Price",
    )
    second_task = FakeTicketTask(
        layer_id=100,
        artboard_name="Footer",
        layer_name="Card / Price",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="Price",
        target_text="价格",
        target_font="",
        status="confirmed",
        layer_kind="smart_object_text",
        smart_object_layer_id=211,
        smart_object_name="Card",
        smart_object_inner_layer_name="Price",
    )
    ticket = FakeTicket(FakeTicketMeta(created_by="test", source_psd="C:/design/source.psd"), [first_task, second_task])
    single_modifier = Mock(return_value=SimpleNamespace(success=True, message="single"))
    runtime = fake_runtime(
        rows=[
            FakeScanRow(
                layer_id=2,
                artboard="Hero",
                layer_name="Card / Price",
                original_text="Price",
                raw_text="Price",
                smart_object_layer_id=210,
                smart_object_name="Card",
                smart_object_inner_layer_name="Price",
            ),
            FakeScanRow(
                layer_id=3,
                artboard="Footer",
                layer_name="Card / Price",
                original_text="Price",
                raw_text="Price",
                smart_object_layer_id=211,
                smart_object_name="Card",
                smart_object_inner_layer_name="Price",
            ),
        ]
    )
    runtime.update(
        {
            "load_ticket_json": Mock(return_value=ticket),
            "save_ticket_json": Mock(),
            "TextMapping": lambda **kwargs: SimpleNamespace(**kwargs),
            "AdjustParams": lambda **kwargs: SimpleNamespace(**kwargs),
            "modify_smart_object_text_layer": single_modifier,
        }
    )
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    class ImmediateThread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(execution.threading, "Thread", ImmediateThread)

    result = execution.start_ticket_execution_impl(ticket_id, dry_run=True, workspace=ws, job_id="job-1")

    assert result["ok"] is True
    runtime["scan_document_for_ticket"].assert_not_called()
    assert single_modifier.call_count == 2
    assert first_task.status == "done"
    assert second_task.status == "done"
    assert first_task.notes == "single"
    assert second_task.notes == "single"


def test_smart_layer_resolution_rejects_stale_non_smart_id_without_name_fallback():
    from modules.adobe.photoshop import execution

    connector = FakeConnector()
    connector.layers[2344] = SimpleNamespace(id=2344, ID=2344, Name="Not a smart object", Kind=1)
    task = Mock(
        smart_object_layer_id=2344,
        smart_object_name="Card",
        artboard_name="Hero",
    )

    layer, layer_id = execution._resolve_smart_layer(connector, FakeDoc(), task)

    assert layer is None
    assert layer_id == 0


def test_start_ticket_execution_marks_error_when_all_tasks_fail(tmp_path, monkeypatch):
    from modules.adobe.photoshop import execution

    ws = patch_workspace(monkeypatch, tmp_path)
    ticket_id = "ticket-all-fail"
    service._ticket_path(ticket_id, ws).write_text("{}", encoding="utf-8")
    with service._execution_lock:
        service._executions.clear()

    task = FakeTicketTask(
        layer_id=999,
        artboard_name="Board",
        layer_name="Missing",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="Hello",
        target_text="你好",
        target_font="",
        status="confirmed",
        layer_kind="text",
    )
    ticket = FakeTicket(FakeTicketMeta(created_by="test", source_psd="C:/design/source.psd"), [task])
    runtime = fake_runtime()
    runtime.update(
        {
            "load_ticket_json": Mock(return_value=ticket),
            "save_ticket_json": Mock(),
            "TextMapping": lambda **kwargs: SimpleNamespace(**kwargs),
            "AdjustParams": lambda **kwargs: SimpleNamespace(**kwargs),
        }
    )
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    class ImmediateThread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(execution.threading, "Thread", ImmediateThread)
    finished: list[tuple[bool, dict]] = []

    result = execution.start_ticket_execution_impl(
        ticket_id,
        dry_run=True,
        workspace=ws,
        job_id="job-1",
        on_finish=lambda ok, payload: finished.append((ok, payload)),
    )

    assert result["ok"] is True
    state = service._executions[ticket_id]
    assert state.status == "error"
    assert "without any successful task" in state.error
    assert task.status == "error"
    assert task.notes == "Layer id not found during execution"
    assert finished and finished[0][0] is False


def test_preserve_copy_skips_modify_calls(tmp_path, monkeypatch):
    from modules.adobe.photoshop import execution

    ws = patch_workspace(monkeypatch, tmp_path)
    ticket_id = "ticket-preserve"
    service._ticket_path(ticket_id, ws).write_text("{}", encoding="utf-8")
    with service._execution_lock:
        service._executions.clear()

    preserve_task = FakeTicketTask(
        layer_id=1,
        artboard_name="Board",
        layer_name="Brand",
        output_name="out.psd",
        language="zh",
        line_count=1,
        alignment="left",
        font_size=12,
        tracking=0,
        width_px=100,
        height_px=20,
        source_psd="source.psd",
        source_font="SourceFont",
        original_text="ProductX",
        target_text="",
        target_font="",
        status="confirmed",
        layer_kind="text",
        preserve_copy=True,
    )
    ticket = FakeTicket(FakeTicketMeta(created_by="test", source_psd="C:/design/source.psd"), [preserve_task])
    modify_text_layer = Mock(return_value=SimpleNamespace(success=True, message="unexpected"))
    modify_smart = Mock(return_value=SimpleNamespace(success=True, message="unexpected"))
    runtime = fake_runtime(rows=[])
    runtime.update(
        {
            "load_ticket_json": Mock(return_value=ticket),
            "save_ticket_json": Mock(),
            "TextMapping": lambda **kwargs: SimpleNamespace(**kwargs),
            "AdjustParams": lambda **kwargs: SimpleNamespace(**kwargs),
            "modify_text_layer": modify_text_layer,
            "modify_smart_object_text_layer": modify_smart,
        }
    )
    monkeypatch.setattr(service, "_runtime", lambda: runtime)

    class ImmediateThread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(execution.threading, "Thread", ImmediateThread)

    result = execution.start_ticket_execution_impl(
        ticket_id,
        dry_run=True,
        workspace=ws,
        job_id="job-1",
        on_finish=lambda *_a: None,
    )

    assert result["ok"] is True
    modify_text_layer.assert_not_called()
    modify_smart.assert_not_called()
    assert preserve_task.status == "done"
    assert "固定文案" in (preserve_task.notes or "")


def test_task_helpers_and_start_execution_delegate(monkeypatch):
    assert service._default_output_name("C:/design/banner.psd") == "banner_photoshop.psd"
    from modules.adobe.photoshop import execution

    assert execution._output_directory("C:/design/banner.psd", Mock(output_dir="")) == Path("C:/design")
    assert execution._output_directory("C:/design/banner.psd", Mock(output_dir="D:/exports")) == Path("D:/exports")
    assert execution._output_filename("D:/other/custom.psd", "C:/design/banner.psd") == "custom.psd"
    assert execution._output_filename("", "C:/design/banner.psd") == "banner_photoshop.psd"

    tasks = [
        Mock(output_name="", status="skip", target_text="", target_font="", original_text=""),
        Mock(
            output_name="a.psd",
            status="confirmed",
            target_text="",
            target_font="Inter",
            original_text="Hi",
        ),
        Mock(output_name="a.psd", status="pending", target_text="Hello", original_text="Hi", target_font=""),
        Mock(output_name="b.psd", status="pending", target_text="", target_font="", original_text="Brand", preserve_copy=True),
    ]
    assert service._should_execute_task(tasks[0]) is False
    assert service._should_execute_task(tasks[1]) is True
    assert service._should_execute_task(tasks[2]) is True
    assert service._should_execute_task(tasks[3]) is True
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
