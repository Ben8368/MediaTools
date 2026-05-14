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
from config_reader import TextMapping, horizontal_outer_strip


def _normalize_ticket_layer_text(value: str) -> str:
    """将图层文字中的段落分隔统一为换行符 \\n，再写入工单 JSON（与 Ai 翻译一致）。"""
    if not value:
        return ""
    t = value.replace("\r\n", "\n").replace("\r", "\n")
    return horizontal_outer_strip(t)


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
    so_chain: list = None

    def __post_init__(self):
        if self.so_chain is None:
            self.so_chain = []


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

        norm = _normalize_ticket_layer_text(rec.text)
        line_breaks = norm.count("\n") if norm else 0

        scan_rows.append(TicketScanRow(
            layer_id=rec.layer_id,
            source_psd=os.path.basename(source_psd),
            artboard=artboard,
            layer_name=rec.layer_name,
            line_count=line_breaks + 1 if norm else 1,
            alignment='left',
            font_size=rec.size_pt,
            tracking=rec.tracking,
            width_px=0.0,
            height_px=rec.bounds_h_px,
            source_font=rec.font,
            source_font_family=font_family,
            source_font_weight=font_weight,
            raw_text=norm,
            original_text=norm,
            layer_obj=None,
            smart_object_layer_id=rec.so_layer_id if is_so else 0,
            smart_object_name=rec.so_psb_name if is_so else '',
            smart_object_inner_layer_name=rec.layer_name if is_so else '',
            so_chain=rec.so_chain if is_so else [],
        ))

    return scan_rows


def modify_smart_object_text_layer(ps, parent_doc, row: TicketScanRow, mapping: TextMapping, params) -> Any:
    """修改智能对象内的文字图层

    Supports multi-level SO nesting via so_chain. Adds canvas expansion
    (boundary protection) after each SO modification to prevent text clipping.
    """
    from text_modifier import ModifyResult, modify_text_layer
    from text_utils import expand_so_canvas

    smart_layer_id = int(getattr(row, 'smart_object_layer_id', 0) or 0)
    raw_text = getattr(row, 'raw_text', None) or getattr(row, 'original_text', '')
    so_chain = getattr(row, 'so_chain', None) or []

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

    # Activate parent document
    try:
        parent_doc.Activate()
    except Exception:
        pass

    # Find outermost SO layer
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

    result = None
    opened_docs = []  # Stack of (doc, layer_id) for cleanup and canvas expansion

    try:
        if so_chain and len(so_chain) > 1:
            # Multi-level SO: navigate through each SO in the chain
            # so_chain[0] is the outermost (already found as smart_layer)
            # so_chain[1:] are nested SOs to enter sequentially
            current_doc = parent_doc

            for depth, entry in enumerate(so_chain):
                so_id = entry.get("layer_id")
                if so_id is None:
                    continue

                # Find the SO layer at this depth
                if depth == 0:
                    so_layer = smart_layer
                else:
                    so_layer = ps.find_layer_by_id(current_doc, so_id)

                if so_layer is None:
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
                        message=f'SO layer id {so_id} not found at depth {depth}',
                        fit_status='error',
                    )

                # Enter this SO
                inner_doc = ps.open_smart_object_contents_by_id(so_id)
                opened_docs.append((inner_doc, so_id))

                if depth == len(so_chain) - 1:
                    # Innermost SO: find and modify the text layer
                    current_doc = inner_doc
                    target_layer = ps.find_layer_by_id(current_doc, row.layer_id)

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
                            message=f'Text layer id {row.layer_id} inside nested SO not found',
                            fit_status='error',
                        )

                    result = modify_text_layer(ps, target_layer, mapping, params, skip_temp_doc=True)
                else:
                    current_doc = inner_doc
        else:
            # Single-level SO (original path, or legacy ticket without chain)
            smart_doc = ps.open_smart_object_contents_by_id(smart_layer_id)
            opened_docs.append((smart_doc, smart_layer_id))

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

            result = modify_text_layer(ps, target_layer, mapping, params, skip_temp_doc=True)

        # Boundary protection: expand canvas at each SO level (innermost first)
        if result and result.success:
            if getattr(result, 'fit_status', '') == 'fallback':
                # 直接套用未做自适应缩排，译文更长时略放大画板，降低裁切概率
                oh = max(float(getattr(result, 'original_height', 0) or 0), 0.1)
                fh = max(float(getattr(result, 'final_height', 0) or 0), 0.1)
                growth = max(1.2, fh / oh)
                raw = getattr(result, 'new_text', '') or ''
                master = getattr(result, 'original_text', '') or ''
                char_growth = (len(raw) + 1) / (len(master) + 1)
                expansion = max(1.45, min(3.0, 1.15 * max(growth, char_growth ** 0.35)))
            else:
                size_ratio = result.final_font_size / max(row.font_size, 0.1)
                expansion = max(1.2, min(3.0, size_ratio * 1.1))

            for so_doc, so_id in reversed(opened_docs):
                try:
                    ps.app.ActiveDocument = so_doc
                    expand_so_canvas(ps.app, so_doc, expansion)
                except Exception:
                    pass

            # Save SO documents (innermost first)
            for so_doc, so_id in reversed(opened_docs):
                try:
                    so_doc.Save()
                except Exception:
                    pass

        return result

    finally:
        # Close all SO documents (outermost first, or just all)
        for so_doc, so_id in opened_docs:
            try:
                ps.close_document(so_doc, save=False)
            except Exception:
                pass
        try:
            parent_doc.Activate()
        except Exception:
            pass
