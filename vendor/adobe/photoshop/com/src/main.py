"""
PSD 文字修改工具 - CLI 入口
支持单文件和批量处理
"""

import argparse
import csv
import os
import sys
import shutil
import time
from pathlib import Path
from collections import defaultdict

# 修复 Windows 终端 Unicode 输出问题
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config_reader import read_mappings
from ps_connector import PhotoshopConnector
from text_modifier import process_document, AdjustParams
from ticket_workflow import (
    scan_document_for_ticket,
    write_scan_layers_csv,
    write_scan_summary_csv,
    build_ticket_rows,
    write_ticket_csv,
    read_ticket_csv,
    execute_ticket,
)


def safe_close_document(ps: PhotoshopConnector, doc) -> None:
    """尽量关闭文档，不让异常阻断清理流程。"""
    if doc is None:
        return
    try:
        ps.close_document(doc, save=False)
    except Exception:
        pass


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PSD 文字修改工具 - 快速修改 Photoshop 文件中的文字内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 传统模式：用 CSV 映射表处理
  python main.py --psd input.psd --csv mapping.csv --output ./output

  # 新模式：扫描工程文字内容
  python main.py --psd input.psd --scan --output ./scan_output

  # 新模式：验证字体转换效果（生成缓存）
  python main.py --psd input.psd --verify-font --font-from ByteSans --font-to NotoSans --output ./scan_output

  # 新模式：用扫描 CSV + 缓存批量应用
  python main.py --psd input.psd --scan-csv scan_output/input_text_content.csv --use-cache scan_output/font_conversion_cache.csv --output . --output-name output.psd

  # 导出标准 CSV 映射表
  python main.py --export-mapping --scan-csv scan_output/input_text_content.csv --use-cache scan_output/font_conversion_cache.csv --output my_mapping.csv
        """,
    )

    # 输入文件
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--psd", type=str, help="单个 PSD 文件路径")
    input_group.add_argument("--psd-dir", type=str, help="包含多个 PSD 文件的文件夹路径（批量处理）")

    # 映射表（传统模式）
    parser.add_argument("--csv", type=str, help="CSV/Excel 映射表路径")

    # 新模式：扫描
    parser.add_argument("--scan", action="store_true", help="扫描 PSD 文字内容和字体组合，输出 CSV")
    parser.add_argument("--scan-ticket", type=str, help="扫描 PSD 并生成唯一主工单 CSV（如 _local/tickets/主工单.csv）")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描 PSD 文字层，输出扫描明细和文案汇总")
    parser.add_argument("--build-ticket", action="store_true", help="扫描 PSD 并生成工单模板 CSV")
    parser.add_argument("--ticket", type=str, help="工单 CSV 路径，严格按工单执行")
    parser.add_argument("--execute-ticket", type=str, help="执行唯一主工单 CSV")
    parser.add_argument("--ticket-languages", type=str, help="生成工单时预展开的语言列表，逗号分隔")
    parser.add_argument("--ticket-outputs", type=str, help="生成工单时预展开的输出文件名列表，逗号分隔")

    # 新模式：验证字体转换
    parser.add_argument("--verify-font", action="store_true", help="临时工程验证字体转换效果，生成缓存 CSV")
    parser.add_argument("--font-from", type=str, help="原字体家族名（如 ByteSans）")
    parser.add_argument("--font-to", type=str, help="目标字体规格（家族名或完整 PostScript 名，如 NotoSans 或 NotoSans-Bold）")
    parser.add_argument("--force-verify", action="store_true", help="强制重新验证，忽略已有缓存")

    # 新模式：用扫描 CSV + 缓存批量应用
    parser.add_argument("--scan-csv", type=str, help="扫描生成的文字内容 CSV（用户填写后）")
    parser.add_argument("--use-cache", type=str, help="字体转换缓存 CSV 路径")

    # 导出标准 CSV 映射表
    parser.add_argument("--export-mapping", action="store_true", help="把扫描 CSV + 缓存导出为标准 CSV 映射表")

    parser.add_argument("--build-font-metrics", action="store_true", help="扫描工单字体对，在临时文档里测量 metrics，生成缓存 CSV")
    parser.add_argument("--font-metrics", type=str, default=None, help="font_metrics 缓存 CSV 路径（默认自动查找 PSD 同目录的 font_metrics_cache.csv）")

    # 输出目录
    parser.add_argument("--output", type=str, help="输出文件夹路径或文件路径")

    # 输出格式
    parser.add_argument(
        "--format", type=str, default="psd,png",
        help="输出格式，逗号分隔，可选: psd, png, jpg (默认: psd,png)",
    )

    # 自适应调整参数
    parser.add_argument(
        "--tracking-min", type=float, default=-50,
        help="字间距(tracking)最小值，低于此值字会贴合不可读 (默认: -50)",
    )
    parser.add_argument(
        "--tracking-step", type=float, default=5,
        help="字间距每次调整步长 (默认: 5)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.05,
        help="宽高容差比例，允许新文字宽高超出原宽高的比例 (默认: 0.05 即 5%%)",
    )
    parser.add_argument(
        "--font-size-min-ratio", type=float, default=0.5,
        help="最小字号比例，字号不能小于原字号的此比例 (默认: 0.5 即 50%%)",
    )

    # JPG 质量
    parser.add_argument(
        "--jpg-quality", type=int, default=10,
        help="JPG 导出质量 (0-12, 默认: 10)",
    )

    # 多画板导出
    parser.add_argument(
        "--export-artboards", action="store_true", default=False,
        help="多画板模式下，每个画板单独导出为一张图片 (默认: 整个文档导出为一张图)",
    )

    # 输出文件名（单文件模式下有效）
    parser.add_argument(
        "--output-name", type=str, default=None,
        help="输出文件名（不含路径，如 output.psd）。单文件模式有效，默认在原文件名后加 _modified",
    )

    return parser.parse_args()


def collect_psd_files(path: str) -> list[str]:
    """收集 PSD 文件路径"""
    path_obj = Path(path)
    if path_obj.is_file():
        if path_obj.suffix.lower() == ".psd":
            return [str(path_obj.absolute())]
        else:
            raise ValueError(f"文件不是 PSD 格式: {path}")
    elif path_obj.is_dir():
        psd_files = list(path_obj.glob("*.psd")) + list(path_obj.glob("*.PSD"))
        if not psd_files:
            raise ValueError(f"文件夹中没有找到 PSD 文件: {path}")
        return [str(f.absolute()) for f in psd_files]
    else:
        raise ValueError(f"路径不存在: {path}")


def process_single_file(
    ps: PhotoshopConnector,
    psd_path: str,
    mappings: list,
    output_dir: str,
    formats: list[str],
    params: AdjustParams,
    jpg_quality: int,
    export_artboards: bool = False,
    output_name: str = None,
) -> None:
    """处理单个 PSD 文件"""
    print(f"\n{'='*60}")
    print(f"处理文件: {os.path.basename(psd_path)}")
    print(f"{'='*60}")

    # 确定输出文件名
    original_stem = Path(psd_path).stem
    if output_name:
        out_stem = Path(output_name).stem
    else:
        out_stem = f"{original_stem}_modified"

    # 先复制原文件到输出目录，对副本进行操作，原文件不受影响
    os.makedirs(output_dir, exist_ok=True)
    work_psd_path = os.path.join(output_dir, out_stem + ".psd")
    shutil.copy2(psd_path, work_psd_path)
    print(f"  复制原文件 -> {work_psd_path}")

    # 打开副本
    doc = ps.open_document(work_psd_path)

    # 处理文字图层
    results = process_document(ps, doc, mappings, params)

    # 输出结果统计
    success_count = sum(1 for r in results if r.success)
    print(f"\n修改完成: {success_count}/{len(results)} 个图层成功")

    for result in results:
        status = "[OK]" if result.success else "[FAIL]"
        print(f"  {status} {result.layer_name}")
        print(f"      原文字: {result.original_text[:30]}...")
        print(f"      新文字: {result.new_text[:30]}...")
        print(f"      字号: {result.original_font_size:.2f} -> {result.final_font_size:.2f}")
        print(f"      字间距: {result.original_tracking:.0f} -> {result.final_tracking:.0f}")
        if result.original_width > 0:
            w_change = (result.final_width / result.original_width - 1) * 100
            h_change = (result.final_height / result.original_height - 1) * 100
            print(f"      宽度: {result.original_width:.0f}px -> {result.final_width:.0f}px ({w_change:+.1f}%)")
            print(f"      高度: {result.original_height:.0f}px -> {result.final_height:.0f}px ({h_change:+.1f}%)")
        if result.message:
            print(f"      {result.message}")

    output_base = os.path.join(output_dir, out_stem)

    # 保存 PSD（直接保存副本）
    print(f"\n保存文件...")
    if "psd" in formats:
        doc.Save()
        print(f"  [OK] PSD: {work_psd_path}")

    # 导出图片
    artboards = ps.collect_artboards(doc)
    has_artboards = len(artboards) > 0

    if export_artboards and has_artboards:
        print(f"\n  [多画板导出] 共 {len(artboards)} 个画板")
        for ab in artboards:
            ab_name = ab.Name
            safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in ab_name)
            ab_output_base = f"{output_base}_{safe_name}"

            if "png" in formats:
                png_output = f"{ab_output_base}.png"
                ps.export_artboard_png(doc, ab, png_output)
                print(f"  [OK] PNG: {png_output}")

            if "jpg" in formats or "jpeg" in formats:
                jpg_output = f"{ab_output_base}.jpg"
                ps.export_artboard_jpg(doc, ab, jpg_output, quality=jpg_quality)
                print(f"  [OK] JPG: {jpg_output}")
    else:
        if "png" in formats:
            png_output = f"{output_base}.png"
            ps.export_png(doc, png_output)
            print(f"  [OK] PNG: {png_output}")

        if "jpg" in formats or "jpeg" in formats:
            jpg_output = f"{output_base}.jpg"
            ps.export_jpg(doc, jpg_output, quality=jpg_quality)
            print(f"  [OK] JPG: {jpg_output}")

    # 关闭文档
    ps.close_document(doc, save=False)


def main():
    """主函数"""
    args = parse_args()

    # ===== 模式 0: 构建 font_metrics 缓存 =====
    if args.build_font_metrics:
        if not args.psd or not args.ticket:
            print("错误: --build-font-metrics 需要同时指定 --psd 和 --ticket")
            sys.exit(1)

        try:
            ticket_rows = read_ticket_csv(args.ticket)
            print(f"读取工单: {args.ticket} ({len(ticket_rows)} 条)")
        except Exception as e:
            print(f"错误: 读取工单失败: {e}")
            sys.exit(1)

        font_metrics_path = args.font_metrics
        if not font_metrics_path:
            psd_dir = Path(args.psd).parent
            font_metrics_path = str(psd_dir / "font_metrics_cache.csv")

        ps = PhotoshopConnector()
        try:
            ps.connect()
            from font_metrics_cache import build_font_metrics
            metrics = build_font_metrics(ps, ticket_rows, font_metrics_path)
            print(f"\n[OK] font_metrics 缓存已生成: {font_metrics_path} ({len(metrics)} 条)")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            ps.disconnect()
        return

    # ===== 模式 1: 导出标准 CSV 映射表 =====
    if args.export_mapping:
        if not args.scan_csv or not args.use_cache:
            print("错误: --export-mapping 需要同时指定 --scan-csv 和 --use-cache")
            sys.exit(1)
        if not args.output:
            print("错误: --export-mapping 需要指定 --output 输出文件路径")
            sys.exit(1)
        
        from font_analyzer import TextLayerInfo
        from font_verifier import load_cache
        
        # 读取扫描 CSV
        print(f"读取扫描 CSV: {args.scan_csv}")
        scan_data = []
        with open(args.scan_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("new_font") or row.get("new_text", "").strip():
                    scan_data.append(row)
        print(f"  [OK] 加载了 {len(scan_data)} 条有效记录")
        
        # 读取缓存
        print(f"读取缓存: {args.use_cache}")
        cache = load_cache(args.use_cache)
        print(f"  [OK] 加载了 {len(cache)} 条缓存")
        
        # 导出标准 CSV
        print(f"导出标准 CSV: {args.output}")
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["match_mode", "original_text", "new_text", "font", "font_size", "tracking", "artboard"])
            
            for row in scan_data:
                text = row["text_content"]
                new_text = row.get("new_text", "")
                artboard = row.get("artboard", "")
                original_font = row.get("font", "").strip()
                alignment = row.get("alignment", "").strip()
                target_font = cache.get((original_font, alignment), row["new_font"])
                writer.writerow(["exact", text, new_text, target_font, "", "", artboard])
        
        print(f"  [OK] 导出完成")
        return

    # ===== 模式 1A: 扫描并生成唯一主工单 =====
    if args.scan_ticket:
        if not args.psd:
            print("错误: --scan-ticket 需要指定 --psd")
            sys.exit(1)

        ticket_path = args.scan_ticket
        languages = [item.strip() for item in (args.ticket_languages or "").split(",") if item.strip()]
        output_names = [item.strip() for item in (args.ticket_outputs or "").split(",") if item.strip()]

        ps = PhotoshopConnector()
        doc = None
        try:
            ps.connect()
            doc = ps.open_document(args.psd)
            scan_rows = scan_document_for_ticket(ps, doc, args.psd)
            ticket_rows = build_ticket_rows(scan_rows, languages, output_names)
            write_ticket_csv(ticket_rows, ticket_path)

            print("\n主工单已生成:")
            print(f"  {ticket_path}")
            print("\n请直接在该工单中填写 target_text 和 target_font，后续执行只读取这一个工单文件")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            safe_close_document(ps, doc)
            ps.disconnect()

        return

    # ===== 模式 2: 扫描 PSD =====
    if args.scan_only or args.build_ticket:
        if not args.psd:
            print("错误: --scan-only/--build-ticket 需要指定 --psd")
            sys.exit(1)

        stem = Path(args.psd).stem
        psd_dir = Path(args.psd).parent
        languages = [item.strip() for item in (args.ticket_languages or "").split(",") if item.strip()]
        output_names = [item.strip() for item in (args.ticket_outputs or "").split(",") if item.strip()]

        ps = PhotoshopConnector()
        doc = None
        try:
            ps.connect()
            doc = ps.open_document(args.psd)
            scan_rows = scan_document_for_ticket(ps, doc, args.psd)

            if args.build_ticket:
                # 只生成工单，放在 PSD 同目录
                ticket_csv = psd_dir / f"{stem}_ticket.csv"
                ticket_rows = build_ticket_rows(scan_rows, languages, output_names)
                write_ticket_csv(ticket_rows, ticket_csv)
                print(f"\n工单已生成: {ticket_csv}")
                print("请填写工单末尾两列 target_text 和 target_font，再按 --ticket 执行")
            else:
                # scan_only 模式：生成明细和汇总
                if not args.output:
                    args.output = "./_local/scan"
                os.makedirs(args.output, exist_ok=True)
                layers_csv = os.path.join(args.output, f"{stem}_scan_layers.csv")
                summary_csv = os.path.join(args.output, f"{stem}_scan_summary.csv")
                write_scan_layers_csv(scan_rows, layers_csv)
                write_scan_summary_csv(scan_rows, summary_csv)
                print(f"\n扫描完成:")
                print(f"  文字层明细: {layers_csv}")
                print(f"  文案汇总:   {summary_csv}")

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            safe_close_document(ps, doc)
            ps.disconnect()

        return

    # ===== 模式 2A: 按工单执行 =====
    if args.execute_ticket or args.ticket:
        if not args.psd:
            print("错误: --execute-ticket/--ticket 模式需要指定 --psd")
            sys.exit(1)
        if not args.output:
            args.output = "./_local/output"

        ticket_path = args.execute_ticket or args.ticket

        try:
            ticket_rows = read_ticket_csv(ticket_path)
            print(f"读取工单: {ticket_path}")
            print(f"  [OK] 加载了 {len(ticket_rows)} 条工单记录")
        except Exception as e:
            print(f"错误: 读取工单失败: {e}")
            sys.exit(1)

        ps = PhotoshopConnector()
        try:
            ps.connect()
            params = AdjustParams(
                tracking_min=args.tracking_min,
                tracking_step=args.tracking_step,
                font_size_min_ratio=args.font_size_min_ratio,
                tolerance=args.tolerance,
            )
            # 自动推断 font_metrics 缓存路径
            font_metrics_path = args.font_metrics
            if not font_metrics_path:
                psd_dir = Path(args.psd).parent
                font_metrics_path = str(psd_dir / "font_metrics_cache.csv")
            results = execute_ticket(ps, args.psd, ticket_rows, args.output, params, font_metrics_path=font_metrics_path)
            print("\n工单执行完成:")
            for output_name, output_results in results.items():
                success_count = sum(1 for item in output_results if item.success)
                print(f"  {output_name}: {success_count}/{len(output_results)} 成功")
        except Exception as e:
            print(f"错误: 执行工单失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            ps.disconnect()

        return

    # ===== 模式 2: 扫描 PSD =====
    if args.scan:
        if not args.psd:
            print("错误: --scan 需要指定 --psd")
            sys.exit(1)
        if not args.output:
            args.output = "./scan"
        
        from font_analyzer import scan_psd, write_text_content_csv, write_font_profiles_csv
        
        print(f"扫描 PSD: {args.psd}")
        ps = PhotoshopConnector()
        doc = None
        try:
            ps.connect()
            doc = ps.open_document(args.psd)
            
            text_layers, font_profiles = scan_psd(ps, doc)
            
            # 输出两个 CSV
            stem = Path(args.psd).stem
            os.makedirs(args.output, exist_ok=True)
            
            text_csv = os.path.join(args.output, f"{stem}_text_content.csv")
            profile_csv = os.path.join(args.output, f"{stem}_font_profiles.csv")
            
            write_text_content_csv(text_layers, text_csv)
            write_font_profiles_csv(font_profiles, profile_csv)
            
            print(f"\n扫描完成:")
            print(f"  文字内容清单: {text_csv}")
            print(f"  字体组合清单: {profile_csv}")
            print(f"\n请填写 {text_csv} 中的 new_text 和 new_font 列")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            safe_close_document(ps, doc)
            ps.disconnect()
        
        return

    # ===== 模式 3: 验证字体转换 =====
    if args.verify_font:
        if not args.psd:
            print("错误: --verify-font 需要指定 --psd")
            sys.exit(1)
        if not args.font_from or not args.font_to:
            print("错误: --verify-font 需要指定 --font-from 和 --font-to")
            sys.exit(1)
        if not args.output:
            args.output = "./scan"
        
        from font_analyzer import scan_psd
        from font_verifier import verify_font_mapping, load_cache, write_cache
        
        print(f"验证字体转换: {args.font_from} -> {args.font_to}")
        
        cache_path = os.path.join(args.output, "font_conversion_cache.csv")
        existing_mappings = {}
        if os.path.exists(cache_path) and not args.force_verify:
            print(f"加载已有缓存: {cache_path}")
            existing_mappings = load_cache(cache_path)
            print(f"  [OK] 加载了 {len(existing_mappings)} 条映射")
        
        ps = PhotoshopConnector()
        doc = None
        try:
            ps.connect()
            doc = ps.open_document(args.psd)
            
            print("扫描字体组合...")
            _, font_profiles = scan_psd(ps, doc)
            
            print(f"\n开始验证...")
            mappings = verify_font_mapping(
                ps, font_profiles, args.font_from, args.font_to, existing_mappings
            )
            
            os.makedirs(args.output, exist_ok=True)
            write_cache(mappings, cache_path)
            
            print(f"\n验证完成: {cache_path}")
            print(f"  共 {len(mappings)} 条字体映射")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            safe_close_document(ps, doc)
            ps.disconnect()
        
        return

    # ===== 模式 4: 用扫描 CSV + 缓存批量应用 =====
    if args.scan_csv and args.use_cache:
        if not args.psd:
            print("错误: 批量应用需要指定 --psd")
            sys.exit(1)
        if not args.output:
            args.output = "./output"
        
        from font_verifier import load_cache
        from text_modifier import apply_from_cache
        from font_analyzer import _get_font_family, _get_alignment
        
        # 读取扫描 CSV（每行对应一个图层）
        print(f"读取扫描 CSV: {args.scan_csv}")
        scan_data = defaultdict(list)
        with open(args.scan_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("new_font") or row.get("new_text", "").strip():
                    key = (
                        row["artboard"].strip(),
                        row["layer_name"].strip(),
                        row["text_content"].strip(),
                        row["font_family"].strip(),
                    )
                    scan_data[key].append({
                        "new_text": row.get("new_text", "").strip() or None,
                        "new_font": row["new_font"].strip(),
                    })
        print(f"  [OK] 加载了 {len(scan_data)} 条修改规则")
        
        # 读取缓存: (original_font, alignment) → target_font
        print(f"读取缓存: {args.use_cache}")
        cache = load_cache(args.use_cache)
        print(f"  [OK] 加载了 {len(cache)} 条字体映射")
        
        # 处理 PSD
        print(f"\n处理 PSD: {args.psd}")
        
        original_stem = Path(args.psd).stem
        if args.output_name:
            out_stem = Path(args.output_name).stem
        else:
            out_stem = f"{original_stem}_modified"
        
        os.makedirs(args.output, exist_ok=True)
        work_psd_path = os.path.join(args.output, out_stem + ".psd")
        shutil.copy2(args.psd, work_psd_path)
        print(f"  复制原文件 -> {work_psd_path}")
        
        ps = PhotoshopConnector()
        doc = None
        try:
            ps.connect()
            doc = ps.open_document(work_psd_path)
            time.sleep(0.5)
            
            def collect_layers(container, artboard_name, results):
                try:
                    for ls in container.LayerSets:
                        collect_layers(ls, artboard_name, results)
                except Exception:
                    pass
                try:
                    for layer in container.ArtLayers:
                        if layer.Kind != 2:
                            continue
                        try:
                            ti = layer.TextItem
                            raw_text = ti.Contents
                            text = raw_text.strip().replace("\r", " ").replace("\n", " ")
                            if not text:
                                continue
                            font = ti.Font
                            alignment = _get_alignment(ti)
                            
                            results.append({
                                "layer_obj": layer,
                                "artboard": artboard_name,
                                "layer_name": layer.Name,
                                "text": text,
                                "font": font,
                                "font_family": _get_font_family(font),
                                "alignment": alignment,
                            })
                        except Exception:
                            pass
                except Exception:
                    pass
            
            layers_data = []
            artboards = ps.collect_artboards(doc)
            time.sleep(0.3)
            
            if artboards:
                artboard_ids = set()
                for ab in artboards:
                    try:
                        artboard_ids.add(ab.id)
                    except Exception:
                        pass
                    collect_layers(ab, ab.Name, layers_data)
                outside_layers = ps.collect_text_layers_outside_artboards(doc, artboard_ids)
                for layer in outside_layers:
                    collect_layers(type("_Container", (), {"LayerSets": [], "ArtLayers": [layer]})(), "(画板外)", layers_data)
            else:
                collect_layers(doc, "(无画板)", layers_data)
            
            print(f"  找到 {len(layers_data)} 个文字图层")
            
            # 批量应用
            results = []
            for layer_info in layers_data:
                scan_key = (
                    layer_info["artboard"],
                    layer_info["layer_name"],
                    layer_info["text"],
                    layer_info["font_family"],
                )
                
                if scan_key not in scan_data:
                    continue
                
                rule = scan_data[scan_key].pop(0)
                if not scan_data[scan_key]:
                    del scan_data[scan_key]
                
                # 用 (原字体, 对齐方式) 查缓存获取目标字体
                cache_key = (layer_info["font"], layer_info["alignment"])
                if rule["new_font"] and cache_key in cache:
                    target_font = cache[cache_key]
                else:
                    # 只改文案时允许跳过字体替换
                    if not rule["new_font"]:
                        target_font = layer_info["font"]
                    else:
                        target_font = rule["new_font"]
                
                layer_obj = layer_info["layer_obj"]
                print(f"  [应用] [{layer_info['artboard']}] {layer_info['layer_name']}")
                result = apply_from_cache(ps, layer_obj, rule["new_text"], target_font)
                results.append(result)
            
            doc.Save()
            print(f"  [OK] PSD: {work_psd_path}")
            
            print(f"\n完成! 修改了 {len(results)} 个图层")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            safe_close_document(ps, doc)
            ps.disconnect()
        
        return

    # ===== 模式 5: 传统 CSV 映射表模式 =====
    if args.csv:
        if not args.output:
            print("错误: --csv 模式需要指定 --output 输出目录")
            sys.exit(1)

        # 解析输出格式
        formats = [f.strip().lower() for f in args.format.split(",")]
        valid_formats = {"psd", "png", "jpg", "jpeg"}
        invalid = set(formats) - valid_formats
        if invalid:
            print(f"错误: 不支持的输出格式: {invalid}")
            sys.exit(1)

        # 读取映射表
        print(f"读取映射表: {args.csv}")
        try:
            mappings = read_mappings(args.csv)
            print(f"  [OK] 加载了 {len(mappings)} 条映射规则")
        except Exception as e:
            print(f"错误: 读取映射表失败: {e}")
            sys.exit(1)

        # 收集 PSD 文件
        try:
            if args.psd:
                psd_files = collect_psd_files(args.psd)
            else:
                psd_files = collect_psd_files(args.psd_dir)
            print(f"  [OK] 找到 {len(psd_files)} 个 PSD 文件")
        except Exception as e:
            print(f"错误: {e}")
            sys.exit(1)

        # 创建输出目录
        os.makedirs(args.output, exist_ok=True)

        # 连接 Photoshop
        print(f"\n连接 Photoshop...")
        ps = PhotoshopConnector()
        try:
            ps.connect()
            print(f"  [OK] 已连接")
        except Exception as e:
            print(f"错误: {e}")
            sys.exit(1)

        # 构建调整参数
        params = AdjustParams(
            tracking_min=args.tracking_min,
            tracking_step=args.tracking_step,
            font_size_min_ratio=args.font_size_min_ratio,
            tolerance=args.tolerance,
        )

        # 处理所有文件
        try:
            for i, psd_path in enumerate(psd_files, 1):
                print(f"\n[{i}/{len(psd_files)}]")
                try:
                    process_single_file(
                        ps, psd_path, mappings, args.output, formats, params,
                        args.jpg_quality, args.export_artboards, args.output_name
                    )
                except Exception as e:
                    print(f"错误: 处理文件失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"\n{'='*60}")
            print(f"全部完成! 输出目录: {args.output}")
            print(f"{'='*60}")

        finally:
            ps.disconnect()
        
        return

    # 没有指定任何模式
    print("错误: 请指定操作模式")
    print("  --scan-ticket: 扫描并生成唯一主工单")
    print("  --execute-ticket: 执行唯一主工单")
    print("  --scan-only: 仅扫描并输出文字层明细/汇总")
    print("  --build-ticket: 扫描并生成工单模板")
    print("  --ticket: 按工单执行")
    print("  --scan: 扫描 PSD")
    print("  --verify-font: 验证字体转换")
    print("  --scan-csv + --use-cache: 批量应用")
    print("  --csv: 传统 CSV 映射表模式")
    print("  --export-mapping: 导出标准 CSV")
    sys.exit(1)


if __name__ == "__main__":
    main()
