"""
核心逻辑：文字替换 + 自适应调整
策略：字号是粗调，字间距(tracking)是微调
自适应算法：宽度优先（宽度和高度分别判断，取超出更多的维度）
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from config_reader import TextMapping
from ps_connector import PhotoshopConnector


@dataclass
class AdjustParams:
    """自适应调整参数"""
    tracking_min: float = -50         # tracking 下限（保守值，保证可读性）
    tracking_step: float = 5          # tracking 每次调整步长
    font_size_min_ratio: float = 0.75  # 最小字号 = 原字号 × 此比例
    tolerance: float = 0.05           # 宽高容差，允许超出 5%
    font_size_max_ratio: float = 1.25
    font_size_binary_iterations: int = 8
    font_size_refine_ratio: float = 0.05
    font_size_refine_iterations: int = 5
    tracking_delta: float = 120
    tracking_binary_iterations: int = 6
    leading_min_ratio: float = 0.85
    leading_max_ratio: float = 1.15
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


def _safe_float(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _is_multiline_text(text: str) -> bool:
    return "\r" in text or "\n" in text


def _effective_leading(original_leading: float, font_size: float) -> float:
    if original_leading and original_leading > 0:
        return original_leading
    return font_size * 1.2


def _set_leading(text_item, leading: float) -> None:
    try:
        text_item.Leading = leading
    except Exception:
        pass


def _restore_spacing(text_item, original_tracking: float, original_leading: float) -> None:
    text_item.Tracking = original_tracking
    if original_leading is not None:
        _set_leading(text_item, original_leading)


def _bounds_score(width: float, height: float, original_width: float, original_height: float, multiline: bool) -> float:
    width_error = abs(width - original_width) / max(original_width, 1.0)
    height_error = abs(height - original_height) / max(original_height, 1.0)
    if multiline:
        return width_error * 0.5 + height_error * 0.5
    return width_error * 0.85 + height_error * 0.15


def _is_acceptable(width: float, height: float, original_width: float, original_height: float, params: AdjustParams, multiline: bool) -> bool:
    width_error = abs(width - original_width) / max(original_width, 1.0)
    height_error = abs(height - original_height) / max(original_height, 1.0)
    height_tolerance = params.tolerance if multiline else params.height_tolerance
    return width_error <= params.tolerance and height_error <= height_tolerance


def _is_too_large(width: float, height: float, original_width: float, original_height: float, multiline: bool) -> bool:
    if multiline:
        return (width * height) > (original_width * original_height)
    return width > original_width


def _capture_fit_state(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, multiline: bool) -> dict:
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
        "score": _bounds_score(width, height, original_width, original_height, multiline),
    }


def _restore_fit_state(text_item, state: dict) -> None:
    text_item.Size = state["font_size"]
    text_item.Tracking = state["tracking"]
    _set_leading(text_item, state["leading"])
    _wait_ps()


def _binary_fit_font_size_only(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_size: float, params: AdjustParams, multiline: bool) -> dict:
    low = original_size * params.font_size_min_ratio
    high = original_size * params.font_size_max_ratio
    best = None
    for _ in range(max(1, int(params.font_size_binary_iterations))):
        current = (low + high) / 2.0
        text_item.Size = current
        _wait_ps()
        state = _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)
        if best is None or state["score"] < best["score"]:
            best = state
        if _is_too_large(state["width"], state["height"], original_width, original_height, multiline):
            high = current
        else:
            low = current
    if best is not None:
        _restore_fit_state(text_item, best)
    return best or _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)


def _binary_fit_tracking(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_tracking: float, params: AdjustParams, multiline: bool) -> dict:
    low = original_tracking - abs(params.tracking_delta)
    high = original_tracking + abs(params.tracking_delta)
    best = None
    for _ in range(max(1, int(params.tracking_binary_iterations))):
        current = (low + high) / 2.0
        text_item.Tracking = current
        _wait_ps()
        state = _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)
        if best is None or state["score"] < best["score"]:
            best = state
        if state["width"] > original_width:
            high = current
        else:
            low = current
    if best is not None:
        _restore_fit_state(text_item, best)
    return best or _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)


def _binary_fit_leading(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_leading: float, current_size: float, params: AdjustParams, multiline: bool) -> dict:
    base_leading = _effective_leading(original_leading, current_size)
    low = base_leading * params.leading_min_ratio
    high = base_leading * params.leading_max_ratio
    best = None
    for _ in range(max(1, int(params.leading_binary_iterations))):
        current = (low + high) / 2.0
        _set_leading(text_item, current)
        _wait_ps()
        state = _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)
        if best is None or state["score"] < best["score"]:
            best = state
        if state["height"] > original_height:
            high = current
        else:
            low = current
    if best is not None:
        _restore_fit_state(text_item, best)
    return best or _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)


def _fit_spacing_at_current_size(ps: PhotoshopConnector, layer, text_item, original_width: float, original_height: float, original_tracking: float, original_leading: float, params: AdjustParams, multiline: bool) -> dict:
    best = _binary_fit_tracking(ps, layer, text_item, original_width, original_height, original_tracking, params, multiline)
    if multiline:
        leading_state = _binary_fit_leading(
            ps,
            layer,
            text_item,
            original_width,
            original_height,
            original_leading,
            _safe_float(text_item.Size, 12.0),
            params,
            multiline,
        )
        if leading_state["score"] < best["score"]:
            best = leading_state
        tracking_state = _binary_fit_tracking(ps, layer, text_item, original_width, original_height, original_tracking, params, multiline)
        if tracking_state["score"] < best["score"]:
            best = tracking_state
    return best


def modify_text_layer(
    ps: PhotoshopConnector,
    layer,
    mapping: TextMapping,
    params: AdjustParams,
    font_metrics: dict = None,
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
       用比例跳跃法测量 Bounds 做自适应调整
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

    # --- Step 1: 替换文字内容 ---
    new_content = _apply_new_text(text_item, original_text, mapping)

    # --- Step 2: 设置字体（如果指定） ---
    if mapping.font:
        resolved_font = _resolve_font(ps, text_item, mapping.font)
        try:
            text_item.Font = resolved_font
            _wait_ps()
            # PS may reset TypeUnits and Leading after a font change; restore both
            try:
                ps.app.Preferences.TypeUnits = 5  # psTypePixels
            except Exception:
                pass
            try:
                text_item.Leading = original_leading
            except Exception:
                pass
        except Exception as e:
            if original_font is not None:
                try:
                    _restore_text_state(text_item, original_text, original_font, original_font_size, original_tracking, original_leading)
                except Exception:
                    pass
            return error_result(f"设置字体失败 ({resolved_font}): {e}")

    # --- Step 3: 设置初始字号和 tracking ---
    try:
        text_item.Size = current_font_size
        text_item.Tracking = initial_tracking
        _wait_ps()
    except Exception as e:
        if original_font is not None:
            try:
                _restore_text_state(text_item, original_text, original_font, original_font_size, original_tracking, original_leading)
            except Exception:
                pass
        return error_result(f"设置字号或 tracking 失败: {e}")

    # 如果用户强制指定了字号，不做自适应调整
    if user_specified_size:
        final_width, final_height = _get_bounds_wh(ps, layer)
        return ModifyResult(
            layer_name=layer_name,
            original_text=original_text,
            new_text=new_content,
            original_font_size=original_font_size,
            final_font_size=current_font_size,
            original_tracking=original_tracking,
            final_tracking=initial_tracking,
            original_width=original_width,
            final_width=final_width,
            original_height=original_height,
            final_height=final_height,
            success=True,
            message="已使用用户指定字号，跳过自适应调整",
        )

    # --- Step 4: 字号调整 ---
    # 优先用 font_metrics 缓存（空白工程验证法），对 Transform 缩放图层也有效
    if font_metrics and mapping.font and original_font:
        from font_metrics_cache import get_size_scale
        # 解析目标字体的完整 PostScript 名（已在 Step 2 中 resolve 过，这里重新取）
        resolved_target = text_item.Font  # Step 2 已经设置好了
        # 用原始文字内容查找 scale（精确匹配每个图层的实际文字）
        scale = get_size_scale(font_metrics, original_font, resolved_target, original_text)
        if scale != 1.0:
            adjusted_size = round(original_font_size / scale, 4)
            text_item.Size = adjusted_size
            _wait_ps()
            current_font_size = adjusted_size
            final_width, final_height = _get_bounds_wh(ps, layer)
            return ModifyResult(
                layer_name=layer_name,
                original_text=original_text,
                new_text=new_content,
                original_font_size=original_font_size,
                final_font_size=current_font_size,
                original_tracking=original_tracking,
                final_tracking=initial_tracking,
                original_width=original_width,
                final_width=final_width,
                original_height=original_height,
                final_height=final_height,
                success=True,
                message=f"[metrics] scale={scale:.4f}, {original_font_size:.2f}px -> {adjusted_size:.2f}px",
            )

    # --- Step 4 fallback: 两阶段自适应调整 ---
    # 先只二分字号摸到接近值，再在该字号下微调 tracking/leading。
    multiline = _is_multiline_text(new_content)
    _restore_spacing(text_item, initial_tracking, original_leading)
    _wait_ps()

    best_state = _capture_fit_state(ps, layer, text_item, original_width, original_height, multiline)

    font_state = _binary_fit_font_size_only(
        ps,
        layer,
        text_item,
        original_width,
        original_height,
        original_font_size,
        params,
        multiline,
    )
    if font_state["score"] < best_state["score"]:
        best_state = font_state

    spacing_state = _fit_spacing_at_current_size(
        ps,
        layer,
        text_item,
        original_width,
        original_height,
        initial_tracking,
        original_leading,
        params,
        multiline,
    )
    if spacing_state["score"] < best_state["score"]:
        best_state = spacing_state

    if not _is_acceptable(spacing_state["width"], spacing_state["height"], original_width, original_height, params, multiline):
        base_size = _safe_float(text_item.Size, original_font_size)
        low = base_size * (1.0 - params.font_size_refine_ratio)
        high = base_size * (1.0 + params.font_size_refine_ratio)
        for _ in range(max(1, int(params.font_size_refine_iterations))):
            current = (low + high) / 2.0
            text_item.Size = current
            _restore_spacing(text_item, initial_tracking, original_leading)
            _wait_ps()

            state = _fit_spacing_at_current_size(
                ps,
                layer,
                text_item,
                original_width,
                original_height,
                initial_tracking,
                original_leading,
                params,
                multiline,
            )
            if state["score"] < best_state["score"]:
                best_state = state
            if _is_acceptable(state["width"], state["height"], original_width, original_height, params, multiline):
                best_state = state
                break
            if _is_too_large(state["width"], state["height"], original_width, original_height, multiline):
                high = current
            else:
                low = current

    _restore_fit_state(text_item, best_state)

    final_width, final_height = _get_bounds_wh(ps, layer)
    current_font_size = _safe_float(text_item.Size, original_font_size)
    current_tracking = _safe_float(text_item.Tracking, initial_tracking)

    msg = ""
    if not _is_acceptable(final_width, final_height, original_width, original_height, params, multiline):
        w_error = abs(final_width - original_width) / max(original_width, 1.0) * 100
        h_error = abs(final_height - original_height) / max(original_height, 1.0) * 100
        msg = (
            f"警告: 已保留最接近结果 (score={best_state['score']:.4f}, 字号={current_font_size:.1f}px, "
            f"tracking={current_tracking:.0f})，宽度误差 {w_error:.1f}%, 高度误差 {h_error:.1f}%"
        )

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
