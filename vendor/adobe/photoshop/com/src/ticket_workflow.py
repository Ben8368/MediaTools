import csv
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from config_reader import TextMapping
from font_analyzer import _get_alignment, _get_font_family, _get_tracking
from text_modifier import AdjustParams, ModifyResult, modify_text_layer


def _normalize_display_text(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ").strip()


def _split_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\r").replace("\n", "\r")
    return [part for part in normalized.split("\r") if part != ""]


def _guess_font_weight(font_name: str) -> str:
    if "-" not in font_name:
        return "Regular"
    return font_name.split("-", 1)[1]


@dataclass
class TicketScanRow:
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


@dataclass
class TicketRow:
    layer_id: int
    output_name: str
    language: str
    artboard_name: str
    layer_name: str
    line_count: int
    alignment: str
    font_size: float
    tracking: float
    width_px: float
    height_px: float
    status: str
    notes: str
    source_psd: str
    source_font: str
    original_text: str
    target_text: str
    target_font: str
    layer_kind: str = "text"
    smart_object_layer_id: int = 0
    smart_object_name: str = ""
    smart_object_inner_layer_name: str = ""


TICKET_FIELDNAMES = [
    "layer_id",
    "artboard_name",
    "layer_name",
    "layer_kind",
    "smart_object_layer_id",
    "smart_object_name",
    "smart_object_inner_layer_name",
    "output_name",
    "language",
    "line_count",
    "alignment",
    "font_size",
    "tracking",
    "width_px",
    "height_px",
    "status",
    "notes",
    "source_psd",
    "source_font",
    "original_text",
    "target_text",
    "target_font",
]

TICKET_REQUIRED_FIELDNAMES = [
    field
    for field in TICKET_FIELDNAMES
    if field not in {"layer_kind", "smart_object_layer_id", "smart_object_name", "smart_object_inner_layer_name"}
]


SCAN_FIELDNAMES = [
    "layer_id",
    "source_psd",
    "artboard",
    "layer_name",
    "line_count",
    "alignment",
    "font_size",
    "tracking",
    "width_px",
    "height_px",
    "source_font",
    "source_font_family",
    "source_font_weight",
    "smart_object_layer_id",
    "smart_object_name",
    "smart_object_inner_layer_name",
    "original_text",
]


SUMMARY_FIELDNAMES = [
    "original_text",
    "occurrence_count",
    "line_count_set",
    "artboards",
    "layer_names",
    "fonts",
]


def scan_document_for_ticket(ps, doc, source_psd: str, progress_callback=None) -> list[TicketScanRow]:
    rows: list[TicketScanRow] = []
    layer_id = 1
    normal_text_layer_count = 0
    smart_text_layer_count = 0
    smart_object_count = 0
    skipped_smart_object_count = 0

    def emit_progress(stage: str, smart_object_name: str = ""):
        if progress_callback is None:
            return
        try:
            progress_callback(
                {
                    "stage": stage,
                    "layer_count": len(rows),
                    "normal_text_layer_count": normal_text_layer_count,
                    "smart_text_layer_count": smart_text_layer_count,
                    "smart_object_count": smart_object_count,
                    "skipped_smart_object_count": skipped_smart_object_count,
                    "smart_object_name": smart_object_name,
                }
            )
        except Exception:
            pass

    def append_row(layer, artboard_name: str, smart_layer=None, inner_layer_name: str = ""):
        nonlocal layer_id, normal_text_layer_count, smart_text_layer_count
        try:
            ti = layer.TextItem
            raw_text = ti.Contents
            if not raw_text or not raw_text.strip():
                return
            bounds = ps.get_layer_bounds(layer)
            width_px = round(bounds[2] - bounds[0], 2)
            height_px = round(bounds[3] - bounds[1], 2)
            font = ti.Font
            line_count = len(_split_lines(raw_text)) or 1
            rows.append(
                TicketScanRow(
                    layer_id=layer_id,
                    source_psd=os.path.basename(source_psd),
                    artboard=artboard_name,
                    layer_name=f"{smart_layer.Name} / {layer.Name}" if smart_layer is not None else layer.Name,
                    line_count=line_count,
                    alignment=_get_alignment(ti),
                    font_size=round(float(ti.Size), 2),
                    tracking=round(float(_get_tracking(ti)), 2),
                    width_px=width_px,
                    height_px=height_px,
                    source_font=font,
                    source_font_family=_get_font_family(font),
                    source_font_weight=_guess_font_weight(font),
                    raw_text=raw_text.strip(),
                    original_text=_normalize_display_text(raw_text.strip()),
                    layer_obj=None if smart_layer is not None else layer,
                    smart_object_layer_id=ps.get_layer_id(smart_layer) if smart_layer is not None else 0,
                    smart_object_name=smart_layer.Name if smart_layer is not None else "",
                    smart_object_inner_layer_name=inner_layer_name or (layer.Name if smart_layer is not None else ""),
                )
            )
            layer_id += 1
            if smart_layer is not None:
                smart_text_layer_count += 1
                emit_progress(f"已发现 {len(rows)} 个文字层，正在扫描智能对象：{smart_layer.Name}", smart_layer.Name)
            else:
                normal_text_layer_count += 1
                emit_progress(f"已发现 {len(rows)} 个文字层，正在扫描普通文字层")
        except Exception:
            return

    def append_smart_object_rows(container, artboard_name: str):
        nonlocal smart_object_count, skipped_smart_object_count
        for smart_layer in ps.collect_smart_object_layers(container):
            smart_doc = None
            try:
                smart_object_count += 1
                emit_progress(f"正在打开智能对象：{smart_layer.Name}", smart_layer.Name)
                smart_doc = ps.open_smart_object_contents(smart_layer)
                for inner_layer in ps.collect_text_layers(smart_doc):
                    append_row(inner_layer, artboard_name, smart_layer=smart_layer, inner_layer_name=inner_layer.Name)
            except Exception:
                skipped_smart_object_count += 1
                emit_progress(f"智能对象无法扫描，已跳过：{smart_layer.Name}", smart_layer.Name)
                continue
            finally:
                if smart_doc is not None:
                    try:
                        ps.close_document(smart_doc, save=False)
                    except Exception:
                        pass
                    try:
                        doc.Activate()
                    except Exception:
                        pass

    artboards = ps.collect_artboards(doc)
    if artboards:
        artboard_ids = set()
        for ab in artboards:
            try:
                artboard_ids.add(ab.id)
            except Exception:
                pass
            for layer in ps.collect_text_layers_in_artboard(ab):
                append_row(layer, ab.Name)
            append_smart_object_rows(ab, ab.Name)

        for layer in ps.collect_text_layers_outside_artboards(doc, artboard_ids):
            append_row(layer, "(画板外)")
        for smart_layer in ps.collect_smart_object_layers_outside_artboards(doc, artboard_ids):
            smart_doc = None
            try:
                smart_object_count += 1
                emit_progress(f"正在打开智能对象：{smart_layer.Name}", smart_layer.Name)
                smart_doc = ps.open_smart_object_contents(smart_layer)
                for inner_layer in ps.collect_text_layers(smart_doc):
                    append_row(inner_layer, "(画板外)", smart_layer=smart_layer, inner_layer_name=inner_layer.Name)
            except Exception:
                skipped_smart_object_count += 1
                emit_progress(f"智能对象无法扫描，已跳过：{smart_layer.Name}", smart_layer.Name)
                continue
            finally:
                if smart_doc is not None:
                    try:
                        ps.close_document(smart_doc, save=False)
                    except Exception:
                        pass
                    try:
                        doc.Activate()
                    except Exception:
                        pass
    else:
        for layer in ps.collect_text_layers(doc):
            append_row(layer, "(无画板)")
        append_smart_object_rows(doc, "(无画板)")

    return rows


def modify_smart_object_text_layer(
    ps, parent_doc, row: TicketScanRow, mapping: TextMapping, params: AdjustParams
) -> ModifyResult:
    """Open a smart object, modify its matching inner text layer, then save it back to the parent PSD."""
    try:
        parent_doc.Activate()
    except Exception:
        pass

    raw_text = getattr(row, "raw_text", None) or getattr(row, "original_text", "")
    smart_layer = ps.find_layer_by_id(parent_doc, row.smart_object_layer_id)
    if smart_layer is None:
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
            message="Smart object layer not found",
        )

    smart_doc = None
    try:
        smart_doc = ps.open_smart_object_contents(smart_layer)
        candidates = ps.collect_text_layers(smart_doc)
        target_layer = None
        for layer in candidates:
            try:
                if (
                    layer.Name == row.smart_object_inner_layer_name
                    and _normalize_display_text(layer.TextItem.Contents.strip()) == row.original_text
                ):
                    target_layer = layer
                    break
            except Exception:
                continue
        if target_layer is None:
            for layer in candidates:
                try:
                    if _normalize_display_text(layer.TextItem.Contents.strip()) == row.original_text:
                        target_layer = layer
                        break
                except Exception:
                    continue
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
                message="Text layer inside smart object not found",
            )
        result = modify_text_layer(ps, target_layer, mapping, params)
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


