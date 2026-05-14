"""
Round-trip optimization test: mirror text + font swap twice, compare with original.
Step 1: test.psd → mirror text + Noto→Byte Sans → test_mirror.psd
Step 2: test_mirror.psd → mirror text + Byte→Noto Sans → test_mirror_mirror.psd
Compare: test.psd (original) vs test_mirror_mirror.psd (round-trip)
"""
import sys, os, json, shutil, time
from pathlib import Path
from dataclasses import dataclass, field, asdict

sys.path.insert(0, r"C:\MediaTools\vendor\adobe\photoshop\com\src")

from ps_connector import PhotoshopConnector
from document_scanner import scan_document
from text_logger import PSALogger
from text_models import TextLayerRecord
from font_resolver import build_font_index
from psa_applier import process_layer, resolve_font_for_record
from adaptive_lab import LabDocument
from text_utils import safe_get, enter_smart_object
from smart_object_handler import outermost_key, process_so_level

BASE_DIR = Path(r"C:\MediaTools\test")
SRC_PSD = BASE_DIR / "test.psd"
MIRROR_PSD = BASE_DIR / "test_mirror.psd"
ROUNDTRIP_PSD = BASE_DIR / "test_mirror_mirror.psd"


def mirror_text(text: str) -> str:
    if not text:
        return text
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return "\r".join(line[::-1] for line in lines)


def scan_psd(ps, psd_path, log_path):
    """Scan a PSD and return records + DPI."""
    logger = PSALogger(str(log_path))
    if os.path.exists(str(psd_path)):
        shutil.copy2(str(psd_path), str(psd_path).replace(".psd", "_work.psd"))
        work_path = str(psd_path).replace(".psd", "_work.psd")
    else:
        work_path = str(psd_path)
    doc = ps.open_document(work_path)
    dpi = float(safe_get(doc, "Resolution", 72.0))
    logger.log_info(f"Scanning: {psd_path}, DPI={dpi}")
    records = scan_document(ps.app, doc, logger)
    logger.log_info(f"Found {len(records)} text layers")
    logger.close()
    return doc, records, dpi, work_path


def apply_changes(ps, doc, records, font_index, target_family, log_path):
    """Apply text mirroring and font change to records, then process all layers."""
    logger = PSALogger(str(log_path))
    dpi = float(safe_get(doc, "Resolution", 72.0))

    modified = 0
    skipped_multi = 0
    for r in records:
        stripped = (r.text or "").strip()
        if not stripped:
            r.enabled = False
            continue
        if r.multi_style:
            logger.log_warning(f"SKIP multi-style: {r.layer_path}")
            r.enabled = False
            skipped_multi += 1
            continue
        r.new_text = mirror_text(r.text)
        r.new_font_family = target_family
        r.new_font_weight = ""
        r.enabled = True
        modified += 1
        r.new_font_ps = resolve_font_for_record(r, font_index, logger)

    if skipped_multi:
        logger.log_info(f"Skipped {skipped_multi} multi-style layer(s)")

    logger.log_info(f"Enabled {modified}/{len(records)} layers for modification")

    direct = [r for r in records if r.enabled and not r.in_smart_object]
    so_records = [r for r in records if r.enabled and r.in_smart_object]

    # -- Group all work by DPI so we can reuse lab documents --
    # Collect: (doc, record, in_so) tuples keyed by DPI
    from collections import defaultdict
    work_by_dpi = defaultdict(list)

    if direct:
        work_by_dpi[dpi].extend([(doc, r, False) for r in direct])

    if so_records:
        groups = {}
        for r in so_records:
            key = outermost_key(r)
            groups.setdefault(key, []).append(r)
        logger.log_info(f"Grouped into {len(groups)} SO groups")

        from smart_object_handler import find_outermost_so
        for key, group in groups.items():
            so_layer = find_outermost_so(ps.app, doc, key, group, logger)
            if so_layer is None:
                logger.log_error(f"find outermost SO '{key}'", Exception("not found"))
                continue
            try:
                ps.app.ActiveDocument = doc
                so_doc = enter_smart_object(ps.app, so_layer)
                so_dpi = float(safe_get(so_doc, "Resolution", dpi))
            except Exception as e:
                logger.log_error(f"enter SO '{key}'", e)
                continue
            # Register SO doc reference so we can close it later
            work_by_dpi[so_dpi].append((so_doc, group, key))

    # -- Process each DPI group with a shared lab --
    total_lab_creations = 0
    for group_dpi, items in work_by_dpi.items():
        logger.log_info(f"Creating LabDocument(DPI={group_dpi}) for {len(items)} work items")
        total_lab_creations += 1
        with LabDocument(ps.app, group_dpi) as lab:
            for item in items:
                if len(item) == 3 and isinstance(item[1], list):
                    # SO group: (so_doc, group_records, key)
                    so_doc, group, key = item
                    try:
                        process_so_level(ps.app, so_doc, group, logger, group_dpi, depth=1,
                                         _process_layer_func=process_layer)
                        try:
                            so_doc.Save()
                            so_doc.Close(1)
                            logger.log_info(f"  SO saved: {key}")
                        except Exception as e:
                            logger.log_error(f"save/close SO '{key}'", e)
                    except Exception as e:
                        logger.log_error(f"process SO '{key}'", e)
                        try:
                            so_doc.Close(2)
                        except Exception:
                            pass
                else:
                    # Direct layer: (doc, record, in_so)
                    item_doc, record, in_so = item
                    try:
                        process_layer(ps.app, item_doc, record, lab, logger, in_so=in_so)
                        lab.clear()
                    except Exception as e:
                        logger.log_error(f"process_layer '{record.layer_path}'", e)

    logger.log_info(f"Total LabDocument creations: {total_lab_creations} (was 52 before optimization)")

    ps.app.ActiveDocument = doc
    doc.Save()
    logger.log_info(f"Saved document")
    logger.close()


