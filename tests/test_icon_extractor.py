import struct
import sys
import types
from pathlib import Path

from modules.assets import icon_extractor


def test_extract_icon_missing_file(tmp_path):
    result = icon_extractor.extract_icon(str(tmp_path / "missing.exe"))

    assert result["ok"] is False
    assert "error" in result


def test_extract_icon_pe_png_success(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    out = tmp_path / "app.png"
    exe.write_bytes(b"MZ")

    def fake_extract(_exe_path: str, output_png: str) -> bool:
        Path(output_png).write_bytes(b"png")
        return True

    monkeypatch.setattr(icon_extractor, "extract_icon_from_pe", fake_extract)

    result = icon_extractor.extract_icon(str(exe), str(out))

    assert result == {"ok": True, "output": str(out), "method": "pe_png", "size": 3}


def test_extract_icon_pe_runtime_error_stops_with_error(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"MZ")

    def fail_pe(_exe_path: str, _output_png: str) -> bool:
        raise RuntimeError("missing pefile")

    monkeypatch.setattr(icon_extractor, "extract_icon_from_pe", fail_pe)

    result = icon_extractor.extract_icon(str(exe))

    assert result == {"ok": False, "error": "missing pefile"}


def test_extract_icon_falls_back_to_win32(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    out = tmp_path / "icon.png"
    exe.write_bytes(b"MZ")

    monkeypatch.setattr(icon_extractor, "extract_icon_from_pe", lambda *_args: False)

    def fake_win32(_exe_path: str, output_png: str) -> bool:
        Path(output_png).write_bytes(b"rendered")
        return True

    monkeypatch.setattr(icon_extractor, "extract_icon_with_win32", fake_win32)

    result = icon_extractor.extract_icon(str(exe), str(out))

    assert result == {"ok": True, "output": str(out), "method": "win32_render", "size": 8}


def test_extract_icon_reports_fallback_exception(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"MZ")

    monkeypatch.setattr(icon_extractor, "extract_icon_from_pe", lambda *_args: False)

    def fail_win32(*_args) -> bool:
        raise ValueError("bad icon")

    monkeypatch.setattr(icon_extractor, "extract_icon_with_win32", fail_win32)

    result = icon_extractor.extract_icon(str(exe))

    assert result == {"ok": False, "error": "bad icon"}


class _Node:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_extract_icon_from_pe_writes_embedded_png(tmp_path, monkeypatch):
    out = tmp_path / "icon.png"
    png = b"\x89PNG\r\n"
    group_data = b"\x00\x00\x01\x00\x01\x00" + struct.pack("<BBBBHHIH", 0, 0, 0, 0, 0, 0, len(png), 7)
    mapped = bytearray(80)
    mapped[10 : 10 + len(group_data)] = group_data
    mapped[40 : 40 + len(png)] = png

    icon_lang = _Node(data=_Node(struct=_Node(OffsetToData=40, Size=len(png))))
    icon_res = _Node(id=7, directory=_Node(entries=[icon_lang]))
    icon_type = _Node(struct=_Node(Id=3), directory=_Node(entries=[icon_res]))

    group_lang = _Node(data=_Node(struct=_Node(OffsetToData=10, Size=len(group_data))))
    group_sub = _Node(directory=_Node(entries=[group_lang]))
    group_type = _Node(struct=_Node(Id=14), directory=_Node(entries=[group_sub]))

    class FakePE:
        DIRECTORY_ENTRY_RESOURCE = _Node(entries=[group_type, icon_type])

        def get_memory_mapped_image(self):
            return bytes(mapped)

        def close(self):
            self.closed = True

    monkeypatch.setitem(sys.modules, "pefile", types.SimpleNamespace(PE=lambda _path: FakePE()))

    assert icon_extractor.extract_icon_from_pe("app.exe", str(out)) is True
    assert out.read_bytes() == png


def test_extract_icon_from_pe_returns_false_without_resources(monkeypatch):
    class FakePE:
        def close(self):
            self.closed = True

    monkeypatch.setitem(sys.modules, "pefile", types.SimpleNamespace(PE=lambda _path: FakePE()))

    assert icon_extractor.extract_icon_from_pe("app.exe", "out.png") is False


def test_extract_icon_from_pe_returns_false_when_no_png_icon(tmp_path, monkeypatch):
    out = tmp_path / "icon.png"
    group_data = b"\x00\x00\x01\x00\x01\x00" + struct.pack("<BBBBHHIH", 32, 32, 0, 0, 0, 0, 0, 7)
    mapped = bytearray(80)
    mapped[10 : 10 + len(group_data)] = group_data

    group_lang = _Node(data=_Node(struct=_Node(OffsetToData=10, Size=len(group_data))))
    group_sub = _Node(directory=_Node(entries=[group_lang]))
    group_type = _Node(struct=_Node(Id=14), directory=_Node(entries=[group_sub]))

    class FakePE:
        DIRECTORY_ENTRY_RESOURCE = _Node(entries=[group_type])

        def get_memory_mapped_image(self):
            return bytes(mapped)

        def close(self):
            self.closed = True

    monkeypatch.setitem(sys.modules, "pefile", types.SimpleNamespace(PE=lambda _path: FakePE()))

    assert icon_extractor.extract_icon_from_pe("app.exe", str(out)) is False
    assert not out.exists()


def test_extract_icon_with_win32_renders_png(tmp_path, monkeypatch):
    out = tmp_path / "icon.png"
    calls = []

    class FakeBitmap:
        def CreateCompatibleBitmap(self, _dc, width, height):
            self.width = width
            self.height = height

        def GetInfo(self):
            return {"bmWidth": self.width, "bmHeight": self.height}

        def GetBitmapBits(self, _signed):
            return b"\x00" * self.width * self.height * 4

    class FakeMemDC:
        def SelectObject(self, _bitmap):
            calls.append("select")

        def GetSafeHdc(self):
            return 123

        def DeleteDC(self):
            calls.append("mem-delete")

    class FakeDC:
        def CreateCompatibleDC(self):
            return FakeMemDC()

        def DeleteDC(self):
            calls.append("dc-delete")

    class FakeImage:
        def save(self, output_png):
            Path(output_png).write_bytes(b"rendered")

    monkeypatch.setitem(
        sys.modules,
        "win32gui",
        types.SimpleNamespace(
            ExtractIconEx=lambda *_args: ([999], []),
            GetDC=lambda _hwnd: 555,
            DrawIconEx=lambda *_args: calls.append("draw"),
            DestroyIcon=lambda _hicon: calls.append("destroy"),
        ),
    )
    monkeypatch.setitem(sys.modules, "win32ui", types.SimpleNamespace(CreateDCFromHandle=lambda _handle: FakeDC(), CreateBitmap=FakeBitmap))
    monkeypatch.setitem(sys.modules, "win32con", types.SimpleNamespace(DI_NORMAL=3))
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")
    image_module.frombuffer = lambda *_args: FakeImage()
    pil_module.Image = image_module
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)

    assert icon_extractor.extract_icon_with_win32("app.exe", str(out), size=2) is True
    assert out.read_bytes() == b"rendered"
    assert calls == ["select", "draw", "destroy", "mem-delete", "dc-delete"]


def test_extract_icon_with_win32_returns_false_without_icons(monkeypatch):
    monkeypatch.setitem(sys.modules, "win32gui", types.SimpleNamespace(ExtractIconEx=lambda *_args: ([], [])))
    monkeypatch.setitem(sys.modules, "win32ui", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "win32con", types.SimpleNamespace(DI_NORMAL=3))
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")
    pil_module.Image = image_module
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)

    assert icon_extractor.extract_icon_with_win32("app.exe", "out.png") is False
