"""
decryptor CLI - 音乐/视频解密模块命令行接口

用法（通过 main.py 调用）:
    python main.py decrypt -i <file_or_dir> [-o <output_dir>]
    python main.py decrypt --version
    python main.py decrypt build   # 构建 um-cli 二进制
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters import UmcliAdapter
from services.decryptor import build_umcli, run_decrypt_job


def main():
    parser = argparse.ArgumentParser(
        description="音乐/视频解密工具（基于 Unlock Music CLI）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持格式:
  QQ音乐:  .qmc* .mflac .mgg .tm*
  网易云:  .ncm .uc
  酷狗:    .kgm .vpr .kgma
  酷我:    .kwm
  虾米:    .xm
  喜马拉雅: .x2m .x3m .bkc*

示例:
  python main.py decrypt -i song.ncm
  python main.py decrypt -i ./music/ -o ./output/
  python main.py decrypt build
        """
    )
    subparsers = parser.add_subparsers(dest="command")

    # 解密命令（默认行为兼容 um-cli 原始参数风格）
    decrypt_p = subparsers.add_parser("run", help="执行解密")
    decrypt_p.add_argument("-i", "--input", required=True, help="输入文件或目录")
    decrypt_p.add_argument("-o", "--output", default=None, help="输出目录")
    decrypt_p.add_argument("--remove-source", action="store_true", help="解密成功后删除源文件")

    # 构建命令
    build_p = subparsers.add_parser("build", help="编译 um-cli 二进制")

    # 状态命令
    subparsers.add_parser("status", help="查看 um-cli 状态")

    args = parser.parse_args()

    wrapper = UmcliAdapter()

    if args.command == "status":
        print(f"um-cli 状态：{'已安装' if wrapper.is_available() else '未安装'}")
        print(f"版本：{wrapper.get_version()}")
        print(f"路径：{wrapper.binary}")
        return

    if args.command == "build":
        print(build_umcli())
        return

    # 解密（统一使用 run 子命令）
    if args.command == "run":
        input_path = args.input
        output_path = args.output
        remove_source = args.remove_source
    else:
        parser.print_help()
        return

    if not wrapper.is_available():
        print(f"[Error] um-cli 未找到: {wrapper.binary}")
        print("请运行: python main.py decrypt build")
        sys.exit(1)

    input_p = Path(input_path)
    if input_p.is_dir():
        print(f"批量解密: {input_path}")
        result = run_decrypt_job("文件夹批量", input_path, output_path, remove_source)
    else:
        print(f"解密: {input_path}")
        result = run_decrypt_job("单个文件", input_path, output_path, remove_source)

    print(result["result_text"])
    if result["summary_rows"][0][1] == "成功":
        print("解密成功")
    else:
        print("[Error] 解密失败")
        sys.exit(1)
