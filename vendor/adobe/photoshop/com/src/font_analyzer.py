"""
PSD 文字内容和字体组合扫描模块

输出两个 CSV：
  1. {stem}_text_content.csv  - 文字内容清单（用户填写翻译和字体要求）
  2. {stem}_font_profiles.csv - 字体组合清单（供临时工程验证用）
"""

import csv
import os
from dataclasses import dataclass, field


@dataclass
class TextLayerInfo:
    """单个文字图层的信息"""
    artboard: str
    layer_name: str
    text_content: str
    font: str               # 完整 PostScript 名，如 ByteSans-Bold
    font_family: str        # 字体家族名，如 ByteSans
    size: float
    tracking: float
    alignment: str          # left / center / right
    is_multiline: bool


@dataclass
class FontProfile:
    """唯一字体组合（用于临时工程验证）"""
    font: str               # 完整 PostScript 名
    size: float
    tracking: float
    alignment: str
    is_multiline: bool
    occurrence_count: int = 0


# Photoshop COM 对齐方式枚举值
_ALIGNMENT_MAP = {
    1: "left",
    2: "right",
    3: "center",
    4: "justify",
    5: "justifyLeft",
    6: "justifyRight",
    7: "justifyAll",
}


def _get_font_family(postscript_name: str) -> str:
    """从 PostScript 名提取字体家族名，如 ByteSans-Bold -> ByteSans"""
    if "-" in postscript_name:
        return postscript_name.split("-")[0]
    return postscript_name


def _get_alignment(text_item) -> str:
    """获取文字对齐方式"""
    try:
        val = text_item.Justification
        return _ALIGNMENT_MAP.get(val, "left")
    except Exception:
        return "left"


def _get_tracking(text_item) -> float:
    """
    安全获取 tracking 值
    某些文字图层（如画板 03/04）访问 Tracking 会抛 COM 错误
    """
    try:
        return round(float(text_item.Tracking), 2)
    except Exception:
        return 0.0


def _is_multiline(text_content: str) -> bool:
    """判断是否多行"""
    return "\r" in text_content or "\n" in text_content


def _build_text_info(layer, artboard_name: str) -> TextLayerInfo | None:
    """从图层对象提取 TextLayerInfo，失败返回 None"""
    try:
        ti = layer.TextItem
        text = ti.Contents.strip()
        if not text:
            return None
        font = ti.Font
        return TextLayerInfo(
            artboard=artboard_name,
            layer_name=layer.Name,
            text_content=text,
            font=font,
            font_family=_get_font_family(font),
            size=round(float(ti.Size), 2),
            tracking=_get_tracking(ti),
            alignment=_get_alignment(ti),
            is_multiline=_is_multiline(ti.Contents),
        )
    except Exception:
        return None


def scan_psd(ps_connector, doc) -> tuple[list[TextLayerInfo], list[FontProfile]]:
    """
    扫描文档，返回：
      - text_layers: 所有文字图层信息列表
      - font_profiles: 唯一字体组合列表
    """
    text_layers: list[TextLayerInfo] = []
    artboards = ps_connector.collect_artboards(doc)

    if artboards:
        artboard_ids = set()
        for ab in artboards:
            try:
                artboard_ids.add(ab.id)
            except Exception:
                pass

        for ab in artboards:
            for layer in ps_connector.collect_text_layers_in_artboard(ab):
                info = _build_text_info(layer, ab.Name)
                if info:
                    text_layers.append(info)

        outside = ps_connector.collect_text_layers_outside_artboards(doc, artboard_ids)
        for layer in outside:
            info = _build_text_info(layer, "(画板外)")
            if info:
                text_layers.append(info)
    else:
        for layer in ps_connector.collect_text_layers(doc):
            info = _build_text_info(layer, "(无画板)")
            if info:
                text_layers.append(info)

    # 生成字体组合清单（去重）
    profile_map: dict[tuple, FontProfile] = {}
    for info in text_layers:
        key = (info.font, info.size, info.tracking, info.alignment, info.is_multiline)
        if key not in profile_map:
            profile_map[key] = FontProfile(
                font=info.font,
                size=info.size,
                tracking=info.tracking,
                alignment=info.alignment,
                is_multiline=info.is_multiline,
                occurrence_count=0,
            )
        profile_map[key].occurrence_count += 1

    font_profiles = sorted(profile_map.values(), key=lambda p: (-p.occurrence_count, p.font))

    return text_layers, font_profiles


def write_text_content_csv(text_layers: list[TextLayerInfo], output_path: str) -> None:
    """
    输出文字内容清单 CSV（用户填写翻译和字体要求）

    表头固定：artboard, layer_name, text_content, font, font_family, alignment, new_text, new_font
    不去重：保留所有图层，用 layer_name + artboard 精确定位
    """
    rows = []

    for info in text_layers:
        display_text = info.text_content.replace("\r", " ").replace("\n", " ")

        rows.append({
            "artboard": info.artboard,
            "layer_name": info.layer_name,
            "text_content": display_text,
            "font": info.font,
            "font_family": info.font_family,
            "alignment": info.alignment,
            "new_text": "",
            "new_font": "",
        })

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["artboard", "layer_name", "text_content", "font", "font_family", "alignment", "new_text", "new_font"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [OK] 文字内容清单: {output_path} ({len(rows)} 条)")


def write_font_profiles_csv(font_profiles: list[FontProfile], output_path: str) -> None:
    """输出字体组合清单 CSV（供临时工程验证用）"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "font", "size", "tracking", "alignment", "is_multiline", "occurrence_count"
        ])
        writer.writeheader()
        for p in font_profiles:
            writer.writerow({
                "font": p.font,
                "size": f"{p.size:.2f}",
                "tracking": f"{p.tracking:.2f}",
                "alignment": p.alignment,
                "is_multiline": str(p.is_multiline).lower(),
                "occurrence_count": p.occurrence_count,
            })

    print(f"  [OK] 字体组合清单: {output_path} ({len(font_profiles)} 种组合)")


def read_text_content_csv(filepath: str) -> list[dict]:
    """读取用户填写后的文字内容清单"""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 过滤掉 new_text 和 new_font 都为空的行（未填写）
            new_text = row.get("new_text", "").strip()
            new_font = row.get("new_font", "").strip()
            if not new_text and not new_font:
                continue
            rows.append({
                "text_content": row["text_content"].strip(),
                "font_family": row["font_family"].strip(),
                "new_text": new_text or None,
                "new_font": new_font or None,
            })
    return rows


def read_font_profiles_csv(filepath: str) -> list[FontProfile]:
    """读取字体组合清单"""
    profiles = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profiles.append(FontProfile(
                font=row["font"],
                size=float(row["size"]),
                tracking=float(row["tracking"]),
                alignment=row["alignment"],
                is_multiline=row["is_multiline"].lower() == "true",
                occurrence_count=int(row.get("occurrence_count", 0)),
            ))
    return profiles