def write_scan_layers_csv(rows: list[TicketScanRow], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAN_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "layer_id": row.layer_id,
                    "source_psd": row.source_psd,
                    "artboard": row.artboard,
                    "layer_name": row.layer_name,
                    "line_count": row.line_count,
                    "alignment": row.alignment,
                    "font_size": row.font_size,
                    "tracking": row.tracking,
                    "width_px": row.width_px,
                    "height_px": row.height_px,
                    "source_font": row.source_font,
                    "source_font_family": row.source_font_family,
                    "source_font_weight": row.source_font_weight,
                    "smart_object_layer_id": row.smart_object_layer_id,
                    "smart_object_name": row.smart_object_name,
                    "smart_object_inner_layer_name": row.smart_object_inner_layer_name,
                    "original_text": row.original_text,
                }
            )


def write_scan_summary_csv(rows: list[TicketScanRow], output_path: str) -> None:
    summary: dict[str, dict] = {}
    for row in rows:
        key = row.original_text
        if key not in summary:
            summary[key] = {
                "occurrence_count": 0,
                "line_count_set": set(),
                "artboards": set(),
                "layer_names": set(),
                "fonts": set(),
            }
        item = summary[key]
        item["occurrence_count"] += 1
        item["line_count_set"].add(str(row.line_count))
        item["artboards"].add(row.artboard)
        item["layer_names"].add(row.layer_name)
        item["fonts"].add(row.source_font)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        for text, item in sorted(summary.items(), key=lambda kv: (-kv[1]["occurrence_count"], kv[0])):
            writer.writerow(
                {
                    "original_text": text,
                    "occurrence_count": item["occurrence_count"],
                    "line_count_set": "|".join(sorted(item["line_count_set"])),
                    "artboards": " | ".join(sorted(item["artboards"])),
                    "layer_names": " | ".join(sorted(item["layer_names"])),
                    "fonts": " | ".join(sorted(item["fonts"])),
                }
            )


