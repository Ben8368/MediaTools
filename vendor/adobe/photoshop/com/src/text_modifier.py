"""
核心逻辑：文字替换 + 自适应调整
策略：字号是粗调，字间距(tracking)是微调
自适应算法：宽度优先（宽度和高度分别判断，取超出更多的维度）
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from config_reader import TextMapping
from ps_connector import PhotoshopConnector, psDoNotSaveChanges, psTypePixels


@dataclass
class AdjustParams:
    """自适应调整参数"""
    tracking_min: float = -50         # tracking 下限（保守值，保证可读性）
    tracking_step: float = 5          # tracking 每次调整步长
    font_size_min_ratio: float = 0.75  # 最小字号 = 原字号 × 此比例
    tolerance: float = 0.05           # 宽高容差，允许超出 5%
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


def _wait_ps(delay: float = 0.05):
    """等待 Photoshop 完成操作（COM 调用后需要短暂延迟）"""
    time.sleep(delay)


def _get_text_content(layer) -> str:
    """安全获取文字图层的文本内容"""
    try:
        return layer.TextItem.Contents
    except Exception:
        return ""


def _normalize_newlines(text: str) -> str:
    """统一换行符：CSV读取时\r可能变成\n，需要统一为\r（Photoshop使用\r）"""
    return text.replace('\r\n', '\r').replace('\n', '\r')


def _restore_text_state(text_item, original_text: str, original_font: str, original_font_size: float, original_tracking: float, original_leading: float = None) -> None:
    """在修改失败时尽量恢复图层原始状态，避免留下半成功结果。"""
    text_item.Contents = original_text
    text_item.Font = original_font
    text_item.Size = original_font_size
    text_item.Tracking = original_tracking
    if original_leading is not None:
        try:
            text_item.Leading = original_leading
        except Exception:
            pass
    _wait_ps()


def _capture_text_state(text_item) -> tuple[str, str | None, float, float, float]:
    """捕获当前文字状态，供失败时回滚。"""
    try:
        current_font = text_item.Font
    except Exception:
        current_font = None

    try:
        current_size = float(text_item.Size)
    except Exception:
        current_size = 12.0

    try:
        current_tracking = float(text_item.Tracking)
    except Exception:
        current_tracking = 0.0

    try:
        current_leading = float(text_item.Leading)
    except Exception:
        current_leading = -1.0  # PS 中 Auto Leading 通常是负值

    return text_item.Contents, current_font, current_size, current_tracking, current_leading

def _match_layer(layer_text: str, mapping: TextMapping) -> bool:
    """判断图层文字是否匹配映射规则"""
    normalized_layer = _normalize_newlines(layer_text.strip())
    normalized_mapping = _normalize_newlines(mapping.original_text)
    if mapping.match_mode == "exact":
        return normalized_layer == normalized_mapping
    elif mapping.match_mode == "contains":
        return normalized_mapping in normalized_layer
    return False


def _apply_new_text(text_item, layer_text: str, mapping: TextMapping) -> str:
    """
    应用新文字内容，返回实际设置的文字
    new_text 为 None 时保持原文字不变（只换字体）
    """
    if mapping.new_text is None:
        return layer_text  # 不修改内容

    if mapping.match_mode == "exact":
        new_content = _normalize_newlines(mapping.new_text)
    else:
        # 包含匹配：只替换匹配到的子串
        normalized_layer = _normalize_newlines(layer_text)
        normalized_original = _normalize_newlines(mapping.original_text)
        new_content = normalized_layer.replace(normalized_original, _normalize_newlines(mapping.new_text), 1)

    text_item.Contents = new_content
    _wait_ps()
    return new_content


def _build_new_content(layer_text: str, mapping: TextMapping) -> str:
    """只计算新文字，不改真实图层。"""
    if mapping.new_text is None:
        return layer_text
    if mapping.match_mode == "exact":
        return _normalize_newlines(mapping.new_text)
    normalized_layer = _normalize_newlines(layer_text)
    normalized_original = _normalize_newlines(mapping.original_text)
    return normalized_layer.replace(normalized_original, _normalize_newlines(mapping.new_text), 1)


def _resolve_font(ps: PhotoshopConnector, text_item, font_spec: str) -> str:
    """
    解析字体规格：
    - 如果包含 '-'，认为是完整 PostScript 名称（如 NotoSans-Bold），直接使用
    - 如果不含 '-'，认为是字体家族名（如 NotoSans），用数值映射找最接近字重
    返回最终使用的 PostScript 字体名称
    """
    if '-' in font_spec:
        return font_spec  # 完整名称，直接用

    # 字体家族名，用数值映射自动判断字重
    try:
        original_font = text_item.Font
        from font_weight_mapper import find_closest_weight
        available = ps.get_available_weights(font_spec)
        # If not found with spaces, try compact form (e.g. "Noto Sans" -> "NotoSans")
        compact_spec = font_spec
        if not available and " " in font_spec:
            compact_spec = font_spec.replace(" ", "")
            available = ps.get_available_weights(compact_spec)
        if not available:
            raise ValueError(f"目标字体家族未安装: {font_spec}")
        sep = ps.get_font_separator(compact_spec)
        resolved = find_closest_weight(original_font, compact_spec, available, separator=sep)
        print(f"        [字重映射] {original_font} -> {resolved}")
        return resolved
    except Exception as e:
        # Build a valid PostScript name: remove spaces so "Noto Sans" -> "NotoSans-Regular"
        compact = font_spec.replace(" ", "")
        fallback = f"{compact}-Regular"
        print(f"        [字重映射失败] {e}，使用 {fallback}")
        return fallback


def _get_bounds_wh(ps: PhotoshopConnector, layer) -> tuple[float, float]:
    """获取图层的宽度和高度"""
    b = ps.get_layer_bounds(layer)
    return b[2] - b[0], b[3] - b[1]


def _get_active_resolution(ps: PhotoshopConnector) -> float:
    try:
        return float(ps.app.ActiveDocument.Resolution)
    except Exception:
        return 72.0


def _get_doc_resolution(doc) -> float:
    try:
        return float(doc.Resolution)
    except Exception:
        return 72.0


def _create_temp_fit_doc(ps: PhotoshopConnector, resolution: float):
    rounded_resolution = round(float(resolution or 72.0), 4)
    doc = ps.app.Documents.Add(4096, 4096, rounded_resolution, f"mediatools_text_fit_{rounded_resolution:g}dpi", 2, 1, 1)
    _wait_ps(0.1)
    return doc


def _close_temp_fit_doc(ps: PhotoshopConnector, doc) -> None:
    if doc is None:
        return
    try:
        doc.Close(psDoNotSaveChanges)
    except Exception:
        pass
    _wait_ps(0.1)


def _create_temp_text_layer(doc, text: str, font: str | None, size: float, tracking: float, leading: float):
    layer = doc.ArtLayers.Add()
    layer.Kind = 2
    ti = layer.TextItem
    ti.Contents = text
    if font:
        ti.Font = font
    ti.Size = size
    ti.Tracking = tracking
    _set_leading(ti, leading)
    try:
        ti.Position = [1000, 1000]
    except Exception:
        pass
    _wait_ps(0.1)
    return layer


def _safe_float(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _is_multiline_text(text: str) -> bool:
    return "\r" in text or "\n" in text


def _set_leading(text_item, leading: float) -> None:
    try:
        text_item.Leading = leading
    except Exception:
        pass


def _restore_spacing(text_item, original_tracking: float, original_leading: float) -> None:
    text_item.Tracking = original_tracking
    if original_leading is not None:
        _set_leading(text_item, original_leading)


def _bounds_score(width: float, height: float, original_width: float, original_height: float, params: AdjustParams, multiline: bool) -> float:
    height_tolerance = params.height_tolerance if not multiline else params.tolerance
    width_error = max(0.0, (width - original_width) / max(original_width, 1.0) - params.tolerance)
    height_error = max(0.0, (height - original_height) / max(original_height, 1.0) - height_tolerance)
    if multiline:
        return width_error * 0.5 + height_error * 0.5
    return width_error * 0.85 + height_error * 0.15


def _is_acceptable(width: float, height: float, original_width: float, original_height: float, params: AdjustParams, multiline: bool) -> bool:
    height_tolerance = params.height_tolerance if not multiline else params.tolerance
    return (
        width <= original_width * (1.0 + params.tolerance)
        and height <= original_height * (1.0 + height_tolerance)
    )


def _is_too_large(width: float, height: float, original_width: float, original_height: float, params: AdjustParams, multiline: bool) -> bool:
    if multiline:
        return (width * height) > (original_width * original_height)
    return width > original_width * (1.0 + params.tolerance)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _capture_fit_state(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, params: AdjustParams, multiline: bool) -> dict:
    width, height = _get_bounds_wh(ps, layer)
    try:
        leading = float(text_item.Leading)
    except Exception:
        leading = -1.0
    return {
        "font_size": _safe_float(text_item.Size, 12.0),
        "tracking": _safe_float(text_item.Tracking, 0.0),
        "leading": leading,
        "width": width,
        "height": height,
        "score": _bounds_score(width, height, original_width, original_height, params, multiline),
    }


def _restore_fit_state(text_item, state: dict) -> None:
    text_item.Size = state["font_size"]
    text_item.Tracking = state["tracking"]
    _set_leading(text_item, state["leading"])
    _wait_ps()


def _binary_fit_font_size_only(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_size: float, original_tracking: float, original_leading: float, params: AdjustParams, multiline: bool) -> dict:
    low = original_size * params.font_size_min_ratio
    high = original_size
    best = None
    for _ in range(max(1, int(params.font_size_binary_iterations))):
        current = (low + high) / 2.0
        text_item.Size = current
        _restore_spacing(text_item, original_tracking, original_leading)
        _wait_ps()
        state = _capture_fit_state(ps, layer, text_item, original_width, original_height, params, multiline)
        if best is None or state["score"] < best["score"]:
            best = state
        if _is_too_large(state["width"], state["height"], original_width, original_height, params, multiline):
            high = current
        else:
            low = current
    if best is not None:
        _restore_fit_state(text_item, best)
    return best or _capture_fit_state(ps, layer, text_item, original_width, original_height, params, multiline)


def _micro_adjust_spacing_once(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_tracking: float, original_leading: float, params: AdjustParams, multiline: bool) -> dict:
    width, height = _get_bounds_wh(ps, layer)
    width_error = (original_width - width) / max(original_width, 1.0)
    tracking_offset = _clamp(width_error * 200.0, -abs(params.tracking_delta), abs(params.tracking_delta))
    text_item.Tracking = original_tracking + tracking_offset

    if multiline and original_leading > 0:
        height_error = (original_height - height) / max(original_height, 1.0)
        leading_ratio = _clamp(1.0 + height_error, params.leading_min_ratio, params.leading_max_ratio)
        _set_leading(text_item, original_leading * leading_ratio)

    _wait_ps()
    return _capture_fit_state(ps, layer, text_item, original_width, original_height, params, multiline)


def _fit_text_in_temp_document(
    ps: PhotoshopConnector,
    *,
    resolution: float,
    original_text: str,
    new_text: str,
    original_font: str | None,
    target_font: str | None,
    original_font_size: float,
    original_tracking: float,
    original_leading: float,
    params: AdjustParams,
    after_doc,
) -> dict:
    parent_doc = ps.app.ActiveDocument
    temp_doc = None
    try:
        temp_doc = _create_temp_fit_doc(ps, resolution)
        temp_doc.Activate()

        baseline_layer = _create_temp_text_layer(
            temp_doc,
            original_text,
            original_font,
            original_font_size,
            original_tracking,
            original_leading,
        )
        original_width, original_height = _get_bounds_wh(ps, baseline_layer)
        baseline_layer.Delete()

        fit_layer = _create_temp_text_layer(
            temp_doc,
            new_text,
            target_font or original_font,
            original_font_size,
            original_tracking,
            original_leading,
        )
        text_item = fit_layer.TextItem
        multiline = _is_multiline_text(new_text)

        best_state = _capture_fit_state(ps, fit_layer, text_item, original_width, original_height, params, multiline)

        # 如果新文案在原字号下已经可接受，不做缩放
        if _is_acceptable(best_state["width"], best_state["height"], original_width, original_height, params, multiline):
            result = {
                **best_state,
                "original_width": original_width,
                "original_height": original_height,
                "width": best_state["width"],
                "height": best_state["height"],
                "multiline": multiline,
                "fit_document_resolution": resolution,
                "fit_status": "ok",
            }
            try:
                fit_layer.Delete()
            except Exception:
                pass
            return result

        font_state = _binary_fit_font_size_only(
            ps,
            fit_layer,
            text_item,
            original_width,
            original_height,
            original_font_size,
            original_tracking,
            original_leading,
            params,
            multiline,
        )
        if font_state["score"] < best_state["score"]:
            best_state = font_state

        base_size = _safe_float(text_item.Size, original_font_size)
        low = base_size * (1.0 - params.font_size_refine_ratio)
        high = base_size * (1.0 + params.font_size_refine_ratio)
        for _ in range(max(1, int(params.font_size_refine_iterations))):
            spacing_state = _micro_adjust_spacing_once(
                ps,
                fit_layer,
                text_item,
                original_width,
                original_height,
                original_tracking,
                original_leading,
                params,
                multiline,
            )
            if spacing_state["score"] < best_state["score"]:
                best_state = spacing_state
            if _is_acceptable(spacing_state["width"], spacing_state["height"], original_width, original_height, params, multiline):
                best_state = spacing_state
                break

            _restore_spacing(text_item, original_tracking, original_leading)
            current = (low + high) / 2.0
            text_item.Size = current
            _wait_ps()
            size_state = _capture_fit_state(ps, fit_layer, text_item, original_width, original_height, params, multiline)
            if size_state["score"] < best_state["score"]:
                best_state = size_state
            if _is_acceptable(size_state["width"], size_state["height"], original_width, original_height, params, multiline):
                best_state = size_state
                break
            if _is_too_large(size_state["width"], size_state["height"], original_width, original_height, params, multiline):
                high = current
            else:
                low = current

        _restore_fit_state(text_item, best_state)
        final_width, final_height = _get_bounds_wh(ps, fit_layer)
        result = {
            **best_state,
            "original_width": original_width,
            "original_height": original_height,
            "width": final_width,
            "height": final_height,
            "multiline": multiline,
            "fit_document_resolution": resolution,
            "fit_status": "ok",
        }
        try:
            fit_layer.Delete()
        except Exception:
            pass
        return result
    finally:
        if temp_doc is not None:
            _close_temp_fit_doc(ps, temp_doc)
        try:
            after_doc.Activate()
        except Exception:
            pass
        try:
            ps.app.Preferences.TypeUnits = psTypePixels
        except Exception:
            pass


def modify_text_layer(
    ps: PhotoshopConnector,
    layer,
    mapping: TextMapping,
    params: AdjustParams,
    font_metrics: dict = None,
    skip_temp_doc: bool = False,
) -> ModifyResult:
    """
    修改单个文字图层，执行自适应调整

    算法流程：
    1. 记录原始状态（字号、tracking、leading、Bounds）
    2. 替换文字内容和字体，保持原字号
    3. 如果有 font_metrics 缓存：
       直接用 new_size = original_size / scale 计算目标字号并应用
       （对 Transform 缩放图层也有效，完全绕开 Bounds 约束）
    4. 如果没有 font_metrics 缓存（fallback）：
       先 8 次只二分字号，再 4 次 spacing/字号微调
    5. 如果 skip_temp_doc=True（智能对象内部）：
       跳过临时文档拟合，直接用原始样式写回
    """
    text_item = layer.TextItem
    layer_name = layer.Name

    # --- 记录原始状态 ---
    # Ensure TypeUnits is px before any Size read/write; PS may reset it when switching documents
    try:
        ps.app.Preferences.TypeUnits = 5  # psTypePixels
    except Exception:
        pass
    original_text = _get_text_content(layer)
    original_width, original_height = _get_bounds_wh(ps, layer)

    try:
        original_font_size = float(text_item.Size)
    except Exception:
        original_font_size = 12.0

    try:
        original_font = text_item.Font
    except Exception:
        original_font = None

    try:
        original_tracking = text_item.Tracking
    except Exception:
        original_tracking = 0.0

    try:
        original_leading = float(text_item.Leading)
    except Exception:
        original_leading = -1.0  # PS 中 Auto Leading 通常是负值

    # 确定初始 tracking（用户指定 > 原始值）
    initial_tracking = mapping.tracking if mapping.tracking is not None else original_tracking

    # 确定目标字号（用户指定 > 原始值）
    user_specified_size = mapping.font_size is not None
    current_font_size = mapping.font_size if user_specified_size else original_font_size

    # 构建错误返回的辅助函数
    def error_result(msg: str) -> ModifyResult:
        return ModifyResult(
            layer_name=layer_name,
            original_text=original_text,
            new_text=original_text,
            original_font_size=original_font_size,
            final_font_size=current_font_size,
            original_tracking=original_tracking,
            final_tracking=initial_tracking,
            original_width=original_width,
            final_width=original_width,
            original_height=original_height,
            final_height=original_height,
            success=False,
            message=msg,
        )

    new_content = _build_new_content(original_text, mapping)
    resolved_font = _resolve_font(ps, text_item, mapping.font) if mapping.font else original_font
    parent_doc = ps.app.ActiveDocument
    real_layer_id = ps.get_layer_id(layer)

    best_state = {
        "font_size": current_font_size,
        "tracking": initial_tracking,
        "leading": original_leading,
        "original_width": original_width,
        "original_height": original_height,
        "width": original_width,
        "height": original_height,
        "score": 0.0,
        "multiline": _is_multiline_text(new_content),
        "fit_document_resolution": _get_doc_resolution(parent_doc),
        "fit_status": "skipped" if user_specified_size or skip_temp_doc else "fallback",
    }
    fit_warning = ""

    if not user_specified_size and not skip_temp_doc:
        try:
            best_state = _fit_text_in_temp_document(
                ps,
                resolution=_get_doc_resolution(parent_doc),
                original_text=original_text,
                new_text=new_content,
                original_font=original_font,
                target_font=resolved_font,
                original_font_size=original_font_size,
                original_tracking=initial_tracking,
                original_leading=original_leading,
                params=params,
                after_doc=parent_doc,
            )
        except Exception as e:
            fit_warning = f"临时工程拟合失败，已用原始样式写回: {e}"
            best_state["fit_status"] = "warning"

    try:
        try:
            parent_doc.Activate()
        except Exception:
            pass
        # best_state belongs only to this modify_text_layer call; the temp doc is reused, not the fit result.
        write_layer = ps.find_layer_by_id(parent_doc, real_layer_id) if real_layer_id else layer
        if write_layer is None:
            raise RuntimeError(f"真实图层重新定位失败: layer_id={real_layer_id}")
        write_text_item = write_layer.TextItem
        write_text_item.Contents = new_content
        if resolved_font:
            write_text_item.Font = resolved_font
        write_text_item.Size = best_state["font_size"]
        write_text_item.Tracking = best_state["tracking"]
        _set_leading(write_text_item, best_state["leading"])
        _wait_ps()
        actual_text = _normalize_newlines(str(write_text_item.Contents or ""))
        expected_text = _normalize_newlines(new_content)
        if actual_text != expected_text:
            raise RuntimeError(f"真实图层写回验证失败: expected={expected_text!r}, actual={actual_text!r}")
    except Exception as e:
        try:
            parent_doc.Activate()
        except Exception:
            pass
        if original_font is not None:
            try:
                _restore_text_state(text_item, original_text, original_font, original_font_size, original_tracking, original_leading)
            except Exception:
                pass
        return error_result(f"真实图层写回失败: {e}")

    final_width = best_state["width"]
    final_height = best_state["height"]
    original_width = best_state.get("original_width", original_width)
    original_height = best_state.get("original_height", original_height)
    current_font_size = _safe_float(best_state.get("font_size"), original_font_size)
    current_tracking = _safe_float(best_state.get("tracking"), initial_tracking)
    current_leading = _safe_float(best_state.get("leading"), original_leading)
    multiline = bool(best_state.get("multiline", _is_multiline_text(new_content)))

    msg = fit_warning
    if not _is_acceptable(final_width, final_height, original_width, original_height, params, multiline):
        w_error = abs(final_width - original_width) / max(original_width, 1.0) * 100
        h_error = abs(final_height - original_height) / max(original_height, 1.0) * 100
        fit_msg = (
            f"警告: 临时工程已保留最接近结果 (score={best_state['score']:.4f}, 字号={current_font_size:.1f}px, "
            f"tracking={current_tracking:.0f})，宽度误差 {w_error:.1f}%, 高度误差 {h_error:.1f}%"
        )
        msg = f"{msg}; {fit_msg}" if msg else fit_msg

    return ModifyResult(
        layer_name=layer_name,
        original_text=original_text,
        new_text=new_content,
        original_font_size=original_font_size,
        final_font_size=current_font_size,
        original_tracking=original_tracking,
        final_tracking=current_tracking,
        original_width=original_width,
        final_width=final_width,
        original_height=original_height,
        final_height=final_height,
        success=True,
        message=msg,
        original_leading=original_leading,
        final_leading=current_leading,
        score=_safe_float(best_state.get("score"), 0.0),
        fit_document_resolution=_safe_float(best_state.get("fit_document_resolution"), 0.0),
        fit_status=str(best_state.get("fit_status") or "ok"),
    )


def _filter_mappings(mappings: list[TextMapping], artboard_name: str = None) -> list[TextMapping]:
    """
    筛选适用于当前上下文的映射规则
    - artboard_name=None: 返回全局规则（artboard 字段为空的）
    - artboard_name="xxx": 返回全局规则 + 该画板专属规则（专属规则优先）
    """
    global_rules = [m for m in mappings if m.artboard is None]

    if artboard_name is None:
        return global_rules

    artboard_rules = [m for m in mappings if m.artboard == artboard_name]

    # 专属规则优先：同一 original_text 有专属规则时，全局规则不生效
    artboard_originals = {m.original_text for m in artboard_rules}
    filtered_global = [m for m in global_rules if m.original_text not in artboard_originals]

    return artboard_rules + filtered_global


def _process_layers(
    ps: PhotoshopConnector,
    text_layers: list,
    applicable_mappings: list[TextMapping],
    params: AdjustParams,
    indent: str = "  ",
) -> list[ModifyResult]:
    """处理一组文字图层，返回修改结果列表"""
    results = []
    for layer in text_layers:
        layer_text = _get_text_content(layer)
        if not layer_text:
            continue

        for mapping in applicable_mappings:
            if _match_layer(layer_text, mapping):
                display_new = mapping.new_text if mapping.new_text else "(保持原文字)"
                print(f"{indent}[匹配] 图层 '{layer.Name}': '{layer_text[:30]}' -> '{display_new}'")
                result = modify_text_layer(ps, layer, mapping, params)
                results.append(result)

                if result.message:
                    print(f"{indent}       {result.message}")
                if result.success:
                    print(
                        f"{indent}       字号: {result.original_font_size:.1f} -> {result.final_font_size:.1f}px, "
                        f"tracking: {result.original_tracking:.0f} -> {result.final_tracking:.0f}"
                    )
                break  # 匹配到一条规则后不再继续

    return results


def process_document(
    ps: PhotoshopConnector,
    doc,
    mappings: list[TextMapping],
    params: AdjustParams,
) -> list[ModifyResult]:
    """
    处理单个文档中的所有文字图层
    自动检测是否有画板：
    - 有画板：按画板分组处理，支持画板级别的映射规则
    - 无画板：走原有逻辑
    """
    results = []
    artboards = ps.collect_artboards(doc)

    if artboards:
        # ===== 多画板模式 =====
        print(f"  [多画板模式] 检测到 {len(artboards)} 个画板")
        artboard_ids = set()
        for ab in artboards:
            try:
                artboard_ids.add(ab.id)
            except Exception:
                pass

        for ab in artboards:
            ab_name = ab.Name
            print(f"\n  --- 画板: {ab_name} ---")

            text_layers = ps.collect_text_layers_in_artboard(ab)
            if not text_layers:
                print(f"    [!] 未找到文字图层")
                continue

            print(f"    找到 {len(text_layers)} 个文字图层")
            applicable = _filter_mappings(mappings, ab_name)
            results.extend(_process_layers(ps, text_layers, applicable, params, indent="    "))

        # 处理画板外的文字图层
        outside_layers = ps.collect_text_layers_outside_artboards(doc, artboard_ids)
        if outside_layers:
            print(f"\n  --- 画板外的文字图层 ---")
            print(f"    找到 {len(outside_layers)} 个文字图层")
            global_mappings = _filter_mappings(mappings, None)
            results.extend(_process_layers(ps, outside_layers, global_mappings, params, indent="    "))

    else:
        # ===== 无画板模式 =====
        text_layers = ps.collect_text_layers(doc)
        if not text_layers:
            print("  [!] 未找到任何文字图层")
            return results

        print(f"  找到 {len(text_layers)} 个文字图层")
        results.extend(_process_layers(ps, text_layers, mappings, params, indent="  "))

    return results


# ============================================================
# 查表直接应用模式（跳过自适应循环，速度快 5-10 倍）
# ============================================================

def apply_from_cache(
    ps: PhotoshopConnector,
    layer,
    new_text: Optional[str],
    new_font: str,
    cache_entry=None,
) -> ModifyResult:
    """
    只替换字体，保持原文字号和 tracking 不变
    不等待 PS 刷新，适合批量快速应用
    """
    text_item = layer.TextItem
    layer_name = layer.Name

    original_text, original_font, original_font_size, original_tracking, original_leading = _capture_text_state(text_item)
    original_text = original_text.strip()
    original_font_size = round(float(original_font_size), 2)
    try:
        original_tracking = round(float(original_tracking), 2)
    except Exception:
        original_tracking = 0.0
    original_width, original_height = _get_bounds_wh(ps, layer)

    try:
        # 替换文字内容
        normalized_new_text = _normalize_newlines(new_text) if new_text else None
        if new_text:
            text_item.Contents = normalized_new_text

        # 换字体（px 模式下不存在单位重新解释问题）
        text_item.Font = new_font
        text_item.Size = original_font_size
        text_item.Tracking = original_tracking
    except Exception as e:
        if original_font is not None:
            try:
                _restore_text_state(text_item, original_text, original_font, original_font_size, original_tracking, original_leading)
            except Exception:
                pass
        return ModifyResult(
            layer_name=layer_name,
            original_text=original_text,
            new_text=original_text,
            original_font_size=original_font_size,
            final_font_size=original_font_size,
            original_tracking=original_tracking,
            final_tracking=original_tracking,
            original_width=original_width,
            final_width=original_width,
            original_height=original_height,
            final_height=original_height,
            success=False,
            message=f"[换字体失败] {e}",
        )

    # 批量场景中只在最后获取一次宽高，避免不必要的 wait
    final_width, final_height = _get_bounds_wh(ps, layer)

    return ModifyResult(
        layer_name=layer_name,
        original_text=original_text,
        new_text=normalized_new_text if normalized_new_text else original_text,
        original_font_size=original_font_size,
        final_font_size=original_font_size,
        original_tracking=original_tracking,
        final_tracking=original_tracking,
        original_width=original_width,
        final_width=final_width,
        original_height=original_height,
        final_height=final_height,
        success=True,
        message="[换字体] 保持原字号和 tracking 不变",
    )
