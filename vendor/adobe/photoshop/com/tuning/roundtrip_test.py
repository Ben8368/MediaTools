#!/usr/bin/env python
"""往返测试脚本 — 验证 PSA 自适应算法精度与效率.

用法:
  python roundtrip_test.py --psd smoke.psd --mode quick       # 快速往返
  python roundtrip_test.py --psd baseline.psd --mode full      # 标准往返
  python roundtrip_test.py --psd baseline.psd --mode full --round round3
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure src modules are importable
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from text_utils import (
    get_app,
    safe_get,
    enter_smart_object,
    layer_bounds_px,
    PSAError,
)
from document_scanner import scan_document
from text_models import TextLayerRecord, AdaptedParams
from text_logger import PSALogger
from adaptive_lab import LabDocument
from font_resolver import build_font_index, resolve_font
from psa_applier import process_layer, resolve_font_for_record
from smart_object_handler import outermost_key, find_outermost_so, process_so_level


# ═══════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════


def mirror_text(text: str) -> str:
    """Photoshop 换行符感知的逐行镜像."""
    if not text:
        return text
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return "\r".join(line[::-1] for line in lines)


def _extract_font_family(postscript_name: str) -> str:
    """从 PostScript 名提取家族名，如 ByteSans-Bold → ByteSans."""
    if not postscript_name:
        return ""
    if "-" in postscript_name:
        return postscript_name.split("-")[0]
    return postscript_name


# ═══════════════════════════════════════════════════════════════════════════
# scan
# ═══════════════════════════════════════════════════════════════════════════


def scan_psd(app, psd_path: str, logger: PSALogger) -> list[TextLayerRecord]:
    """Open *psd_path*, scan all text layers, close."""
    doc = app.Open(psd_path)
    try:
        return scan_document(app, doc, logger)
    finally:
        try:
            doc.Close(2)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# apply
# ═══════════════════════════════════════════════════════════════════════════


def _apply_direct_layers(
    app, doc, records: list[TextLayerRecord],
    dpi: float, logger: PSALogger,
) -> None:
    if not records:
        return
    app.ActiveDocument = doc
    with LabDocument(app, dpi) as lab:
        for r in records:
            try:
                process_layer(app, doc, r, lab, logger, in_so=False)
            except Exception as exc:
                logger.log_error(f"apply direct '{r.layer_path}'", exc)


def _apply_process_layer_callback(
    app, doc, record: TextLayerRecord,
    lab: LabDocument, logger: PSALogger,
    **kwargs,
):
    """Callback for process_so_level — delegates to PSA's process_layer."""
    return process_layer(app, doc, record, lab, logger, in_so=True)


def _apply_so_groups(
    app, doc, records: list[TextLayerRecord],
    dpi: float, logger: PSALogger,
) -> None:
    """Group SO records by outermost key, enter each SO, process recursively."""
    groups: dict[str, list[TextLayerRecord]] = {}
    for r in records:
        key = outermost_key(r)
        groups.setdefault(key, []).append(r)

    for key, group in groups.items():
        so_layer = find_outermost_so(app, doc, key, group, logger)
        if so_layer is None:
            logger.log_error(f"SO group '{key}'", PSAError("outermost SO not found"))
            continue

        try:
            app.ActiveDocument = doc
            so_doc = enter_smart_object(app, so_layer)
        except Exception as exc:
            logger.log_error(f"enter SO '{key}'", exc)
            continue

        try:
            so_dpi = float(safe_get(so_doc, "Resolution", dpi))
            process_so_level(
                app, so_doc, group, logger, so_dpi, depth=1,
                _process_layer_func=_apply_process_layer_callback,
            )
            so_doc.Save()
            so_doc.Close(1)
        except Exception as exc:
            logger.log_error(f"process SO group '{key}'", exc)
            try:
                so_doc.Close(2)
            except Exception:
                pass