def _expand_ticket_targets(languages: list[str], output_names: list[str]) -> list[tuple[str, str]]:
    if not languages and not output_names:
        return [("", "")]
    if languages and output_names and len(languages) != len(output_names):
        raise ValueError("--ticket-languages 和 --ticket-outputs 数量必须一致")
    if output_names and not languages:
        return [("", name) for name in output_names]
    if languages and not output_names:
        return [(lang, f"{lang}.psd") for lang in languages]
    return list(zip(languages, output_names, strict=False))


def build_ticket_rows(scan_rows: list[TicketScanRow], languages: list[str], output_names: list[str]) -> list[dict]:
    expanded_targets = _expand_ticket_targets(languages, output_names)
    rows: list[dict] = []
    sorted_scan_rows = sorted(scan_rows, key=lambda row: (row.artboard, row.layer_name, row.layer_id))
    for scan_row in sorted_scan_rows:
        for language, output_name in expanded_targets:
            rows.append(
                {
                    "layer_id": scan_row.layer_id,
                    "artboard_name": scan_row.artboard,
                    "layer_name": scan_row.layer_name,
                    "layer_kind": "smart_object_text" if scan_row.smart_object_layer_id else "text",
                    "smart_object_layer_id": scan_row.smart_object_layer_id,
                    "smart_object_name": scan_row.smart_object_name,
                    "smart_object_inner_layer_name": scan_row.smart_object_inner_layer_name,
                    "output_name": output_name,
                    "language": language,
                    "line_count": scan_row.line_count,
                    "alignment": scan_row.alignment,
                    "font_size": scan_row.font_size,
                    "tracking": scan_row.tracking,
                    "width_px": scan_row.width_px,
                    "height_px": scan_row.height_px,
                    "status": "pending",
                    "notes": "",
                    "source_psd": scan_row.source_psd,
                    "source_font": scan_row.source_font,
                    "original_text": scan_row.original_text,
                    "target_text": "",
                    "target_font": "",
                }
            )
    return sorted(rows, key=lambda row: (row["artboard_name"], row["layer_name"], row["output_name"], row["layer_id"]))


