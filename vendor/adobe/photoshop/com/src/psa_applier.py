"""
Core layer processing with calibration, verify/refine, and SO boundary protection.

Ported from PSA reference (C:\\PSA\\psa_applier.py).
Provides per-layer processing functions consumed by text_modifier and ticket_workflow.
"""
from __future__ import annotations

from text_models import TextLayerRecord, AdaptedParams
from text_utils import (
    safe_get,
    enter_smart_object,
    find_layer_by_id,
    find_layer_by_path,
    expand_so_canvas,
    pt_to_px,
    layer_bounds_px,
    com_retry,
    LayerNotFoundError,
    SOEnterError,
)
from font_resolver import build_font_index, resolve_font
from adaptive_lab import LabDocument
from smart_object_handler import (
    _find_so_by_psb,
    outermost_key,
    find_outermost_so,
    process_so_level,
)


def process_layer(app, doc, record: TextLayerRecord, lab: LabDocument, logger,
                  in_so: bool = False) -> AdaptedParams | None:
    """Handle one layer: find it, calibrate scale via lab, run adaptive, apply, verify+refine.

    This is the core processing function ported from PSA's _process_layer().
    It implements Method A (calibration) and Method B (verify+refine).

    Returns AdaptedParams on success, None on failure.
    """
    try:
        if record.multi_style:
            logger.log_warning(
                f"SKIP multi-style layer [{record.layer_path}]: "
                f"layer has multiple text formatting ranges, cannot safely modify"
            )
            return None

        if in_so:
            parts = record.layer_path.split("/")
            layer = find_layer_by_path(doc, parts)
            if layer is None:
                layer = find_layer_by_id(doc, record.layer_id)
        else:
            layer = find_layer_by_id(doc, record.layer_id)

        if layer is None:
            raise LayerNotFoundError(
                f"Layer id={record.layer_id} path='{record.layer_path}' not found"
            )

        logger.log_layer_before(record)
        new_font_ps = record.new_font_ps or record.font
        new_text = record.new_text if record.new_text is not None else record.text
        logger.log_apply_start(record.layer_path, record.bounds_h_px, new_font_ps)

        # ===== Method A: calibrate scale using original text in lab =====
        scale = 1.0
        try:
            lab_orig_h = lab.measure_text(
                font_ps=record.font,
                contents=record.text,
                size_pt=record.size_pt,
                tracking=record.tracking,
                auto_leading=record.auto_leading,
                leading_pt=record.leading_pt,
            )
            if lab_orig_h > 0.5:
                scale = record.bounds_h_px / lab_orig_h
            logger.log_info(
                f"CALIBRATE [{record.layer_path}]: real_h={record.bounds_h_px:.2f}px "
                f"lab_h={lab_orig_h:.2f}px scale={scale:.4f}"
            )
        except Exception as e:
            logger.log_error(f"calibrate scale for '{record.layer_path}'", e)
            scale = 1.0

        target_h_lab = record.bounds_h_px / scale if scale > 0 else record.bounds_h_px

        # Restore doc+layer as active (lab switched it) — retry on COM busy
        com_retry(setattr, app, "ActiveDocument", doc)
        com_retry(setattr, doc, "ActiveLayer", layer)

        # Run adaptive algorithm with corrected target
        params = lab.find_adapted_params(
            record, new_font_ps, new_text, logger,
            target_h_override=target_h_lab,
        )

        # Apply to real layer
        com_retry(setattr, app, "ActiveDocument", doc)
        com_retry(setattr, doc, "ActiveLayer", layer)
        apply_params_to_layer(app, doc, layer, params, record, logger)

        # ===== Boundary protection for Smart Objects =====
        if in_so:
            try:
                size_ratio = params.size_pt / max(record.size_pt, 0.1)
                expansion = max(1.2, size_ratio * 1.1)
                expansion = min(expansion, 3.0)
                expand_so_canvas(app, doc, expansion)
                pct = int((expansion - 1.0) * 100)
                logger.log_info(
                    f"BOUNDARY PROTECT [{record.layer_path}]: Expanded SO canvas by {pct}% "
                    f"(scale={expansion:.3f}, size_ratio={size_ratio:.3f})"
                )
            except Exception as e:
                logger.log_warning(f"BOUNDARY PROTECT [{record.layer_path}]: {str(e)}")

        # ===== Method B: verify real rendered height, refine if needed =====
        try:
            real_h = real_bounds_h(app, layer)
            logger.log_info(
                f"VERIFY [{record.layer_path}]: real_h={real_h:.2f}px target={record.bounds_h_px:.2f}px "
                f"diff={real_h - record.bounds_h_px:+.2f}px"
            )

            max_refine = 5 if record.faux_bold else 3
            refine_converge_px = 4.0 if record.faux_bold else 2.0
            _refine_safety = False
            for refine_iter in range(1, max_refine + 1):
                diff = real_h - record.bounds_h_px
                if abs(diff) < refine_converge_px:
                    if refine_iter == 1:
                        break  # first REFINE hit — skip safety
                    if _refine_safety:
                        break
                    _refine_safety = True
                ratio = record.bounds_h_px / real_h if real_h > 0.5 else 1.0
                new_size_pt = params.size_pt * ratio
                try:
                    com_retry(setattr, app, "ActiveDocument", doc)
                    com_retry(setattr, doc, "ActiveLayer", layer)
                    ti = layer.TextItem
                    ti.Size = new_size_pt
                    if not params.auto_leading:
                        new_leading = params.leading_pt * ratio
                        ti.Leading = new_leading
                        params.leading_pt = new_leading
                        params.leading_px = pt_to_px(new_leading, record.dpi)
                    params.size_pt = new_size_pt
                    params.size_px = pt_to_px(new_size_pt, record.dpi)
                except Exception as e:
                    logger.log_error(f"refine iter {refine_iter} '{record.layer_path}'", e)
                    break
                real_h = real_bounds_h(app, layer)
                logger.log_info(
                    f"REFINE {refine_iter} [{record.layer_path}]: size={new_size_pt:.4f}pt "
                    f"real_h={real_h:.2f}px target={record.bounds_h_px:.2f}px"
                )

            params.final_bounds_h_px = real_h
            params.target_h_px = record.bounds_h_px
            final_conv_px = 6.0 if record.faux_bold else 3.0
            params.converged = abs(real_h - record.bounds_h_px) < final_conv_px
        except Exception as e:
            logger.log_error(f"verify '{record.layer_path}'", e)

        logger.log_apply_result(record.layer_path, params, record)
        logger.log_layer_after(record, params)
        return params
    except Exception as e:
        logger.log_error(f"apply layer '{record.layer_path}'", e)
        return None