def apply_workorder(
    source_psd: str,
    records: list[TextLayerRecord],
    output_psd: str,
    logger: PSALogger,
    font_family_override: str = "",
) -> str:
    """Apply modifications in *records* to a copy of *source_psd*, save as *output_psd*.

    Args:
        source_psd: Path to the original PSD.
        records: TextLayerRecord list with new_text / new_font_family already set.
        output_psd: Where to write the modified copy.
        logger: PSALogger instance.
        font_family_override: If set, override every record's font family.

    Returns:
        *output_psd*.
    """
    app = get_app()
    font_index = build_font_index(app)
    logger.log_info(f"Font index: {len(font_index)} families")

    # Resolve fonts and prepare records
    enabled: list[TextLayerRecord] = []
    for r in records:
        if r.multi_style:
            logger.log_warning(f"SKIP multi-style [{r.layer_path}]")
            continue
        if font_family_override:
            r.new_font_family = font_family_override
            r.new_font_weight = ""
        if r.new_font_family and r.new_font_family.strip():
            r.new_font_ps = resolve_font_for_record(r, font_index, logger)
        else:
            r.new_font_ps = None
        r.enabled = True
        enabled.append(r)

    if not enabled:
        logger.log_info("No enabled records to process.")
        return output_psd

    # Create working copy
    shutil.copy2(source_psd, output_psd)
    logger.log_info(f"Working copy: {output_psd}")

    doc = app.Open(output_psd)
    try:
        dpi = float(safe_get(doc, "Resolution", 72.0))
        direct = [r for r in enabled if not r.in_smart_object]
        so = [r for r in enabled if r.in_smart_object]

        logger.log_info(f"Processing {len(direct)} direct + {len(so)} SO layers")

        _apply_direct_layers(app, doc, direct, dpi, logger)
        _apply_so_groups(app, doc, so, dpi, logger)

        doc.Save()
        doc.Close(1)
    except Exception:
        try:
            doc.Close(2)
        except Exception:
            pass
        raise

    logger.log_info(f"Done: {output_psd}")
    return output_psd


# ═══════════════════════════════════════════════════════════════════════════
# compare
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class LayerDiff:
    layer_path: str
    layer_name: str
    in_smart_object: bool
    multi_style: bool
    # original
    orig_text: str
    orig_font: str
    orig_size_pt: float
    orig_tracking: float
    orig_bounds_h: float
    orig_leading_pt: float
    # roundtrip
    rt_text: str
    rt_font: str
    rt_size_pt: float
    rt_tracking: float
    rt_bounds_h: float
    rt_leading_pt: float
    # computed
    text_restored: bool
    font_restored: bool
    size_drift_pct: float
    tracking_drift: float
    bounds_drift_px: float
    leading_drift: float


@dataclass
class ComparisonReport:
    source_psd: str
    mode: str
    round_name: str
    total_layers: int
    matched: int
    multi_style_skipped: int
    layers: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_psd": self.source_psd,
            "mode": self.mode,
            "round": self.round_name,
            "total_layers": self.total_layers,
            "matched": self.matched,
            "multi_style_skipped": self.multi_style_skipped,
            "summary": self.summary,
            "layers": self.layers,
        }


def compare(
    orig_records: list[TextLayerRecord],
    rt_records: list[TextLayerRecord],
    source_psd: str,
    mode: str,
    round_name: str,
) -> ComparisonReport:
    """Compare original and roundtrip scan results by layer_path."""
    orig_by_path: dict[str, TextLayerRecord] = {}
    for r in orig_records:
        if r.multi_style:
            continue
        orig_by_path[r.layer_path] = r

    rt_by_path: dict[str, TextLayerRecord] = {r.layer_path: r for r in rt_records if not r.multi_style}

    diffs: list[LayerDiff] = []
    for path, orig in orig_by_path.items():
        rt = rt_by_path.get(path)
        if rt is None:
            continue

        diffs.append(LayerDiff(
            layer_path=path,
            layer_name=orig.layer_name,
            in_smart_object=orig.in_smart_object,
            multi_style=False,
            orig_text=orig.text,
            orig_font=orig.font,
            orig_size_pt=orig.size_pt,
            orig_tracking=orig.tracking,
            orig_bounds_h=orig.bounds_h_px,
            orig_leading_pt=orig.leading_pt,
            rt_text=rt.text,
            rt_font=rt.font,
            rt_size_pt=rt.size_pt,
            rt_tracking=rt.tracking,
            rt_bounds_h=rt.bounds_h_px,
            rt_leading_pt=rt.leading_pt,
            text_restored=orig.text.strip() == rt.text.strip(),
            font_restored=orig.font == rt.font,
            size_drift_pct=abs(rt.size_pt - orig.size_pt) / max(orig.size_pt, 0.1) * 100,
            tracking_drift=abs(rt.tracking - orig.tracking),
            bounds_drift_px=abs(rt.bounds_h_px - orig.bounds_h_px),
            leading_drift=abs(rt.leading_pt - orig.leading_pt),
        ))

    if not diffs:
        return ComparisonReport(
            source_psd=source_psd, mode=mode, round_name=round_name,
            total_layers=len(orig_records), matched=0, multi_style_skipped=0,
            summary={"error": "no matching layers found"},
        )

    n = len(diffs)
    text_restored_n = sum(1 for d in diffs if d.text_restored)
    font_restored_n = sum(1 for d in diffs if d.font_restored)

    report = ComparisonReport(
        source_psd=source_psd,
        mode=mode,
        round_name=round_name,
        total_layers=len(orig_records),
        matched=n,
        multi_style_skipped=sum(1 for r in orig_records if r.multi_style),
        layers=[d.__dict__ for d in diffs],
        summary={
            "text_restoration_rate": round(text_restored_n / n, 4),
            "font_restoration_rate": round(font_restored_n / n, 4),
            "avg_size_drift_pct": round(sum(d.size_drift_pct for d in diffs) / n, 2),
            "avg_tracking_drift": round(sum(d.tracking_drift for d in diffs) / n, 2),
            "avg_bounds_drift_px": round(sum(d.bounds_drift_px for d in diffs) / n, 2),
            "avg_leading_drift": round(sum(d.leading_drift for d in diffs) / n, 2),
            "max_size_drift_pct": round(max(d.size_drift_pct for d in diffs), 2),
            "max_tracking_drift": round(max(d.tracking_drift for d in diffs), 2),
            "max_bounds_drift_px": round(max(d.bounds_drift_px for d in diffs), 2),
        },
    )
    return report


