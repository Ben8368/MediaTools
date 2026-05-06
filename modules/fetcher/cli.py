"""
fetcher CLI - 媒体获取模块命令行接口

用法（通过 main.py 调用）:
    python main.py fetch download <url> [url...] [--video] [--video-codec h264] [--subtitles original_only]
    python main.py fetch info <url>
    python main.py fetch analyze <srt_path>
    python main.py fetch export
    python main.py fetch ytdlp status|update|download
    python main.py fetch ffmpeg --info
"""
import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters import FFmpegAdapter, YtdlpAdapter
from backend.config import DEFAULT_NAMING_TEMPLATE
from modules.fetcher.analyzer import SubtitleAnalyzer
from modules.fetcher.csv_manager import CSVManager
from modules.fetcher.subtitle import SubtitleProcessor
from backend.services.fetcher import fetch_video_info, run_fetch_batch
from backend.services.workspace import get_current_workspace


def main():
    workspace = get_current_workspace()
    parser = argparse.ArgumentParser(description="媒体获取工具（支持 YouTube/抖音/TikTok/B站等）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    info_parser = subparsers.add_parser("info", help="获取视频信息")
    info_parser.add_argument("url", help="视频 URL（支持 YouTube/抖音/TikTok/B站等）")

    dl_parser = subparsers.add_parser("download", help="下载视频 + 字幕")
    dl_parser.add_argument("urls", nargs="+", help="视频 URL 列表")
    dl_parser.add_argument("--output-dir", default=workspace["downloads_dir"], help="输出目录")
    dl_parser.add_argument("--naming", default=DEFAULT_NAMING_TEMPLATE, help="命名模板")
    dl_parser.add_argument("--sub-only", action="store_true", help="仅下载字幕")
    dl_parser.add_argument("--analyze", action="store_true", help="下载后自动分析字幕")

    analyze_parser = subparsers.add_parser("analyze", help="分析字幕")
    analyze_parser.add_argument("srt_path", help="SRT 字幕文件路径")
    analyze_parser.add_argument("--model", default=None, help="LLM 模型名称")

    export_parser = subparsers.add_parser("export", help="导出 CSV 统计")
    export_parser.add_argument("--csv-path", default="youtube_videos.csv", help="CSV 文件路径")

    ytdlp_parser = subparsers.add_parser("ytdlp", help="yt-dlp 二进制管理")
    ytdlp_sub = ytdlp_parser.add_subparsers(dest="ytdlp_cmd")
    ytdlp_sub.add_parser("status", help="查看 yt-dlp 状态")
    ytdlp_sub.add_parser("update", help="更新 yt-dlp 到最新版")
    ytdlp_sub.add_parser("download", help="下载 yt-dlp 二进制（首次安装）")

    ffmpeg_parser = subparsers.add_parser("ffmpeg", help="FFmpeg 状态管理")
    ffmpeg_parser.add_argument("--info", action="store_true", help="显示 FFmpeg 信息")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "ffmpeg":
        if args.info:
            info = FFmpegAdapter().get_info()
            if info.get("installed"):
                print("FFmpeg 状态：已安装")
                print(f"版本：{info['version']}")
                print(f"ffmpeg: {info['ffmpeg_path']} ({info['ffmpeg_size_mb']} MB)")
                print(f"ffprobe: {info['ffprobe_path']} ({info['ffprobe_size_mb']} MB)")
            else:
                print(f"FFmpeg 未安装，请将 ffmpeg/ffprobe 放置于: {info['bin_dir']}")
        else:
            ffmpeg_parser.print_help()
        return

    if args.command == "ytdlp":
        ym = YtdlpAdapter()
        if args.ytdlp_cmd == "status":
            status = ym.get_status()
            print(f"yt-dlp 状态：{'已安装' if status['installed'] else '未安装'}")
            print(f"当前版本：{status['version']}")
            print(f"二进制路径：{status['path']}")
        elif args.ytdlp_cmd == "update":
            print("正在更新 yt-dlp...")
            success, msg = ym.update()
            print(msg)
        elif args.ytdlp_cmd == "download":
            print("正在下载 yt-dlp 最新版...")
            success, msg = ym.download_latest()
            print(msg)
        else:
            ytdlp_parser.print_help()
        return

    if args.command == "info":
        info = fetch_video_info(args.url, workspace["downloads_dir"], DEFAULT_NAMING_TEMPLATE)
        print(json.dumps(info, indent=2, ensure_ascii=False, default=str))

    elif args.command == "download":
        result = run_fetch_batch(args.urls, args.output_dir, args.naming, sub_only=args.sub_only, analyze=args.analyze)
        print(result["summary_text"])
        if result["logs_text"]:
            print(result["logs_text"])

    elif args.command == "analyze":
        processor = SubtitleProcessor()
        analyzer = SubtitleAnalyzer()
        highlights, _ = analyzer.analyze_from_srt(args.srt_path, processor, model=args.model)
        print(json.dumps(highlights, indent=2, ensure_ascii=False))

    elif args.command == "export":
        csv_mgr = CSVManager(args.csv_path)
        stats = csv_mgr.get_stats()
        print(f"总计视频：{stats.get('total', 0)}")
        print(f"总时长：{stats.get('total_duration', 0)} 秒")
        print(f"总播放量：{stats.get('total_views', 0)}")
        print(f"含亮点：{stats.get('with_highlights', 0)}")
        print(f"CSV 路径：{args.csv_path}")
