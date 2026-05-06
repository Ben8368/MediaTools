"""
工单 JSON ↔ Excel 转换模块
- JSON 导出为 Excel 供用户审阅
- Excel 导入更新 JSON
"""

import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from ticket_json import Ticket, TicketTask


# 用户审阅时需要看到的列（中文列名）
REVIEW_COLUMNS = [
    ("artboard_name", "画板"),
    ("layer_name", "图层名"),
    ("original_text", "原文"),
    ("target_text", "译文"),
    ("source_font", "原字体"),
    ("target_font", "目标字体"),
    ("font_size", "字号"),
    ("tracking", "字间距"),
    ("status", "状态"),
    ("notes", "备注"),
    ("ai_confidence", "AI信心"),
    ("ai_notes", "AI备注"),
    ("user_approved", "已审核"),
]

# Excel 中可编辑的列（用户可以修改）
EDITABLE_COLUMNS = {"target_text", "target_font", "status", "notes", "user_approved"}


def export_ticket_to_excel(ticket: Ticket, excel_path: str) -> None:
    """
    将工单 JSON 导出为 Excel，供用户审阅和编辑。
    
    Args:
        ticket: Ticket 对象
        excel_path: 输出 Excel 路径
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "工单审阅"

    # 写入表头
    headers = [cn_name for _, cn_name in REVIEW_COLUMNS]
    ws.append(headers)

    # 表头样式
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 写入数据
    for task in ticket.tasks:
        row = []
        for field_name, _ in REVIEW_COLUMNS:
            value = getattr(task, field_name, "")
            # 布尔值转换为 ✓ / ✗
            if isinstance(value, bool):
                value = "✓" if value else "✗"
            # 浮点数格式化
            elif isinstance(value, float):
                if field_name in ("font_size", "tracking"):
                    value = f"{value:.2f}"
                elif field_name == "ai_confidence":
                    value = f"{value:.0%}" if value > 0 else ""
            row.append(value)
        ws.append(row)

    # 列宽自动调整
    for col_idx, (field_name, cn_name) in enumerate(REVIEW_COLUMNS, start=1):
        max_len = len(cn_name)
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            cell_value = str(row[0].value or "")
            max_len = max(max_len, len(cell_value))
        ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = min(max_len + 2, 50)

    # 可编辑列高亮（淡黄色）
    editable_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    for col_idx, (field_name, _) in enumerate(REVIEW_COLUMNS, start=1):
        if field_name in EDITABLE_COLUMNS:
            for row in range(2, ws.max_row + 1):
                ws.cell(row, col_idx).fill = editable_fill

    # 保存
    os.makedirs(os.path.dirname(excel_path) if os.path.dirname(excel_path) else ".", exist_ok=True)
    wb.save(excel_path)
    print(f"  [OK] Excel 已导出: {excel_path}")


def import_excel_to_ticket(excel_path: str, original_ticket: Ticket) -> Ticket:
    """
    从 Excel 读取用户编辑的内容，更新原 Ticket 对象。
    
    Args:
        excel_path: Excel 文件路径
        original_ticket: 原始 Ticket 对象
    
    Returns:
        更新后的 Ticket 对象
    """
    wb = load_workbook(excel_path, read_only=True)
    ws = wb.active

    # 读取表头，建立列索引
    headers = [cell.value for cell in ws[1]]
    col_map = {}
    for idx, header in enumerate(headers):
        for field_name, cn_name in REVIEW_COLUMNS:
            if header == cn_name:
                col_map[field_name] = idx
                break

    # 读取数据行，更新 tasks
    updated_tasks = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=0):
        if row_idx >= len(original_ticket.tasks):
            print(f"  [warn] Excel 行数超过原工单，跳过多余行")
            break

        task = original_ticket.tasks[row_idx]

        # 只更新可编辑列
        for field_name in EDITABLE_COLUMNS:
            if field_name not in col_map:
                continue
            col_idx = col_map[field_name]
            if col_idx >= len(row):
                continue
            value = row[col_idx]

            # 布尔值转换
            if field_name == "user_approved":
                if value in ("✓", "是", "yes", "true", "True", True, 1):
                    value = True
                else:
                    value = False

            # 字符串字段
            elif isinstance(getattr(task, field_name), str):
                value = str(value or "").strip()

            setattr(task, field_name, value)

        updated_tasks.append(task)

    wb.close()

    # 返回更新后的 Ticket
    original_ticket.tasks = updated_tasks
    print(f"  [OK] Excel 已导入，更新了 {len(updated_tasks)} 条任务")
    return original_ticket


def auto_sync_excel_to_json(json_path: str, excel_path: str) -> bool:
    """
    自动检测 Excel 文件变化，同步到 JSON。
    
    Args:
        json_path: JSON 工单路径
        excel_path: Excel 审阅文件路径
    
    Returns:
        是否有更新
    """
    if not os.path.exists(excel_path):
        return False
    if not os.path.exists(json_path):
        return False

    # 比较修改时间
    json_mtime = os.path.getmtime(json_path)
    excel_mtime = os.path.getmtime(excel_path)

    if excel_mtime > json_mtime:
        print(f"  [sync] 检测到 Excel 更新，同步到 JSON...")
        from ticket_json import load_ticket_json, save_ticket_json
        ticket = load_ticket_json(json_path)
        updated_ticket = import_excel_to_ticket(excel_path, ticket)
        save_ticket_json(updated_ticket, json_path)
        return True

    return False