def compare_psds(ps, original_path, roundtrip_path, output_json):
    """Scan both PSDs and compare layer-by-layer."""
    # Scan original
    orig_log = str(BASE_DIR / "compare_orig.log")
    orig_doc, orig_records, orig_dpi, orig_work = scan_psd(ps, original_path, orig_log)
    orig_by_id = {r.layer_id: r for r in orig_records}
    ps.close_document(orig_doc, save=False)

    # Scan round-trip
    rt_log = str(BASE_DIR / "compare_roundtrip.log")
    rt_doc, rt_records, rt_dpi, rt_work = scan_psd(ps, roundtrip_path, rt_log)
    rt_by_id = {r.layer_id: r for r in rt_records}
    ps.close_document(rt_doc, save=False)

    # Compare
    comparisons = []
    total_size_drift = 0.0
    total_h_drift = 0.0
    total_tracking_drift = 0.0
    total_leading_drift = 0.0
    font_mismatches = 0
    count = 0

    for lid, orig in sorted(orig_by_id.items()):
        rt = rt_by_id.get(lid)
        if rt is None:
            comparisons.append({"layer_id": lid, "layer_path": orig.layer_path, "error": "not found in round-trip"})
            continue
            continue
        count += 1

        size_drift_pct = (rt.size_pt - orig.size_pt) / max(orig.size_pt, 0.1) * 100
        h_drift = rt.bounds_h_px - orig.bounds_h_px
        tracking_drift = rt.tracking - orig.tracking
        leading_drift = rt.leading_pt - orig.leading_pt

        # Check font family restoration
        orig_family = orig.font.split("-")[0] if "-" in orig.font else orig.font
        rt_family = rt.font.split("-")[0] if "-" in rt.font else rt.font
        font_restored = orig_family.lower() == rt_family.lower()

        total_size_drift += abs(size_drift_pct)
        total_h_drift += abs(h_drift)
        total_tracking_drift += abs(tracking_drift)
        total_leading_drift += abs(leading_drift)
        if not font_restored:
            font_mismatches += 1

        comparisons.append({
            "layer_path": orig.layer_path,
            "in_smart_object": orig.in_smart_object,
            "orig_font": orig.font,
            "rt_font": rt.font,
            "font_restored": font_restored,
            "orig_size_pt": round(orig.size_pt, 4),
            "rt_size_pt": round(rt.size_pt, 4),
            "size_drift_pct": round(size_drift_pct, 2),
            "orig_tracking": orig.tracking,
            "rt_tracking": rt.tracking,
            "tracking_drift": round(tracking_drift, 1),
            "orig_leading_pt": round(orig.leading_pt, 4),
            "rt_leading_pt": round(rt.leading_pt, 4),
            "leading_drift": round(leading_drift, 2),
            "orig_bounds_h": round(orig.bounds_h_px, 2),
            "rt_bounds_h": round(rt.bounds_h_px, 2),
            "h_drift_px": round(h_drift, 2),
            "orig_text": orig.text[:60],
            "rt_text": rt.text[:60],
            "text_restored": orig.text == rt.text,
        })

    summary = {
        "total_layers": len(orig_records),
        "matched_layers": count,
        "avg_size_drift_pct": round(total_size_drift / max(count, 1), 2),
        "avg_h_drift_px": round(total_h_drift / max(count, 1), 2),
        "avg_tracking_drift": round(total_tracking_drift / max(count, 1), 2),
        "avg_leading_drift": round(total_leading_drift / max(count, 1), 2),
        "font_mismatches": font_mismatches,
        "text_mismatches": sum(1 for c in comparisons if not c.get("text_restored", True)),
    }

    # Sort by size drift (worst first) for analysis
    comparisons.sort(key=lambda c: abs(c.get("size_drift_pct", 0)), reverse=True)

    report = {"summary": summary, "layers": comparisons}
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main():
    print("=" * 60)
    print("ROUND-TRIP OPTIMIZATION TEST")
    print("=" * 60)

    ps = PhotoshopConnector()
    try:
        ps.connect()
        print(f"Connected to Photoshop {ps.app.Version}")

        # ---- Build font index once ----
        print("\nBuilding font index...")
        font_index = build_font_index(ps.app)
        print(f"  {len(font_index)} families loaded")

        # ---- Step 1: test.psd → mirror + Byte Sans → test_mirror.psd ----
        print(f"\n{'='*40}")
        print("STEP 1: test.psd → mirror text + Noto→Byte Sans")
        print(f"{'='*40}")

        doc1, records1, dpi1, work1 = scan_psd(ps, str(SRC_PSD), str(BASE_DIR / "round2_step1.log"))
        print(f"  Scanned: {len(records1)} layers")

        # Reopen log for apply
        apply_changes(ps, doc1, records1, font_index, "Byte Sans",
                      str(BASE_DIR / "round2_step1.log"))
        ps.close_document(doc1, save=False)

        # Rename work file to mirror output
        if os.path.exists(str(MIRROR_PSD)):
            os.remove(str(MIRROR_PSD))
        os.rename(work1, str(MIRROR_PSD))
        print(f"  Output: {MIRROR_PSD}")

        # ---- Step 2: test_mirror.psd → mirror + Noto Sans → test_mirror_mirror.psd ----
        print(f"\n{'='*40}")
        print("STEP 2: test_mirror.psd → mirror text + Byte→Noto Sans")
        print(f"{'='*40}")

        doc2, records2, dpi2, work2 = scan_psd(ps, str(MIRROR_PSD), str(BASE_DIR / "round2_step2.log"))
        print(f"  Scanned: {len(records2)} layers")

        apply_changes(ps, doc2, records2, font_index, "Noto Sans",
                      str(BASE_DIR / "round2_step2.log"))
        ps.close_document(doc2, save=False)

        if os.path.exists(str(ROUNDTRIP_PSD)):
            os.remove(str(ROUNDTRIP_PSD))
        os.rename(work2, str(ROUNDTRIP_PSD))
        print(f"  Output: {ROUNDTRIP_PSD}")

        # ---- Compare: test.psd vs test_mirror_mirror.psd ----
        print(f"\n{'='*40}")
        print("COMPARE: test.psd vs test_mirror_mirror.psd")
        print(f"{'='*40}")

        report = compare_psds(ps, str(SRC_PSD), str(ROUNDTRIP_PSD),
                              str(BASE_DIR / "round2_comparison.json"))

        s = report["summary"]
        print(f"\n  Total layers: {s['total_layers']}")
        print(f"  Matched: {s['matched_layers']}")
        print(f"  Avg |Δsize|: {s['avg_size_drift_pct']}%")
        print(f"  Avg |Δheight|: {s['avg_h_drift_px']}px")
        print(f"  Avg |Δtracking|: {s['avg_tracking_drift']}")
        print(f"  Avg |Δleading|: {s['avg_leading_drift']}")
        print(f"  Font mismatches: {s['font_mismatches']}")
        print(f"  Text mismatches: {s['text_mismatches']}")

        # Top 10 worst layers
        print(f"\n  Top 10 worst layers (by size drift):")
        for c in report["layers"][:10]:
            print(f"    [{c['layer_path']}]")
            print(f"      size: {c['orig_size_pt']:.2f} → {c['rt_size_pt']:.2f}pt ({c['size_drift_pct']:+.1f}%)")
            print(f"      h: {c['orig_bounds_h']:.1f} → {c['rt_bounds_h']:.1f}px ({c['h_drift_px']:+.1f}px)")
            print(f"      tracking: {c['orig_tracking']:.0f} → {c['rt_tracking']:.0f} (Δ{c['tracking_drift']:+.0f})")
            print(f"      font: {c['orig_font']} → {c['rt_font']} restored={c['font_restored']}")
            if not c.get("text_restored", True):
                print(f"      TEXT MISMATCH!")

        print(f"\n  Full report: {BASE_DIR / 'round2_comparison.json'}")

    finally:
        ps.disconnect()
        print("\nDone.")


if __name__ == "__main__":
    main()
