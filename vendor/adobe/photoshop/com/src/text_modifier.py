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
from font_resolver import build_font_index, resolve_font
from adaptive_lab import LabDocument
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
) -> ModifyResult:
    """修改单个文字图层"""
    # 1. 获取图层当前状态
    ti = layer.TextItem
    current_text = ti.Contents.strip()
    current_font = ti.Font
    current_size = float(ti.Size)

    try:
        current_tracking = float(ti.Tracking)
    except Exception:
        current_tracking = 0.0

    bounds = ps.get_layer_bounds(layer)
    current_height = bounds[3] - bounds[1]

    # 2. 构造 TextLayerRecord
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
        size_px=current_size,
        tracking=current_tracking,
        auto_leading=True,
        leading_pt=-1.0,
        leading_px=-1.0,
        bounds_left=0.0,
        bounds_top=0.0,
        bounds_right=0.0,
        bounds_bottom=0.0,
        bounds_h_px=current_height,
        dpi=72.0,
        enabled=True,
        new_text=mapping.new_text if mapping.new_text else None,
        new_font_family=mapping.font if mapping.font else None,
        new_font_weight='',
        new_font_ps=None,
    )

    # 3. 检查是否需要修改
    if not record.new_text and not record.new_font_family:
        return _adapted_params_to_result(record, None)

    # 4. 创建临时 logger
    log_path = os.path.join(tempfile.gettempdir(), f'modify_{os.getpid()}.log')
    logger = PSALogger(log_path)

    # 5. 构建字体索引并解析目标字体
    font_index = build_font_index(ps.app)

    if record.new_font_family:
        resolved_font = resolve_font(
            font_index=font_index,
            target_family=record.new_font_family,
            target_weight_kw='',
            preserve_italic=False,
            original_ps_name=record.font,
        )
        if resolved_font:
            record.new_font_ps = resolved_font
        else:
            logger.log_warning(f'Font family not found: {record.new_font_family}, using original')
            record.new_font_ps = record.font

    # 6. 调用自适应算法
    new_font_ps = record.new_font_ps or record.font
    new_text = record.new_text or record.text
    # 记录当前活跃文档，lab 关闭后恢复
    try:
        _active_doc_before_lab = ps.app.ActiveDocument
    except Exception:
        _active_doc_before_lab = None
    try:
        with LabDocument(ps.app, 72.0) as lab:
            adapted_params = lab.find_adapted_params(record, new_font_ps, new_text, logger)
    except Exception as exc:
        logger.log_error('Adaptive algorithm failed', exc)
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
            message=str(exc),
            fit_status='error',
        )
    finally:
        # lab 关闭后恢复之前的活跃文档
        if _active_doc_before_lab is not None:
            try:
                ps.app.ActiveDocument = _active_doc_before_lab
            except Exception:
                pass

    # 7. 应用结果到图层
    if adapted_params and adapted_params.converged:
        try:
            ti.Font = adapted_params.font_ps
            ti.Size = adapted_params.size_pt

            if adapted_params.auto_leading:
                ti.UseAutoLeading = True
            else:
                ti.UseAutoLeading = False
                ti.Leading = adapted_params.leading_pt

            if hasattr(ti, 'Tracking'):
                ti.Tracking = adapted_params.tracking

            if record.new_text:
                ti.Contents = record.new_text
        except Exception as exc:
            logger.log_error('Failed to apply params', exc)
            adapted_params.converged = False

    # 8. 转换为 ModifyResult
    return _adapted_params_to_result(record, adapted_params)
