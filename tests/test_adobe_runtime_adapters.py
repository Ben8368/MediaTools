"""Tests for Adobe runtime adapter dispatch and dependency checks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import adapters.adobe_runtime as adobe_runtime
import adapters.after_effects_runtime as ae_runtime
from adapters.after_effects_runtime import AfterEffectsAutomationAdapter


class _FakeToolAdapter:
    def __init__(self, name: str) -> None:
        self.name = name

    def get_status(self) -> dict[str, str]:
        return {"tool": self.name}

    def load_runtime(self) -> dict[str, str]:
        return {"runtime": self.name}


def test_adobe_adapter_dispatches_status_and_runtime(monkeypatch):
    monkeypatch.setattr(
        adobe_runtime,
        "PhotoshopAutomationAdapter",
        lambda: _FakeToolAdapter("photoshop"),
    )
    monkeypatch.setattr(
        adobe_runtime,
        "AfterEffectsAutomationAdapter",
        lambda: _FakeToolAdapter("after_effects"),
    )

    adapter = adobe_runtime.AdobeAutomationAdapter()

    assert adapter.get_status("photoshop") == {"tool": "photoshop"}
    assert adapter.get_status("after_effects") == {"tool": "after_effects"}
    assert adapter.get_status() == {
        "photoshop": {"tool": "photoshop"},
        "after_effects": {"tool": "after_effects"},
    }
    assert adapter.load_runtime("photoshop") == {"runtime": "photoshop"}
    assert adapter.load_runtime("after_effects") == {"runtime": "after_effects"}
    with pytest.raises(ValueError, match="Unknown Adobe tool"):
        adapter.load_runtime("illustrator")  # type: ignore[arg-type]


def test_after_effects_status_reasons(tmp_path, monkeypatch):
    adapter = AfterEffectsAutomationAdapter()
    adapter.src_dir = tmp_path / "missing"

    assert adapter.get_status()["reason"] == "missing_source"

    adapter.src_dir = tmp_path / "src"
    adapter.src_dir.mkdir()
    (adapter.src_dir / "ae_connector.py").write_text("# connector", encoding="utf-8")

    monkeypatch.setattr(adapter, "is_supported_platform", lambda: False)
    assert adapter.get_status()["reason"] == "windows_only"

    monkeypatch.setattr(adapter, "is_supported_platform", lambda: True)
    monkeypatch.setattr(adapter, "can_import_pywin32", lambda: False)
    assert adapter.get_status()["reason"] == "missing_pywin32"

    monkeypatch.setattr(adapter, "can_import_pywin32", lambda: True)
    status = adapter.get_status()
    assert status["available"] is True
    assert status["reason"] == ""
    assert status["source_exists"] is True
    assert status["platform"] == "com"


def test_after_effects_default_src_dir_uses_product_first_layout():
    adapter = AfterEffectsAutomationAdapter()

    assert adapter.src_dir.as_posix().endswith("vendor/adobe/after-effects/com/src")


def test_after_effects_runtime_path_is_inserted_once(tmp_path, monkeypatch):
    adapter = AfterEffectsAutomationAdapter()
    adapter.src_dir = tmp_path / "ae-src"
    runtime_path: list[str] = []
    monkeypatch.setattr(ae_runtime.sys, "path", runtime_path)

    adapter.ensure_runtime_path()
    adapter.ensure_runtime_path()

    assert runtime_path == [str(adapter.src_dir)]


@pytest.mark.parametrize(
    ("status", "message"),
    [
        ({"source_exists": False, "windows_only": True, "pywin32": True}, "source is missing"),
        ({"source_exists": True, "windows_only": False, "pywin32": True}, "only supported on Windows"),
        ({"source_exists": True, "windows_only": True, "pywin32": False}, "pywin32 is not installed"),
    ],
)
def test_after_effects_load_runtime_rejects_unavailable_dependencies(monkeypatch, status, message):
    adapter = AfterEffectsAutomationAdapter()
    monkeypatch.setattr(adapter, "get_status", lambda: status)

    with pytest.raises(RuntimeError, match=message):
        adapter.load_runtime()


def test_after_effects_load_runtime_imports_connector_and_pythoncom(monkeypatch):
    adapter = AfterEffectsAutomationAdapter()
    ensure_calls: list[bool] = []
    connector = SimpleNamespace(AfterEffectsConnector=object())
    pythoncom = SimpleNamespace()

    monkeypatch.setattr(
        adapter,
        "get_status",
        lambda: {"source_exists": True, "windows_only": True, "pywin32": True},
    )
    monkeypatch.setattr(adapter, "ensure_runtime_path", lambda: ensure_calls.append(True))
    monkeypatch.setattr(
        ae_runtime.importlib,
        "import_module",
        lambda name: {"ae_connector": connector, "pythoncom": pythoncom}[name],
    )

    runtime = adapter.load_runtime()

    assert ensure_calls == [True]
    assert runtime["AfterEffectsConnector"] is connector.AfterEffectsConnector
    assert runtime["pythoncom"] is pythoncom