def write_ticket_csv(rows: list[dict], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=TICKET_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def read_ticket_csv(filepath: str) -> list[TicketRow]:
    rows: list[TicketRow] = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = set(TICKET_REQUIRED_FIELDNAMES) - headers
        if missing:
            raise ValueError(f"工单缺少必需列: {sorted(missing)}")
        for idx, row in enumerate(reader, start=2):
            try:
                smart_object_layer_id = int(str(row.get("smart_object_layer_id", "")).strip() or 0)
                layer_kind = row.get("layer_kind", "").strip() or (
                    "smart_object_text" if smart_object_layer_id else "text"
                )
                rows.append(
                    TicketRow(
                        layer_id=int(str(row["layer_id"]).strip()),
                        output_name=row["output_name"].strip(),
                        language=row["language"].strip(),
                        artboard_name=row["artboard_name"].strip(),
                        layer_name=row["layer_name"].strip(),
                        line_count=int(str(row["line_count"]).strip() or 1),
                        alignment=row["alignment"].strip(),
                        font_size=float(str(row["font_size"]).strip() or 0),
                        tracking=float(str(row["tracking"]).strip() or 0),
                        width_px=float(str(row["width_px"]).strip() or 0),
                        height_px=float(str(row["height_px"]).strip() or 0),
                        status=row["status"].strip().lower(),
                        notes=row["notes"].strip(),
                        source_psd=row["source_psd"].strip(),
                        source_font=row["source_font"].strip(),
                        original_text=row["original_text"].strip(),
                        target_text=row["target_text"],
                        target_font=row["target_font"].strip(),
                        layer_kind=layer_kind,
                        smart_object_layer_id=smart_object_layer_id,
                        smart_object_name=row.get("smart_object_name", "").strip(),
                        smart_object_inner_layer_name=row.get("smart_object_inner_layer_name", "").strip(),
                    )
                )
            except Exception as e:
                raise ValueError(f"工单第 {idx} 行解析错误: {e}") from e
    return rows


def _should_apply_ticket_row(row: TicketRow) -> bool:
    if row.status == "skip":
        return False
    if row.status in {"confirmed", "ready", "approved"}:
        return True
    return bool((row.target_text or "").strip() or row.target_font)


def _group_ticket_rows(rows: list[TicketRow]) -> dict[str, list[TicketRow]]:
    grouped: dict[str, list[TicketRow]] = {}
    for row in rows:
        if not row.output_name:
            continue
        grouped.setdefault(row.output_name, []).append(row)
    return grouped


def _is_smart_ticket_row(row: TicketRow) -> bool:
    return row.layer_kind == "smart_object_text" or row.smart_object_layer_id > 0


def _find_scan_row_for_ticket_row(scanned: list[TicketScanRow], ticket_row: TicketRow) -> TicketScanRow | None:
    is_smart_row = _is_smart_ticket_row(ticket_row)
    for row in scanned:
        if row.layer_id == ticket_row.layer_id and bool(row.smart_object_layer_id) == is_smart_row:
            return row

    if not is_smart_row:
        return None

    for row in scanned:
        if row.smart_object_layer_id <= 0:
            continue
        if ticket_row.smart_object_layer_id and row.smart_object_layer_id != ticket_row.smart_object_layer_id:
            continue
        if ticket_row.smart_object_name and row.smart_object_name != ticket_row.smart_object_name:
            continue
        if (
            ticket_row.smart_object_inner_layer_name
            and row.smart_object_inner_layer_name != ticket_row.smart_object_inner_layer_name
        ):
            continue
        if ticket_row.original_text and row.original_text != ticket_row.original_text:
            continue
        return row

    for row in scanned:
        if row.smart_object_layer_id > 0 and row.layer_name == ticket_row.layer_name:
            return row
    return None


def execute_ticket(
    ps,
    psd_path: str,
    ticket_rows: list[TicketRow],
    output_dir: str,
    params: AdjustParams,
    font_metrics_path: str = None,
) -> dict[str, list[ModifyResult]]:
    grouped = _group_ticket_rows(ticket_rows)
    if not grouped:
        raise ValueError("工单中没有有效的 output_name")

    # 加载 font_metrics 缓存（空白工程验证法）
    font_metrics = {}
    if font_metrics_path and os.path.exists(font_metrics_path):
        from font_metrics_cache import load_font_metrics

        font_metrics = load_font_metrics(font_metrics_path)
        print(f"  [font_metrics] 加载缓存: {font_metrics_path} ({len(font_metrics)} 条)")
    else:
        print("  [font_metrics] 未找到缓存，将使用 Bounds 自适应法（fallback）")

    os.makedirs(output_dir, exist_ok=True)
    all_results: dict[str, list[ModifyResult]] = {}

    for output_name, rows in grouped.items():
        out_stem = Path(output_name).stem
        work_psd_path = os.path.join(output_dir, out_stem + ".psd")
        shutil.copy2(psd_path, work_psd_path)
        doc = ps.open_document(work_psd_path)
        try:
            scanned = scan_document_for_ticket(ps, doc, os.path.basename(psd_path))
            results: list[ModifyResult] = []
            for ticket_row in rows:
                if not _should_apply_ticket_row(ticket_row):
                    continue
                target = _find_scan_row_for_ticket_row(scanned, ticket_row)
                if target is None:
                    results.append(
                        ModifyResult(
                            layer_name=ticket_row.layer_name,
                            original_text=ticket_row.original_text,
                            new_text=ticket_row.original_text,
                            original_font_size=ticket_row.font_size,
                            final_font_size=ticket_row.font_size,
                            original_tracking=ticket_row.tracking,
                            final_tracking=ticket_row.tracking,
                            original_width=ticket_row.width_px,
                            final_width=ticket_row.width_px,
                            original_height=ticket_row.height_px,
                            final_height=ticket_row.height_px,
                            success=False,
                            message=(
                                "SMART_OBJECT_TEXT_NOT_FOUND"
                                if _is_smart_ticket_row(ticket_row)
                                else "未找到 layer_id 对应的文字图层"
                            ),
                        )
                    )
                    continue
                if target.artboard != ticket_row.artboard_name or target.layer_name != ticket_row.layer_name:
                    results.append(
                        ModifyResult(
                            layer_name=ticket_row.layer_name,
                            original_text=ticket_row.original_text,
                            new_text=ticket_row.original_text,
                            original_font_size=ticket_row.font_size,
                            final_font_size=ticket_row.font_size,
                            original_tracking=ticket_row.tracking,
                            final_tracking=ticket_row.tracking,
                            original_width=ticket_row.width_px,
                            final_width=ticket_row.width_px,
                            original_height=ticket_row.height_px,
                            final_height=ticket_row.height_px,
                            success=False,
                            message="layer_id 对应图层信息与工单不一致",
                        )
                    )
                    continue

                mapping = TextMapping(
                    match_mode="exact",
                    original_text=target.raw_text,
                    new_text=(ticket_row.target_text or "").strip() or None,
                    font=ticket_row.target_font or None,
                )
                if target.smart_object_layer_id:
                    result = modify_smart_object_text_layer(ps, doc, target, mapping, params)
                elif target.layer_obj is None:
                    result = ModifyResult(
                        layer_name=ticket_row.layer_name,
                        original_text=ticket_row.original_text,
                        new_text=ticket_row.original_text,
                        original_font_size=ticket_row.font_size,
                        final_font_size=ticket_row.font_size,
                        original_tracking=ticket_row.tracking,
                        final_tracking=ticket_row.tracking,
                        original_width=ticket_row.width_px,
                        final_width=ticket_row.width_px,
                        original_height=ticket_row.height_px,
                        final_height=ticket_row.height_px,
                        success=False,
                        message="TEXT_LAYER_OBJECT_NOT_AVAILABLE",
                    )
                else:
                    result = modify_text_layer(ps, target.layer_obj, mapping, params, font_metrics=font_metrics)
                # 打印关键信息
                if result.message and ("[metrics]" in result.message or "警告" in result.message):
                    print(f"    [{ticket_row.artboard_name}] {ticket_row.layer_name}: {result.message}")
                results.append(result)

            doc.Save()
            all_results[output_name] = results
        finally:
            ps.close_document(doc, save=False)

    return all_results
