"""
工单工作流：扫描和修改
"""
from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

# 核心模块
from text_models import TextLayerRecord, AdaptedParams
from document_scanner import scan_document
from text_logger import PSALogger
from font_resolver import build_font_index, resolve_font
from adaptive_lab import LabDocument
from config_reader import TextMapping


@dataclass
class TicketScanRow:
    """扫描结果行"""
    layer_id: int
    source_psd: str
    artboard: str
    layer_name: str
    line_count: int
    alignment: str
    font_size: float
    tracking: float
    width_px: float
    height_px: float
    source_font: str
    source_font_family: str
    source_font_weight: str
    raw_text: str
    original_text: str
    layer_obj: object | None = None
    smart_object_layer_id: int = 0
    smart_object_name: str = ""
    smart_object_inner_layer_name: str = ""


def scan_document_for_ticket(
    ps,
    doc,
    source_psd: str,
    progress_callback: Callable[[dict], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> list[TicketScanRow]:
    """扫描文档生成工单"""
    # 创建临时 logger
    log_path = os.path.join(tempfile.gettempdir(), f'scan_{os.getpid()}.log')
    logger = PSALogger(log_path)

    # 调用核心扫描，实时触发进度回调
    try:
        records = scan_document(ps.app, doc, logger, progress_callback=progress_callback)
    except Exception as exc:
        if 'CANCELLED' in str(exc):
            raise RuntimeError('MEDIATOOLS_SCAN_CANCELLED')
        raise

    # 转换为 TicketScanRow 格式
    scan_rows = []
    normal_count = 0
    smart_count = 0
    for rec in records:
        if cancel_check and cancel_check():
            raise RuntimeError('MEDIATOOLS_SCAN_CANCELLED')

        parts = rec.layer_path.split('/')
        artboard = parts[0] if len(parts) > 1 else '(无画板)'

        font_family = rec.font.split('-')[0] if '-' in rec.font else rec.font
        font_weight = rec.font.split('-')[1] if '-' in rec.font else 'Regular'

        is_so = rec.in_smart_object
        if is_so:
            smart_count += 1
        else:
            normal_count += 1

        scan_rows.append(TicketScanRow(
            layer_id=rec.layer_id,
            source_psd=os.path.basename(source_psd),
            artboard=artboard,
            layer_name=rec.layer_name,
            line_count=rec.text.count('\n') + 1,
            alignment='left',
            font_size=rec.size_pt,
            tracking=rec.tracking,
            width_px=0.0,
            height_px=rec.bounds_h_px,
            source_font=rec.font,
            source_font_family=font_family,
            source_font_weight=font_weight,
            raw_text=rec.text,
            original_text=rec.text.replace('\r', ' ').replace('\n', ' ').strip(),
            layer_obj=None,
            smart_object_layer_id=rec.so_layer_id if is_so else 0,
            smart_object_name=rec.so_psb_name if is_so else '',
            smart_object_inner_layer_name=rec.layer_name if is_so else '',
        ))

    return scan_rows


def modify_smart_object_text_layer(ps, parent_doc, row: TicketScanRow, mapping: TextMapping, params) -> Any:
    """修改智能对象内的文字图层"""
    from text_modifier import ModifyResult, modify_text_layer

    smart_layer_id = int(getattr(row, 'smart_object_layer_id', 0) or 0)
    raw_text = getattr(row, 'raw_text', None) or getattr(row, 'original_text', '')

    if not smart_layer_id:
        return ModifyResult(
            layer_name=row.layer_name,
            original_text=raw_text,
            new_text=raw_text,
            original_font_size=row.font_size,
            final_font_size=row.font_size,
            original_tracking=row.tracking,
            final_tracking=row.tracking,
            original_width=row.width_px,
            final_width=row.width_px,
            original_height=row.height_px,
            final_height=row.height_px,
            success=False,
            message='Smart object layer id is missing',
            fit_status='error',
        )

    # 激活父文档
    try:
        parent_doc.Activate()
    except Exception:
        pass

    # 查找 SO 图层
    smart_layer = ps.find_layer_by_id(parent_doc, smart_layer_id)
    if smart_layer is None or not ps.is_smart_object_layer(smart_layer):
        return ModifyResult(
            layer_name=row.layer_name,
            original_text=raw_text,
            new_text=raw_text,
            original_font_size=row.font_size,
            final_font_size=row.font_size,
            original_tracking=row.tracking,
            final_tracking=row.tracking,
            original_width=row.width_px,
            final_width=row.width_px,
            original_height=row.height_px,
            final_height=row.height_px,
            success=False,
            message=f'Smart object layer id {smart_layer_id} not found',
            fit_status='error',
        )

    # 进入 SO
    smart_doc = None
    try:
        smart_doc = ps.open_smart_object_contents_by_id(smart_layer_id)
        target_layer = ps.find_layer_by_id(smart_doc, row.layer_id)

        if target_layer is None:
            return ModifyResult(
                layer_name=row.layer_name,
                original_text=raw_text,
                new_text=raw_text,
                original_font_size=row.font_size,
                final_font_size=row.font_size,
                original_tracking=row.tracking,
                final_tracking=row.tracking,
                original_width=row.width_px,
                final_width=row.width_px,
                original_height=row.height_px,
                final_height=row.height_px,
                success=False,
                message=f'Text layer id {row.layer_id} inside smart object not found',
                fit_status='error',
            )

        # 调用修改
        result = modify_text_layer(ps, target_layer, mapping, params, skip_temp_doc=True)

        # 保存 SO 文档
        if result.success:
            smart_doc.Save()

        return result

    finally:
        if smart_doc is not None:
            try:
                ps.close_document(smart_doc, save=False)
            except Exception:
                pass
            try:
                parent_doc.Activate()
            except Exception:
                pass
