"""
CSV/Excel 映射表读取模块
支持 CSV 和 Excel(.xlsx) 格式
"""

import csv
import os
from dataclasses import dataclass
from typing import Optional

# 仅含「横向」空白，避免 str.strip() 去掉首尾换行导致多行文案行数变化
_HORIZONTAL_WS = frozenset(" \t\v\f\u00a0\u2007\u3000")


def horizontal_outer_strip(value: str) -> str:
    """去除首尾横向空白（空格、Tab 等），保留换行符与段落结构。"""
    if not value:
        return value
    s = str(value)
    start = 0
    end = len(s)
    while start < end and s[start] in _HORIZONTAL_WS:
        start += 1
    while end > start and s[end - 1] in _HORIZONTAL_WS:
        end -= 1
    return s[start:end]


@dataclass
class TextMapping:
    """单条文字替换映射"""
    match_mode: str           # "exact" 或 "contains"
    original_text: str        # 原文字（用于匹配图层）
    new_text: Optional[str] = None       # 替换后的新文字，None 表示保持原文字（只换字体）
    font: Optional[str] = None           # 字体名称：完整PS名(如NotoSans-Bold)或家族名(如NotoSans，自动判断字重)
    font_size: Optional[float] = None    # 字号，None 表示保持原字号
    tracking: Optional[float] = None     # 字间距，None 表示保持原值
    artboard: Optional[str] = None       # 画板名称，None 表示全局规则（匹配所有画板）

    def __post_init__(self):
        self.match_mode = self.match_mode.strip().lower()
        if self.match_mode not in ("exact", "contains"):
            raise ValueError(f"match_mode 必须是 'exact' 或 'contains'，当前值: '{self.match_mode}'")
        self.original_text = horizontal_outer_strip(str(self.original_text))

        # new_text 可以为 None（留空），表示保持原文字内容不变
        if self.new_text is not None:
            nt = horizontal_outer_strip(str(self.new_text))
            self.new_text = nt if nt else None

        if self.font is not None:
            self.font = self.font.strip() or None
        if self.font_size is not None:
            self.font_size = float(self.font_size)
        if self.tracking is not None:
            self.tracking = float(self.tracking)
        if self.artboard is not None:
            self.artboard = self.artboard.strip() or None


def _parse_optional_float(value) -> Optional[float]:
    """解析可选的浮点数字段，空字符串返回 None"""
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() == "none":
        return None
    return float(value)


def _parse_optional_str(value) -> Optional[str]:
    """解析可选的字符串字段，空字符串返回 None"""
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() == "none":
        return None
    return value


# new_text 改为可选列
REQUIRED_COLUMNS = {"match_mode", "original_text"}
OPTIONAL_COLUMNS = {"new_text", "font", "font_size", "tracking", "artboard"}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


def read_csv(filepath: str) -> list[TextMapping]:
    """读取 CSV 映射表"""
    mappings = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])

        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"CSV 缺少必需列: {missing}")

        for i, row in enumerate(reader, start=2):
            try:
                mapping = TextMapping(
                    match_mode=row["match_mode"],
                    original_text=row["original_text"],
                    new_text=_parse_optional_str(row.get("new_text")),
                    font=_parse_optional_str(row.get("font")),
                    font_size=_parse_optional_float(row.get("font_size")),
                    tracking=_parse_optional_float(row.get("tracking")),
                    artboard=_parse_optional_str(row.get("artboard")),
                )
                if not mapping.original_text:
                    continue  # 跳过空行
                mappings.append(mapping)
            except Exception as e:
                raise ValueError(f"CSV 第 {i} 行解析错误: {e}")

    return mappings


def read_excel(filepath: str) -> list[TextMapping]:
    """读取 Excel(.xlsx) 映射表"""
    import openpyxl

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel 文件为空")

    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    header_set = set(headers)

    missing = REQUIRED_COLUMNS - header_set
    if missing:
        raise ValueError(f"Excel 缺少必需列: {missing}")

    col_index = {name: idx for idx, name in enumerate(headers) if name in ALL_COLUMNS}
    mappings = []

    for i, row in enumerate(rows[1:], start=2):
        try:
            def get_val(col_name):
                idx = col_index.get(col_name)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            mapping = TextMapping(
                match_mode=str(get_val("match_mode") or "exact"),
                original_text=str(get_val("original_text") or ""),
                new_text=_parse_optional_str(get_val("new_text")),
                font=_parse_optional_str(get_val("font")),
                font_size=_parse_optional_float(get_val("font_size")),
                tracking=_parse_optional_float(get_val("tracking")),
                artboard=_parse_optional_str(get_val("artboard")),
            )
            if not mapping.original_text:
                continue  # 跳过空行
            mappings.append(mapping)
        except Exception as e:
            raise ValueError(f"Excel 第 {i} 行解析错误: {e}")

    wb.close()
    return mappings


def read_mappings(filepath: str) -> list[TextMapping]:
    """根据文件扩展名自动选择读取方式"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return read_csv(filepath)
    elif ext == ".xlsx":
        return read_excel(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，请使用 .csv 或 .xlsx")
