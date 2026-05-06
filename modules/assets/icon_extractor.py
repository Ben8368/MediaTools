"""从 EXE/ICO/DLL 文件中提取最高质量图标并保存为 PNG。"""

from __future__ import annotations

import struct
from pathlib import Path


def extract_icon_from_pe(exe_path: str, output_png: str) -> bool:
    """从 PE 资源段直接提取 256x256 PNG 格式图标（最高质量）。"""
    try:
        import pefile
    except ImportError:
        raise RuntimeError("需要安装 pefile: pip install pefile")

    pe = pefile.PE(exe_path)

    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        pe.close()
        return False

    data = pe.get_memory_mapped_image()

    try:
        for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if entry.struct.Id != 14:
                continue

            for sub_entry in entry.directory.entries:
                for res in sub_entry.directory.entries:
                    rva = res.data.struct.OffsetToData
                    size = res.data.struct.Size
                    group_data = data[rva : rva + size]

                    _, _, count = struct.unpack("<HHH", group_data[0:6])

                    icon_raw: dict[int, bytes] = {}
                    for icon_entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                        if icon_entry.struct.Id != 3:
                            continue
                        for icon_res_entry in icon_entry.directory.entries:
                            icon_id = icon_res_entry.id
                            for lang_res in icon_res_entry.directory.entries:
                                icon_rva = lang_res.data.struct.OffsetToData
                                icon_size = lang_res.data.struct.Size
                                icon_raw[icon_id] = data[icon_rva : icon_rva + icon_size]

                    for i in range(count):
                        offset = 6 + i * 14
                        w = group_data[offset]
                        h = group_data[offset + 1]
                        ref_id = struct.unpack("<H", group_data[offset + 12 : offset + 14])[0]

                        if w == 0 and h == 0 and ref_id in icon_raw:
                            raw = icon_raw[ref_id]
                            if raw[:4] == b"\x89PNG":
                                Path(output_png).write_bytes(raw)
                                return True
    finally:
        pe.close()

    return False


def extract_icon_with_win32(exe_path: str, output_png: str, size: int = 256) -> bool:
    """使用 Windows API 渲染图标为 PNG（fallback）。"""
    try:
        import win32con
        import win32gui
        import win32ui
        from PIL import Image
    except ImportError:
        raise RuntimeError("需要安装 pywin32 和 Pillow")

    icons_large, _ = win32gui.ExtractIconEx(exe_path, 0, 1)
    if not icons_large:
        return False

    hicon = icons_large[0]
    dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    mem_dc = dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(dc, size, size)
    mem_dc.SelectObject(bitmap)

    win32gui.DrawIconEx(mem_dc.GetSafeHdc(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)

    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)
    img = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)
    img.save(output_png)

    win32gui.DestroyIcon(hicon)
    mem_dc.DeleteDC()
    dc.DeleteDC()
    return True


def extract_icon(exe_path: str, output_png: str | None = None) -> dict:
    """
    从 EXE 文件提取图标，优先使用 PE 资源中的原始 PNG 格式。

    返回 {"ok": bool, "output": str, "method": str, "error": str}
    """
    if not Path(exe_path).is_file():
        return {"ok": False, "error": f"文件不存在: {exe_path}"}

    if output_png is None:
        output_png = str(Path(exe_path).with_suffix(".png"))

    try:
        if extract_icon_from_pe(exe_path, output_png):
            size = Path(output_png).stat().st_size
            return {"ok": True, "output": output_png, "method": "pe_png", "size": size}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        pass

    try:
        if extract_icon_with_win32(exe_path, output_png):
            size = Path(output_png).stat().st_size
            return {"ok": True, "output": output_png, "method": "win32_render", "size": size}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": "未能从该文件提取到图标"}
