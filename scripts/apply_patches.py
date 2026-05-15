#!/usr/bin/env python3
"""
补丁管理工具

用于应用和管理外部工具的补丁文件
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor"

# 需要补丁管理的工具
TOOLS_WITH_PATCHES = ["yt-dlp", "ffmpeg", "um-cli", "capcut-mate"]


def apply_patches(tool: str, dry_run: bool = False) -> bool:
    """应用指定工具的所有补丁"""
    tool_dir = VENDOR_DIR / tool
    patches_dir = tool_dir / "patches"
    source_dir = tool_dir / "source"

    if not patches_dir.exists():
        print(f"[错误] 补丁目录不存在: {patches_dir}")
        return False

    if not source_dir.exists():
        print(f"[警告] 源码目录不存在: {source_dir}")
        if tool == "ffmpeg":
            print("  FFmpeg 通常使用预编译版本，不需要应用补丁")
            return True
        return False

    # 获取所有补丁文件
    patch_files = sorted(patches_dir.glob("*.patch"))

    if not patch_files:
        print(f"[信息] {tool} 没有补丁文件")
        return True

    print(f"找到 {len(patch_files)} 个补丁文件:")
    for patch in patch_files:
        print(f"  - {patch.name}")

    if dry_run:
        print("\n[DRY RUN] 不会实际应用补丁")
        return True

    # 应用每个补丁
    success_count = 0
    for patch in patch_files:
        print(f"\n应用补丁: {patch.name}")
        try:
            result = subprocess.run(
                ["git", "apply", "--check", str(patch)],
                cwd=source_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print("  [失败] 补丁检查失败:")
                print(f"  {result.stderr}")
                continue

            result = subprocess.run(
                ["git", "apply", str(patch)],
                cwd=source_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("  [成功] 补丁已应用")
                success_count += 1
            else:
                print("  [失败] 补丁应用失败:")
                print(f"  {result.stderr}")

        except Exception as e:
            print(f"  [错误] {e}")

    print(f"\n总结: {success_count}/{len(patch_files)} 个补丁应用成功")
    return success_count == len(patch_files)


def create_patch(tool: str, patch_name: str, description: str = "") -> bool:
    """从当前修改创建补丁文件"""
    tool_dir = VENDOR_DIR / tool
    patches_dir = tool_dir / "patches"
    source_dir = tool_dir / "source"

    if not source_dir.exists():
        print(f"[错误] 源码目录不存在: {source_dir}")
        return False

    patches_dir.mkdir(exist_ok=True)

    # 获取下一个补丁编号
    existing_patches = list(patches_dir.glob("*.patch"))
    if existing_patches:
        numbers = []
        for p in existing_patches:
            try:
                num = int(p.name.split("-")[0])
                numbers.append(num)
            except (ValueError, IndexError, AttributeError):
                pass
        next_num = max(numbers) + 1 if numbers else 1
    else:
        next_num = 1

    # 生成补丁文件名
    patch_filename = f"{next_num:03d}-{patch_name}.patch"
    patch_path = patches_dir / patch_filename

    # 创建补丁
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=source_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[错误] 无法生成补丁: {result.stderr}")
            return False

        if not result.stdout.strip():
            print("[警告] 没有检测到修改")
            return False

        # 写入补丁文件
        patch_content = result.stdout
        if description:
            patch_content = f"# {description}\n\n{patch_content}"

        patch_path.write_text(patch_content, encoding="utf-8")
        print(f"[成功] 补丁已创建: {patch_path}")
        print("\n补丁内容预览:")
        print(result.stdout[:500])
        if len(result.stdout) > 500:
            print("...")

        return True

    except Exception as e:
        print(f"[错误] {e}")
        return False


def list_patches(tool: str = None):
    """列出所有补丁"""
    tools = [tool] if tool else TOOLS_WITH_PATCHES

    for t in tools:
        tool_dir = VENDOR_DIR / t
        patches_dir = tool_dir / "patches"

        if not patches_dir.exists():
            continue

        patch_files = sorted(patches_dir.glob("*.patch"))

        if patch_files:
            print(f"\n{t}:")
            for patch in patch_files:
                size = patch.stat().st_size
                print(f"  - {patch.name} ({size} bytes)")
        else:
            print(f"\n{t}: 无补丁")


def reset_source(tool: str) -> bool:
    """重置源码到原始状态（撤销所有补丁）"""
    tool_dir = VENDOR_DIR / tool
    source_dir = tool_dir / "source"

    if not source_dir.exists():
        print(f"[错误] 源码目录不存在: {source_dir}")
        return False

    try:
        # 重置所有修改
        result = subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            cwd=source_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"[成功] {tool} 源码已重置到原始状态")
            return True
        else:
            print(f"[失败] {result.stderr}")
            return False

    except Exception as e:
        print(f"[错误] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="补丁管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # apply 命令
    apply_parser = subparsers.add_parser("apply", help="应用补丁")
    apply_parser.add_argument("tool", choices=TOOLS_WITH_PATCHES, help="工具名称")
    apply_parser.add_argument("--dry-run", action="store_true", help="仅检查，不实际应用")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建补丁")
    create_parser.add_argument("tool", choices=TOOLS_WITH_PATCHES, help="工具名称")
    create_parser.add_argument("name", help="补丁名称（不含编号和.patch后缀）")
    create_parser.add_argument("-d", "--description", help="补丁描述")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出补丁")
    list_parser.add_argument("tool", nargs="?", choices=TOOLS_WITH_PATCHES, help="工具名称（可选）")

    # reset 命令
    reset_parser = subparsers.add_parser("reset", help="重置源码（撤销所有补丁）")
    reset_parser.add_argument("tool", choices=TOOLS_WITH_PATCHES, help="工具名称")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "apply":
        success = apply_patches(args.tool, args.dry_run)
        sys.exit(0 if success else 1)

    elif args.command == "create":
        success = create_patch(args.tool, args.name, args.description)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        list_patches(args.tool)

    elif args.command == "reset":
        success = reset_source(args.tool)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