def real_bounds_h(app, art_layer) -> float:
    """Measure the real rendered height of a layer in pixels."""
    bounds = layer_bounds_px(app, art_layer)
    return float(bounds[3]) - float(bounds[1])


def apply_params_to_layer(app, doc, art_layer, params: AdaptedParams,
                          record: TextLayerRecord, logger) -> None:
    """Apply adapted parameters to a real Photoshop text layer.

    Sets Font, Size, UseAutoLeading, Leading, Tracking, and Contents
    with per-property error handling so one failure doesn't block others.
    """
    try:
        com_retry(setattr, app, "ActiveDocument", doc)
        com_retry(setattr, doc, "ActiveLayer", art_layer)
    except Exception:
        pass
    ti = art_layer.TextItem
    try:
        ti.Font = params.font_ps
    except Exception:
        try:
            ti.Font = params.font_ps.replace(" ", "-")
        except Exception as e:
            logger.log_error(f"set Font on '{record.layer_path}'", e)
    try:
        ti.Size = params.size_pt
    except Exception as e:
        logger.log_error(f"set Size on '{record.layer_path}'", e)
    try:
        ti.UseAutoLeading = params.auto_leading
    except Exception as e:
        logger.log_error(f"set UseAutoLeading on '{record.layer_path}'", e)
    if not params.auto_leading:
        try:
            ti.Leading = params.leading_pt
        except Exception as e:
            logger.log_error(f"set Leading on '{record.layer_path}'", e)
    try:
        ti.Tracking = params.tracking
    except Exception as e:
        logger.log_error(f"set Tracking on '{record.layer_path}'", e)
    new_text = record.new_text if record.new_text is not None else record.text
    try:
        ti.Contents = new_text
    except Exception as e:
        logger.log_error(f"set Contents on '{record.layer_path}'", e)


def resolve_font_for_record(record: TextLayerRecord, font_index: dict, logger) -> str:
    """Resolve target font PS name from record's new_font_family/weight.

    Returns the resolved PostScript font name, or the original font as fallback.
    """
    if not record.new_font_family or not record.new_font_family.strip():
        return record.font
    target_weight = (record.new_font_weight or "").strip()
    ps_name = resolve_font(
        font_index=font_index,
        target_family=record.new_font_family,
        target_weight_kw=target_weight,
        preserve_italic=False,
        original_ps_name=record.font,
    )
    if ps_name is None:
        logger.log_warning(
            f"Font family '{record.new_font_family}' not found. "
            f"Falling back to original font '{record.font}'."
        )
        return record.font
    logger.log_info(
        f"Font resolved: family='{record.new_font_family}' weight='{record.new_font_weight}' "
        f"-> PS name='{ps_name}'"
    )
    return ps_name
