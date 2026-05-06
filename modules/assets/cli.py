"""
assets CLI - 素材管理模块命令行接口

用法（通过 main.py 调用）:
    python main.py assets scan [<directory>]
    python main.py assets list [--type video|audio|image|subtitle]
    python main.py assets search <keyword>
    python main.py assets stats
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.assets.library import AssetLibrary
from services.workspace import get_current_workspace


def main():
    workspace = get_current_workspace()
    default_directory = workspace["project_root"]
    parser = argparse.ArgumentParser(description="素材管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    scan_p = subparsers.add_parser("scan", help="扫描目录建立索引")
    scan_p.add_argument("directory", nargs="?", default=default_directory, help="扫描目录（默认当前工作区）")

    list_p = subparsers.add_parser("list", help="列出素材")
    list_p.add_argument("--type", choices=["video", "audio", "image", "subtitle"], help="按类型过滤")
    list_p.add_argument("--directory", default=default_directory, help="素材目录")

    search_p = subparsers.add_parser("search", help="搜索素材")
    search_p.add_argument("keyword", help="搜索关键词")
    search_p.add_argument("--directory", default=default_directory, help="素材目录")

    stats_p = subparsers.add_parser("stats", help="显示统计信息")
    stats_p.add_argument("--directory", default=default_directory, help="素材目录")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "scan":
        lib = AssetLibrary(args.directory)
        assets = lib.scan()
        print(f"扫描完成，共找到 {len(assets)} 个媒体文件")
        for a in assets[:10]:
            print(f"  [{a['type']:8}] {a['name']} ({a['size_mb']} MB)")
        if len(assets) > 10:
            print(f"  ... 还有 {len(assets) - 10} 个文件")

    elif args.command == "list":
        lib = AssetLibrary(args.directory)
        assets = lib.list_assets(args.type)
        type_label = args.type or "全部"
        print(f"共 {len(assets)} 个 {type_label} 素材:")
        for a in assets:
            print(f"  {a['name']} ({a['size_mb']} MB) - {a['directory']}")

    elif args.command == "search":
        lib = AssetLibrary(args.directory)
        assets = lib.search(args.keyword)
        print(f"搜索 \"{args.keyword}\"，找到 {len(assets)} 个结果:")
        for a in assets:
            print(f"  [{a['type']:8}] {a['name']}")
            print(f"           {a['path']}")

    elif args.command == "stats":
        lib = AssetLibrary(args.directory)
        stats = lib.get_stats()
        print(f"素材库统计（{args.directory}）:")
        print(f"  总计: {stats['total']} 个文件")
        for t, info in stats.get("by_type", {}).items():
            print(f"  {t:10}: {info['count']} 个，共 {info['total_size_mb']} MB")
