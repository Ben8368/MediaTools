"""
文字修改核心逻辑
"""
from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from typing import Any

from text_models import TextLayerRecord, AdaptedParams
from text_logger import PSALogger
from text_utils import safe_get, pt_to_px
from font_resolver import build_font_index, resolve_font
from adaptive_lab import LabDocument
from psa_applier import process_layer, resolve_font_for_record
from config_reader import TextMapping


@dataclass
class AdjustParams:
    """自适应调整参数（兼容旧接口）"""
    tracking_min: float = -50
    tracking_step: float = 5
    font_size_min_ratio: float = 0.75
    tolerance: float = 0.05
    font_size_max_ratio: float = 1.25
    font_size_binary_iterations: int = 15
    font_size_refine_ratio: float = 0.05
    font_size_refine_iterations: int = 5
    tracking_delta: float = 40
    tracking_binary_iterations: int = 6
    leading_min_ratio: float = 0.9
    leading_max_ratio: float = 1.1
    leading_binary_iterations: int = 6
    height_tolerance: float = 0.08


@dataclass
class ModifyResult:
    """单次修改的结果"""
    layer_name: str
    original_text: str
    new_text: str
    original_font_size: float
    final_font_size: float
    original_tracking: float
    final_tracking: float
    original_width: float
    final_width: float
    original_height: float
    final_height: float
    success: bool
    message: str = ""
    original_leading: float = -1.0
    final_leading: float = -1.0
    score: float = 0.0
    fit_document_resolution: float = 0.0
    fit_status: str = ""


def _adapted_params_to_result(record: TextLayerRecord, params: AdaptedParams | None) -> ModifyResult:
    """转换结果格式"""
    if params is None:
        return ModifyResult(
            layer_name=record.layer_name,
            original_text=record.text,
            new_text=record.text,
            original_font_size=record.size_pt,
            final_font_size=record.size_pt,
            original_tracking=record.tracking,
            final_tracking=record.tracking,
            original_width=0.0,
            final_width=0.0,
            original_height=record.bounds_h_px,
            final_height=record.bounds_h_px,
            success=False,
            message='skipped (unchanged)',
            original_leading=record.leading_pt,
            final_leading=record.leading_pt,
            fit_status='skipped',
        )

    return ModifyResult(
        layer_name=record.layer_name,
        original_text=record.text,
        new_text=record.new_text or record.text,
        original_font_size=record.size_pt,
        final_font_size=params.size_pt,
        original_tracking=record.tracking,
        final_tracking=params.tracking,
        original_width=0.0,
        final_width=0.0,
        original_height=record.bounds_h_px,
        final_height=params.final_bounds_h_px,
        success=params.converged,
        message='converged' if params.converged else 'not converged',
        original_leading=record.leading_pt,
        final_leading=params.leading_pt,
        fit_status='ok' if params.converged else 'overflow',
    )


def modify_text_layer(
    ps,
    layer,
    mapping: TextMapping,
    params: AdjustParams,
    skip_temp_doc: bool = False,
    font_metrics: dict = None,
    font_index: dict = None,
) -> ModifyResult:
    """修改单个文字图层

    Uses PSA's process_layer() for calibration (Method A), verify+refine
    (Method B), and SO boundary protection.
    """
    ti = layer.TextItem
    current_text = ti.Contents.strip()
    current_font = ti.Font
    current_size = float(ti.Size)

    try:
        current_tracking = float(ti.Tracking)
    except Exception:
        current_tracking = 0.0

    # Read actual values from the layer — NOT hardcoded
    auto_leading = bool(safe_get(ti, "UseAutoLeading", True))
    leading_pt = 0.0
    if not auto_leading:
        try:
            leading_pt = float(safe_get(ti, "Leading", 0.0) or 0.0)
        except Exception:
            leading_pt = 0.0

    # Read document DPI from the active document
    try:
        dpi = float(safe_get(ps.app.ActiveDocument, "Resolution", 72.0))
    except Exception:
        dpi = 72.0

    bounds = ps.get_layer_bounds(layer)
    current_height = bounds[3] - bounds[1]

    size_px = pt_to_px(current_size, dpi)
    leading_px = pt_to_px(leading_pt, dpi)

    record = TextLayerRecord(
        layer_id=ps.get_layer_id(layer),
        layer_name=layer.Name,
        layer_path=layer.Name,
        in_smart_object=False,
        so_layer_id=0,
        so_layer_path='',
        so_psb_name='',
        so_chain=[],
        text=current_text,
        font=current_font,
        size_pt=current_size,
        size_px=size_px,
        tracking=current_tracking,
        auto_leading=auto_leading,
        leading_pt=leading_pt,
        leading_px=leading_px,
        bounds_left=0.0,
        bounds_top=0.0,
        bounds_right=0.0,
        bounds_bottom=0.0,
        bounds_h_px=current_height,
        dpi=dpi,
        enabled=True,
        new_text=mapping.new_text if mapping.new_text else None,
        new_font_family=mapping.font if mapping.font else None,
        new_font_weight='',
        new_font_ps=None,
    )

    # Check if modification is needed
    if not record.new_text and not record.new_font_family:
        return _adapted_params_to_result(record, None)

    # Build font index (once, or reuse caller-provided)
    if font_index is None:
        font_index = build_font_index(ps.app)

    # Resolve target font
    record.new_font_ps = resolve_font_for_record(record, font_index,
                                                  PSALogger(os.path.join(tempfile.gettempdir(), f'modify_{os.getpid()}.log')))

    # Open lab with correct DPI, delegate to PSA's process_layer
    log_path = os.path.join(tempfile.gettempdir(), f'modify_{os.getpid()}.log')
    logger = PSALogger(log_path)

    try:
        _active_doc_before_lab = ps.app.ActiveDocument
    except Exception:
        _active_doc_before_lab = None

    adapted_params = None
    try:
        with LabDocument(ps.app, dpi) as lab:
            adapted_params = process_layer(ps.app, ps.app.ActiveDocument, record,
                                           lab, logger, in_so=False)
    except Exception as exc:
        logger.log_error('Adaptive algorithm failed', exc)
        adapted_params = None
    finally:
        if _active_doc_before_lab is not None:
            try:
                ps.app.ActiveDocument = _active_doc_before_lab
            except Exception:
                pass
        logger.close()

    if adapted_params is None:
        return ModifyResult(
            layer_name=record.layer_name,
            original_text=record.text,
            new_text=record.text,
            original_font_size=record.size_pt,
            final_font_size=record.size_pt,
            original_tracking=record.tracking,
            final_tracking=record.tracking,
            original_width=0.0,
            final_width=0.0,
            original_height=record.bounds_h_px,
            final_height=record.bounds_h_px,
            success=False,
            message='Adaptive algorithm failed',
            fit_status='error',
        )

    return _adapted_params_to_result(record, adapted_params)
