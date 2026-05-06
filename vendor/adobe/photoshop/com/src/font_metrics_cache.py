"""
空白工程验证法：测量字体 metrics 缩放比例
key = (source_font, target_font, original_text) 用实际文字测量，精确反映每个图层的真实 scale

注意：使用 px 模式测量，测量文档固定为 72 DPI，此时 72px = 72pt
"""

import csv
import os
import time
from dataclasses import dataclass

_PROBE_SIZE = 72.0  # 使用 72px 作为基准尺寸（在 72 DPI 文档中等于 72pt）


@dataclass
class FontMetrics:
    source_font: str
    target_font: str
    text: str
    width_scale: float
    height_scale: float


def _resolve_target_font(ps, source_font: str, target_font_spec: str) -> str:
    if "-" in target_font_spec:
        return target_font_spec
    try:
        from font_weight_mapper import find_closest_weight
        available = ps.get_available_weights(target_font_spec)
        if not available:
            return target_font_spec
        return find_closest_weight(source_font, target_font_spec, available)
    except Exception:
        return target_font_spec


def _measure_font_bounds(app, font_name: str, text: str, size: float):
    doc = None
    try:
        doc = app.Documents.Add(2000, 400, 72, "metrics_probe", 2, 1, 1)
        time.sleep(0.1)
        layer = doc.ArtLayers.Add()
        layer.Kind = 2
        ti = layer.TextItem
        ti.Contents = text
        ti.Font = font_name
        ti.Size = size
        time.sleep(0.1)
        bounds = layer.Bounds
        w = float(bounds[2]) - float(bounds[0])
        h = float(bounds[3]) - float(bounds[1])
        return w, h
    except Exception as e:
        print(f"    [metrics] 测量失败 {font_name!r}: {e}")
        return None
    finally:
        if doc is not None:
            try:
                doc.Close(2)
            except Exception:
                pass


def build_font_metrics(ps, ticket_rows: list, cache_path: str) -> dict:
    """
    从工单中收集所有 (source_font, target_font, original_text) 组合，
    用实际文字在临时文档里测量 scale，写入缓存。
    """
    # 收集需要测量的三元组
    triples: set[tuple[str, str, str]] = set()
    for row in ticket_rows:
        sf = (row.source_font or "").strip()
        tf_spec = (row.target_font or "").strip()
        text = (row.original_text or "").strip()
        if sf and tf_spec and sf != tf_spec and text:
            triples.add((sf, tf_spec, text))

    if not triples:
        print("  [font_metrics] 没有需要测量的条目")
        return {}

    existing = load_font_metrics(cache_path)
    results = dict(existing)

    app = ps.app
    orig_ruler = app.Preferences.RulerUnits
    orig_type = app.Preferences.TypeUnits
    app.Preferences.RulerUnits = 1  # psPixels
    app.Preferences.TypeUnits = 5   # psTypePixels (px 模式)

    try:
        # resolve target font 并去重
        to_measure: dict[tuple[str, str, str], bool] = {}
        for sf, tf_spec, text in sorted(triples):
            resolved = _resolve_target_font(ps, sf, tf_spec)
            key = (sf, resolved, text)
            to_measure[key] = True

        need = [(sf, rt, tx) for (sf, rt, tx) in to_measure if (sf, rt, tx) not in results]
        print(f"  [font_metrics] 需要测量 {len(need)} 条（共 {len(to_measure)} 条，已缓存 {len(to_measure)-len(need)} 条）")

        for sf, resolved_target, text in sorted(need):
            key = (sf, resolved_target, text)
            short_text = text[:20].replace("\r", " ").replace("\n", " ")
            print(f"    [measure] {sf} -> {resolved_target} | {short_text!r}")

            src_bounds = _measure_font_bounds(app, sf, text, _PROBE_SIZE)
            tgt_bounds = _measure_font_bounds(app, resolved_target, text, _PROBE_SIZE)

            if src_bounds is None or tgt_bounds is None:
                print(f"    [skip] 测量失败")
                continue
            src_w, src_h = src_bounds
            tgt_w, tgt_h = tgt_bounds
            if src_w <= 0 or src_h <= 0:
                print(f"    [skip] 原字体 Bounds 为零")
                continue

            w_scale = tgt_w / src_w
            h_scale = tgt_h / src_h
            results[key] = FontMetrics(sf, resolved_target, text, w_scale, h_scale)
            print(f"    [ok] w={w_scale:.4f}, h={h_scale:.4f}, max={max(w_scale,h_scale):.4f}")

    finally:
        app.Preferences.RulerUnits = orig_ruler
        app.Preferences.TypeUnits = orig_type

    _write_font_metrics(results, cache_path)
    print(f"  [font_metrics] 缓存已写入: {cache_path} ({len(results)} 条)")
    return results


def load_font_metrics(cache_path: str) -> dict:
    if not os.path.exists(cache_path):
        return {}
    results = {}
    try:
        with open(cache_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                sf = row["source_font"].strip()
                tf = row["target_font"].strip()
                text = row.get("text", "").strip()
                key = (sf, tf, text)
                results[key] = FontMetrics(
                    source_font=sf,
                    target_font=tf,
                    text=text,
                    width_scale=float(row["width_scale"]),
                    height_scale=float(row["height_scale"]),
                )
    except Exception as e:
        print(f"  [font_metrics] 读取缓存失败: {e}")
    return results


def _write_font_metrics(metrics: dict, cache_path: str) -> None:
    os.makedirs(os.path.dirname(cache_path) if os.path.dirname(cache_path) else ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source_font", "target_font", "text", "width_scale", "height_scale"])
        writer.writeheader()
        for m in sorted(metrics.values(), key=lambda x: (x.source_font, x.target_font, x.text)):
            writer.writerow({
                "source_font": m.source_font,
                "target_font": m.target_font,
                "text": m.text,
                "width_scale": f"{m.width_scale:.6f}",
                "height_scale": f"{m.height_scale:.6f}",
            })


def get_size_scale(metrics: dict, source_font: str, target_font: str, text: str = "") -> float:
    """
    查询字号缩放比例：new_size = original_size / get_size_scale(...)
    优先用精确 key (source_font, target_font, text)，
    fallback 到 (source_font, target_font, "") 通用 key。
    """
    key = (source_font, target_font, text)
    if key in metrics:
        m = metrics[key]
        return max(m.width_scale, m.height_scale)
    # fallback: 无文字 key
    key_generic = (source_font, target_font, "")
    if key_generic in metrics:
        m = metrics[key_generic]
        return max(m.width_scale, m.height_scale)
    return 1.0
