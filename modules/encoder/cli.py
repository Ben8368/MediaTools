"""
encoder CLI - 媒体编码转换模块命令行接口

用法（通过 main.py 调用）:
    python main.py encode transcode <input> <output> [--vcodec libx265] [--crf 23]
    python main.py encode to-h265 <input> [--crf 23]
    python main.py encode to-h264 <input> [--crf 23]
    python main.py encode extract-audio <input>
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.encoder import run_transcode_job


def main():
    parser = argparse.ArgumentParser(description="媒体编码转换工具（基于 FFmpeg）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 通用转码
    transcode_p = subparsers.add_parser("transcode", help="通用转码")
    transcode_p.add_argument("input", help="输入文件")
    transcode_p.add_argument("output", help="输出文件")
    transcode_p.add_argument("--vcodec", default=None, help="视频编码器（如 libx265）")
    transcode_p.add_argument("--acodec", default=None, help="音频编码器（如 aac）")
    transcode_p.add_argument("--crf", type=int, default=None, help="CRF 质量（0-51，越小质量越高）")
    transcode_p.add_argument("--preset", default=None, help="编码预设（ultrafast/fast/medium/slow）")

    # 快捷命令
    h265_p = subparsers.add_parser("to-h265", help="转换为 H.265/HEVC")
    h265_p.add_argument("input", help="输入文件")
    h265_p.add_argument("--output", default=None, help="输出文件（默认自动生成）")
    h265_p.add_argument("--crf", type=int, default=23, help="CRF 质量（默认 23）")

    h264_p = subparsers.add_parser("to-h264", help="转换为 H.264/AVC")
    h264_p.add_argument("input", help="输入文件")
    h264_p.add_argument("--output", default=None, help="输出文件（默认自动生成）")
    h264_p.add_argument("--crf", type=int, default=23, help="CRF 质量（默认 23）")

    audio_p = subparsers.add_parser("extract-audio", help="提取音频")
    audio_p.add_argument("input", help="输入文件")
    audio_p.add_argument("--output", default=None, help="输出文件（默认自动生成）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "transcode":
        print(f"转码: {args.input} -> {args.output}")
        result = run_transcode_job(args.input, args.output, "自定义转码", args.crf or 23, args.preset or "medium", args.vcodec or "", args.acodec or "")

    elif args.command == "to-h265":
        print(f"转换为 H.265: {args.input}")
        result = run_transcode_job(args.input, args.output, "H.265 (HEVC)", args.crf, "medium", "", "")

    elif args.command == "to-h264":
        print(f"转换为 H.264: {args.input}")
        result = run_transcode_job(args.input, args.output, "H.264 (AVC)", args.crf, "medium", "", "")

    elif args.command == "extract-audio":
        print(f"提取音频: {args.input}")
        result = run_transcode_job(args.input, args.output, "提取音频", 23, "medium", "", "")
    else:
        parser.print_help()
        return

    if result["output_path"]:
        print(f"成功: {result['output_path']}")
    else:
        print(f"[Error] 失败: {result['log']}")
        sys.exit(1)
