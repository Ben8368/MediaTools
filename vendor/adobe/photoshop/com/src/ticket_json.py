"""
工单 JSON 格式模块
- 主格式：ticket.json（程序读写）
- 审阅格式：ticket_review.xlsx（用户查看/编辑）
- 支持双向转换
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# ──────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────

@dataclass
class TicketTask:
    """工单中的单个任务条目"""
    layer_id: int
    artboard_name: str
    layer_name: str
    output_name: str
    language: str
    line_count: int
    alignment: str
    font_size: float
    tracking: float
    width_px: float
    height_px: float
    source_psd: str
    source_font: str
    original_text: str
    target_text: str
    target_font: str
    status: str = "pending"        # pending / confirmed / skip / done / error
    notes: str = ""
    ai_confidence: float = 0.0    # AI 生成时的置信度 (0.0~1.0)
    ai_notes: str = ""            # AI 生成时的备注
    user_approved: bool = False   # 用户是否审核确认

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "TicketTask":
        # 兼容老字段
        return TicketTask(
            layer_id=int(d.get("layer_id", 0)),
            artboard_name=str(d.get("artboard_name", "")),
            layer_name=str(d.get("layer_name", "")),
            output_name=str(d.get("output_name", "")),
            language=str(d.get("language", "")),
            line_count=int(d.get("line_count", 1)),
            alignment=str(d.get("alignment", "left")),
            font_size=float(d.get("font_size", 12.0)),
            tracking=float(d.get("tracking", 0.0)),
            width_px=float(d.get("width_px", 0.0)),
            height_px=float(d.get("height_px", 0.0)),
            source_psd=str(d.get("source_psd", "")),
            source_font=str(d.get("source_font", "")),
            original_text=str(d.get("original_text", "")),
            target_text=str(d.get("target_text", "")),
            target_font=str(d.get("target_font", "")),
            status=str(d.get("status", "pending")),
            notes=str(d.get("notes", "")),
            ai_confidence=float(d.get("ai_confidence", 0.0)),
            ai_notes=str(d.get("ai_notes", "")),
            user_approved=bool(d.get("user_approved", False)),
        )


@dataclass
class TicketMeta:
    """工单元数据"""
    version: str = "2.0"
    created_at: str = ""
    created_by: str = "manual"      # manual / ai / scan
    source_psd: str = ""
    ai_analysis: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")


@dataclass
class Ticket:
    """完整工单"""
    meta: TicketMeta
    tasks: list[TicketTask]

    def to_dict(self) -> dict:
        return {
            "meta": asdict(self.meta),
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @staticmethod
    def from_dict(d: dict) -> "Ticket":
        meta_d = d.get("meta", {})
        meta = TicketMeta(
            version=meta_d.get("version", "2.0"),
            created_at=meta_d.get("created_at", ""),
            created_by=meta_d.get("created_by", "manual"),
            source_psd=meta_d.get("source_psd", ""),
            ai_analysis=meta_d.get("ai_analysis", {}),
        )
        tasks = [TicketTask.from_dict(t) for t in d.get("tasks", [])]
        return Ticket(meta=meta, tasks=tasks)


# ──────────────────────────────────────────────
# JSON 读写
# ──────────────────────────────────────────────

def load_ticket_json(path: str) -> Ticket:
    """读取工单 JSON"""
    with open(path, encoding="utf-8") as f:
        return Ticket.from_dict(json.load(f))


def save_ticket_json(ticket: Ticket, path: str) -> None:
    """保存工单 JSON"""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ticket.to_dict(), f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# CSV → JSON 迁移（向后兼容）
# ──────────────────────────────────────────────

def load_ticket_csv_as_ticket(csv_path: str) -> Ticket:
    """
    读取旧格式 CSV 工单，转换为 Ticket 对象。
    支持新旧两种表头。
    """
    import csv as _csv

    tasks = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f)
        for i, row in enumerate(reader):
            # 兼容新旧表头（artboard vs artboard_name）
            artboard_name = row.get("artboard_name") or row.get("artboard", "")
            try:
                task = TicketTask(
                    layer_id=int(row.get("layer_id") or 0),
                    artboard_name=artboard_name.strip(),
                    layer_name=(row.get("layer_name", "")).strip(),
                    output_name=(row.get("output_name", "")).strip(),
                    language=(row.get("language", "")).strip(),
                    line_count=int(row.get("line_count") or 1),
                    alignment=(row.get("alignment", "left")).strip(),
                    font_size=float(row.get("font_size") or 12.0),
                    tracking=float(row.get("tracking") or 0.0),
                    width_px=float(row.get("width_px") or 0.0),
                    height_px=float(row.get("height_px") or 0.0),
                    source_psd=(row.get("source_psd", "")).strip(),
                    source_font=(row.get("source_font", "")).strip(),
                    original_text=(row.get("original_text", "")).strip(),
                    target_text=(row.get("target_text", "")).strip(),
                    target_font=(row.get("target_font", "")).strip(),
                    status=(row.get("status", "pending")).strip(),
                    notes=(row.get("notes", "")).strip(),
                )
                tasks.append(task)
            except Exception as e:
                print(f"  [warn] CSV 第 {i+2} 行解析失败: {e}")
                continue

    meta = TicketMeta(
        created_by="csv_import",
        source_psd=tasks[0].source_psd if tasks else "",
    )
    return Ticket(meta=meta, tasks=tasks)


# ──────────────────────────────────────────────
# Excel 导出（供用户审阅编辑）
# ──────────────────────────────────────────────

_EXCEL_COLUMNS = [
    ("layer_id",       "图层ID"),
    ("artboard_name",  "画板"),
    ("layer_name",     "图层名"),
    ("output_name",    "输出文件"),
    ("language",       "语言"),
    ("original_text",  "原文"),
    ("target_text",    "译文"),
    ("target_font",    "目标字体"),
    ("source_font",    "原字体"),
    ("font_size",      "字号"),
    ("tracking",       "字间距"),
    ("status",         "状态"),
    ("ai_confidence",  "AI置信度"),
    ("ai_notes",       "AI备注"),
    ("notes",          "备注"),
    ("user_approved",  "已审核"),
]

_USER_EDITABLE = {"target_text", "target_font", "status", "notes", "user_approved"}


def export_to_excel(ticket: Ticket, excel_path: str) -> None:
    """
    导出工单为 Excel，供用户审阅和编辑。
    可编辑列：译文、目标字体、状态、备注、已审核
    """
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "工单"

    # 颜色定义
    HEADER_FILL   = PatternFill("solid", fgColor="1F3864")   # 深蓝
    EDITABLE_FILL = PatternFill("solid", fgColor="E8F4FD")   # 浅蓝（可编辑）
    ALT_FILL      = PatternFill("solid", fgColor="F5F5F5")   # 浅灰（交替行）
    WHITE_FILL    = PatternFill("solid", fgColor="FFFFFF")

    thin_border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    # 写表头
    headers_en = [col[0] for col in _EXCEL_COLUMNS]
    headers_zh = [col[1] for col in _EXCEL_COLUMNS]
    ws.append(headers_zh)

    for col_idx, (en_name, zh_name) in enumerate(_EXCEL_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = Font(color="FFFFFF", bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        # 标记可编辑列（在表头加 ✏）
        if en_name in _USER_EDITABLE:
            cell.value = f"✏ {zh_name}"

    ws.row_dimensions[1].height = 28

    # 写数据
    for row_idx, task in enumerate(ticket.tasks, start=2):
        row_data = []
        for en_name, _ in _EXCEL_COLUMNS:
            val = getattr(task, en_name, "")
            if isinstance(val, bool):
                val = "是" if val else ""
            elif isinstance(val, float):
                val = round(val, 4)
            row_data.append(val)
        ws.append(row_data)

        # 交替行底色
        is_alt = (row_idx % 2 == 0)
        for col_idx, (en_name, _) in enumerate(_EXCEL_COLUMNS, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if en_name in _USER_EDITABLE:
                cell.fill = EDITABLE_FILL
            elif is_alt:
                cell.fill = ALT_FILL
            else:
                cell.fill = WHITE_FILL

    # 调整列宽
    col_widths = {
        "layer_id": 8,
        "artboard_name": 14,
        "layer_name": 20,
        "output_name": 16,
        "language": 10,
        "original_text": 30,
        "target_text": 30,
        "target_font": 18,
        "source_font": 18,
        "font_size": 8,
        "tracking": 8,
        "status": 12,
        "ai_confidence": 10,
        "ai_notes": 20,
        "notes": 20,
        "user_approved": 8,
    }
    for col_idx, (en_name, _) in enumerate(_EXCEL_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = col_widths.get(en_name, 12)

    # 冻结首行
    ws.freeze_panes = "A2"

    # 元数据 sheet
    ws_meta = wb.create_sheet("元数据")
    ws_meta.append(["字段", "值"])
    ws_meta.append(["版本", ticket.meta.version])
    ws_meta.append(["创建时间", ticket.meta.created_at])
    ws_meta.append(["创建者", ticket.meta.created_by])
    ws_meta.append(["源PSD", ticket.meta.source_psd])
    ws_meta.append(["总任务数", len(ticket.tasks)])
    ws_meta.append(["已确认", sum(1 for t in ticket.tasks if t.status == "confirmed")])
    ws_meta.append([""]); ws_meta.append(["说明", "✏ 标记的列可以编辑后导入"])

    os.makedirs(os.path.dirname(excel_path) if os.path.dirname(excel_path) else ".", exist_ok=True)
    wb.save(excel_path)
    print(f"  [excel] 已导出: {excel_path} ({len(ticket.tasks)} 条)")


# ──────────────────────────────────────────────
# Excel → JSON 导入（用户编辑后同步回来）
# ──────────────────────────────────────────────

def import_from_excel(excel_path: str, ticket: Ticket) -> Ticket:
    """
    读取用户编辑后的 Excel，更新 ticket 中的可编辑字段。
    以 layer_id + output_name 为 key 匹配。
    返回更新后的 Ticket（不修改原对象）。
    """
    import openpyxl

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel 为空")

    # 解析表头（去掉 ✏ 前缀，转回英文 key）
    zh_to_en = {zh: en for en, zh in _EXCEL_COLUMNS}
    raw_headers = [str(h).replace("✏ ", "").strip() if h else "" for h in rows[0]]
    headers_en = [zh_to_en.get(h, h) for h in raw_headers]

    # 建索引
    col_idx = {name: i for i, name in enumerate(headers_en)}

    def get(row, name):
        i = col_idx.get(name)
        if i is None or i >= len(row):
            return None
        v = row[i]
        return str(v).strip() if v is not None else ""

    # 建 task 查找 map
    task_map = {(t.layer_id, t.output_name): t for t in ticket.tasks}

    updated = 0
    for row in rows[1:]:
        try:
            lid = int(get(row, "layer_id") or 0)
            out = get(row, "output_name") or ""
            key = (lid, out)
            if key not in task_map:
                continue

            t = task_map[key]
            # 只更新可编辑字段
            new_target_text  = get(row, "target_text")
            new_target_font  = get(row, "target_font")
            new_status       = get(row, "status")
            new_notes        = get(row, "notes")
            new_approved_raw = get(row, "user_approved")

            if new_target_text  is not None: t.target_text  = new_target_text
            if new_target_font  is not None: t.target_font  = new_target_font
            if new_status       is not None: t.status       = new_status
            if new_notes        is not None: t.notes        = new_notes
            if new_approved_raw is not None:
                t.user_approved = new_approved_raw.lower() in ("是", "true", "yes", "1", "✓")

            updated += 1
        except Exception as e:
            print(f"  [warn] Excel 行解析失败: {e}")
            continue

    wb.close()
    print(f"  [excel] 已导入: {updated} 条更新")
    return ticket


# ──────────────────────────────────────────────
# 自动检测 Excel 变化并导入
# ──────────────────────────────────────────────

def watch_excel_and_sync(json_path: str, excel_path: str, poll_interval: float = 2.0) -> None:
    """
    监听 Excel 文件变化，自动同步回 JSON。
    按 Ctrl+C 停止。
    """
    import time

    last_mtime = None
    print(f"  [watch] 监听 {excel_path}")
    print(f"  [watch] 按 Ctrl+C 停止")
    try:
        while True:
            if os.path.exists(excel_path):
                mtime = os.path.getmtime(excel_path)
                if last_mtime is None:
                    last_mtime = mtime
                elif mtime != last_mtime:
                    print(f"  [watch] 检测到变化，正在同步...")
                    try:
                        ticket = load_ticket_json(json_path)
                        ticket = import_from_excel(excel_path, ticket)
                        save_ticket_json(ticket, json_path)
                        print(f"  [watch] 已同步到 {json_path}")
                    except Exception as e:
                        print(f"  [watch] 同步失败: {e}")
                    last_mtime = mtime
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n  [watch] 已停止")