# ═══════════════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════════════


def _parse_args():
    p = argparse.ArgumentParser(description="PS 自适应算法往返测试")
    p.add_argument("--psd", required=True, help="母版 PSD 路径")
    p.add_argument(
        "--mode", choices=("quick", "full"), default="quick",
        help="quick: 仅镜像不改字体; full: 镜像 + Noto Sans↔Byte Sans 换字体",
    )
    p.add_argument("--round", default="", help="轮次名，用于输出文件前缀")
    return p.parse_args()


def _make_log_path(output_dir: str, stem: str, round_name: str, step: str) -> str:
    prefix = f"{round_name}_" if round_name else ""
    return os.path.join(output_dir, f"{prefix}{step}.log")


def _make_comparison_path(output_dir: str, round_name: str) -> str:
    prefix = f"{round_name}_" if round_name else ""
    return os.path.join(output_dir, f"{prefix}comparison.json")


def main():
    args = _parse_args()
    psd_path = os.path.abspath(args.psd)
    output_dir = os.path.dirname(psd_path)
    stem = Path(psd_path).stem
    round_name = args.round
    mode = args.mode

    print(f"=== PS Roundtrip Test ===")
    print(f"  PSD: {psd_path}")
    print(f"  Mode: {mode}")
    print(f"  Round: {round_name or '(auto)'}")
    print(f"  Output dir: {output_dir}")

    t0 = time.time()

    # ── Step 1: scan original ──────────────────────────────────────────
    print("\n[Step 1a] Scanning original...")
    app = get_app()
    step1_scan_log = _make_log_path(output_dir, stem, round_name, "step1_scan")
    logger1s = PSALogger(step1_scan_log)
    orig_records = scan_psd(app, psd_path, logger1s)
    logger1s.close()
    print(f"  Found {len(orig_records)} text layers")

    if not orig_records:
        print("ERROR: No text layers found. Aborting.")
        sys.exit(1)

    # ── Step 1: prepare modifications ───────────────────────────────────
    print("\n[Step 1b] Preparing modifications...")
    target_font = "Byte Sans" if mode == "full" else ""
    step1_records = []
    for r in orig_records:
        r2 = TextLayerRecord(
            layer_id=r.layer_id, layer_name=r.layer_name, layer_path=r.layer_path,
            in_smart_object=r.in_smart_object,
            so_layer_id=r.so_layer_id, so_layer_path=r.so_layer_path,
            so_psb_name=r.so_psb_name,
            text=r.text, font=r.font,
            size_pt=r.size_pt, size_px=r.size_px,
            tracking=r.tracking,
            auto_leading=r.auto_leading, leading_pt=r.leading_pt, leading_px=r.leading_px,
            bounds_left=r.bounds_left, bounds_top=r.bounds_top,
            bounds_right=r.bounds_right, bounds_bottom=r.bounds_bottom,
            bounds_h_px=r.bounds_h_px, dpi=r.dpi,
            faux_bold=r.faux_bold, faux_italic=r.faux_italic,
            new_text=mirror_text(r.text),
            new_font_family=target_font if target_font else None,
            new_font_weight="",
            enabled=True, so_chain=r.so_chain, multi_style=r.multi_style,
        )
        step1_records.append(r2)

    # ── Step 1: execute ─────────────────────────────────────────────────
    step1_output = os.path.join(output_dir, f"{stem}-mirror.psd")
    print(f"\n[Step 1c] Executing → {os.path.basename(step1_output)}")
    step1_exec_log = _make_log_path(output_dir, stem, round_name, "step1_execute")
    logger1e = PSALogger(step1_exec_log)
    t_step1 = time.time()
    apply_workorder(psd_path, step1_records, step1_output, logger1e, font_family_override=target_font)
    t_step1 = time.time() - t_step1
    logger1e.close()
    print(f"  Step 1 done in {t_step1:.1f}s")

    # ── Step 2: scan mirror result ──────────────────────────────────────
    print("\n[Step 2a] Scanning mirror result...")
    step2_scan_log = _make_log_path(output_dir, stem, round_name, "step2_scan")
    logger2s = PSALogger(step2_scan_log)
    mirror_records = scan_psd(app, step1_output, logger2s)
    logger2s.close()
    print(f"  Found {len(mirror_records)} text layers")

    # ── Step 2: prepare restore modifications ────────────────────────────
    print("\n[Step 2b] Preparing restore...")
    restore_font = "Noto Sans" if mode == "full" else ""
    step2_records = []
    for r in mirror_records:
        r2 = TextLayerRecord(
            layer_id=r.layer_id, layer_name=r.layer_name, layer_path=r.layer_path,
            in_smart_object=r.in_smart_object,
            so_layer_id=r.so_layer_id, so_layer_path=r.so_layer_path,
            so_psb_name=r.so_psb_name,
            text=r.text, font=r.font,
            size_pt=r.size_pt, size_px=r.size_px,
            tracking=r.tracking,
            auto_leading=r.auto_leading, leading_pt=r.leading_pt, leading_px=r.leading_px,
            bounds_left=r.bounds_left, bounds_top=r.bounds_top,
            bounds_right=r.bounds_right, bounds_bottom=r.bounds_bottom,
            bounds_h_px=r.bounds_h_px, dpi=r.dpi,
            faux_bold=r.faux_bold, faux_italic=r.faux_italic,
            new_text=mirror_text(r.text),
            new_font_family=restore_font if restore_font else None,
            new_font_weight="",
            enabled=True, so_chain=r.so_chain, multi_style=r.multi_style,
        )
        step2_records.append(r2)

    # ── Step 2: execute restore ─────────────────────────────────────────
    step2_output = os.path.join(output_dir, f"{stem}-mirror-mirror.psd")
    print(f"\n[Step 2c] Executing restore → {os.path.basename(step2_output)}")
    step2_exec_log = _make_log_path(output_dir, stem, round_name, "step2_execute")
    logger2e = PSALogger(step2_exec_log)
    t_step2 = time.time()
    apply_workorder(step1_output, step2_records, step2_output, logger2e, font_family_override=restore_font)
    t_step2 = time.time() - t_step2
    logger2e.close()
    print(f"  Step 2 done in {t_step2:.1f}s")

    # ── Step 3: compare ─────────────────────────────────────────────────
    print("\n[Step 3] Comparing...")
    comp_scan_log = _make_log_path(output_dir, stem, round_name, "step3_scan_rt")
    logger3 = PSALogger(comp_scan_log)
    rt_records = scan_psd(app, step2_output, logger3)
    logger3.close()

    report = compare(orig_records, rt_records, psd_path, mode, round_name)

    # Inject timing info
    report.summary["step1_time_s"] = round(t_step1, 1)
    report.summary["step2_time_s"] = round(t_step2, 1)
    report.summary["total_time_s"] = round(time.time() - t0, 1)

    comp_path = _make_comparison_path(output_dir, round_name)
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    # ── Print summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"COMPARISON SUMMARY")
    print(f"{'='*60}")
    s = report.summary
    print(f"  Total layers:      {report.total_layers}")
    print(f"  Matched:           {report.matched}")
    print(f"  Multi-style skip:  {report.multi_style_skipped}")
    print(f"  Text restored:     {s['text_restoration_rate']*100:.1f}%")
    if mode == "full":
        print(f"  Font restored:     {s['font_restoration_rate']*100:.1f}%")
    print(f"  Avg size drift:    {s['avg_size_drift_pct']:.2f}%")
    print(f"  Avg tracking drift:{s['avg_tracking_drift']:.2f}")
    print(f"  Avg bounds drift:  {s['avg_bounds_drift_px']:.2f}px")
    print(f"  Max size drift:    {s['max_size_drift_pct']:.2f}%")
    print(f"  Max tracking drift:{s['max_tracking_drift']:.2f}")
    print(f"  Max bounds drift:  {s['max_bounds_drift_px']:.2f}px")
    print(f"  Step1 time:        {s['step1_time_s']:.1f}s")
    print(f"  Step2 time:        {s['step2_time_s']:.1f}s")
    print(f"  Total time:        {s['total_time_s']:.1f}s")
    print(f"\n  Report: {comp_path}")

    # Quick pass/fail for quick mode
    if mode == "quick":
        text_ok = s["text_restoration_rate"] >= 1.0
        no_bug = text_ok
        print(f"\n  QUICK CHECK: {'PASS' if no_bug else 'FAIL'}")
        if not text_ok:
            print(f"  WARNING: text restoration rate < 100% — possible mirror or pipeline bug")

    print(f"\nDONE in {s['total_time_s']:.1f}s")


if __name__ == "__main__":
    main()
