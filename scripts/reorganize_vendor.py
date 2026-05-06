#!/usr/bin/env python3
"""
重组 vendor 目录结构

按照 VENDOR_ORGANIZATION.md 规范重组外部工具目录
"""
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor"
BIN_DIR = PROJECT_ROOT / "bin"


def reorganize_um_cli():
    """重组 um-cli 目录结构"""
    print("=" * 60)
    print("重组 um-cli...")
    print("=" * 60)

    old_dir = VENDOR_DIR / "unlock-music"
    new_dir = VENDOR_DIR / "um-cli"

    if not old_dir.exists():
        print("  [SKIP] unlock-music 目录不存在")
        return

    # 创建新目录结构
    (new_dir / "source").mkdir(parents=True, exist_ok=True)
    (new_dir / "bin").mkdir(exist_ok=True)
    (new_dir / "patches").mkdir(exist_ok=True)

    # 移动源码
    if not (new_dir / "source" / "go.mod").exists():
        print(f"  移动源码: {old_dir} -> {new_dir / 'source'}")
        for item in old_dir.iterdir():
            if item.name not in [".git"]:
                dest = new_dir / "source" / item.name
                if not dest.exists():
                    shutil.move(str(item), str(dest))

    # 查找并移动可执行文件
    um_exe = BIN_DIR / "um-cli.exe"
    if um_exe.exists():
        dest = new_dir / "bin" / "um-cli.exe"
        if not dest.exists():
            print(f"  复制可执行文件: {um_exe} -> {dest}")
            shutil.copy2(str(um_exe), str(dest))

    # 删除旧目录（如果为空）
    if old_dir.exists() and not any(old_dir.iterdir()):
        old_dir.rmdir()
        print(f"  删除空目录: {old_dir}")

    print("  [SUCCESS] um-cli 重组完成")


def setup_ytdlp():
    """设置 yt-dlp 目录结构"""
    print("=" * 60)
    print("设置 yt-dlp...")
    print("=" * 60)

    ytdlp_dir = VENDOR_DIR / "yt-dlp"
    source_dir = ytdlp_dir / "source"
    bin_dir = ytdlp_dir / "bin"
    patches_dir = ytdlp_dir / "patches"

    # 创建目录结构
    source_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(exist_ok=True)
    patches_dir.mkdir(exist_ok=True)

    # 克隆源码（如果不存在）
    if not (source_dir / "yt_dlp").exists():
        print(f"  克隆源码到: {source_dir}")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1",
                 "https://github.com/yt-dlp/yt-dlp.git", str(source_dir)],
                check=True,
                capture_output=True
            )
            print("  [SUCCESS] 源码克隆完成")
        except subprocess.CalledProcessError as e:
            print(f"  [FAILED] 克隆失败: {e}")
            return
    else:
        print("  [SKIP] 源码已存在")

    # 复制可执行文件（如果存在）
    ytdlp_exe = BIN_DIR / "yt-dlp.exe"
    if ytdlp_exe.exists():
        dest = bin_dir / "yt-dlp.exe"
        if not dest.exists():
            print(f"  复制可执行文件: {ytdlp_exe} -> {dest}")
            shutil.copy2(str(ytdlp_exe), str(dest))

    print("  [SUCCESS] yt-dlp 设置完成")


def setup_ffmpeg():
    """设置 FFmpeg 目录结构"""
    print("=" * 60)
    print("设置 FFmpeg...")
    print("=" * 60)

    ffmpeg_dir = VENDOR_DIR / "ffmpeg"
    bin_dir = ffmpeg_dir / "bin"
    patches_dir = ffmpeg_dir / "patches"

    # 创建目录结构
    bin_dir.mkdir(parents=True, exist_ok=True)
    patches_dir.mkdir(exist_ok=True)

    # 复制可执行文件
    for exe_name in ["ffmpeg.exe", "ffprobe.exe"]:
        exe_path = BIN_DIR / exe_name
        if exe_path.exists():
            dest = bin_dir / exe_name
            if not dest.exists():
                print(f"  复制可执行文件: {exe_path} -> {dest}")
                shutil.copy2(str(exe_path), str(dest))

    print("  [SUCCESS] FFmpeg 设置完成")


def setup_capcut_mate():
    """设置 capcut-mate 目录结构"""
    print("=" * 60)
    print("设置 capcut-mate...")
    print("=" * 60)

    capcut_dir = VENDOR_DIR / "capcut-mate"
    patches_dir = capcut_dir / "patches"

    if not capcut_dir.exists():
        print("  [SKIP] capcut-mate 目录不存在")
        return

    # 创建 patches 目录
    patches_dir.mkdir(exist_ok=True)

    print("  [SUCCESS] capcut-mate 设置完成")


def create_readme_files():
    """为每个工具创建 README.md"""
    print("=" * 60)
    print("创建 README 文件...")
    print("=" * 60)

    readmes = {
        "yt-dlp": {
            "name": "yt-dlp",
            "repo": "https://github.com/yt-dlp/yt-dlp",
            "purpose": "视频下载引擎",
            "frequency": "约每14天一个版本",
            "update_cmd": "python scripts/update_tools.py --ytdlp"
        },
        "ffmpeg": {
            "name": "FFmpeg",
            "repo": "https://github.com/FFmpeg/FFmpeg",
            "purpose": "媒体处理引擎",
            "frequency": "约每3-6个月",
            "update_cmd": "手动下载: https://github.com/BtbN/FFmpeg-Builds/releases"
        },
        "um-cli": {
            "name": "Unlock Music CLI",
            "repo": "https://github.com/unlock-music/cli",
            "purpose": "音乐解密工具",
            "frequency": "按需更新",
            "update_cmd": "python main.py decrypt build"
        },
        "capcut-mate": {
            "name": "capcut-mate",
            "repo": "https://github.com/Hommy-master/capcut-mate",
            "purpose": "剪映自动化工具",
            "frequency": "跟随剪映更新",
            "update_cmd": "python scripts/update_tools.py --capcut"
        }
    }

    for tool_dir, info in readmes.items():
        readme_path = VENDOR_DIR / tool_dir / "README.md"
        if readme_path.exists():
            print(f"  [SKIP] {tool_dir}/README.md 已存在")
            continue

        content = f"""# {info['name']}

## 基本信息
- **官方仓库**: {info['repo']}
- **用途**: {info['purpose']}
- **更新频率**: {info['frequency']}

## 目录结构
- `source/` - 官方源码
- `bin/` - 可执行文件
- `patches/` - 我们的补丁

## 更新方式
```bash
{info['update_cmd']}
```

## 补丁说明
暂无补丁

## 更新历史
- 2026-04-24: 初始化目录结构
"""

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(content, encoding="utf-8")
        print(f"  [SUCCESS] 创建 {tool_dir}/README.md")


def main():
    print("\n开始重组 vendor 目录结构...\n")

    # 确保目录存在
    VENDOR_DIR.mkdir(exist_ok=True)
    BIN_DIR.mkdir(exist_ok=True)

    # 执行重组
    reorganize_um_cli()
    setup_ytdlp()
    setup_ffmpeg()
    setup_capcut_mate()
    create_readme_files()

    print("\n" + "=" * 60)
    print("重组完成！")
    print("=" * 60)
    print("\n新的目录结构:")
    print("vendor/")
    print("├── yt-dlp/       (source/ + bin/ + patches/)")
    print("├── ffmpeg/       (bin/ + patches/)")
    print("├── um-cli/       (source/ + bin/ + patches/)")
    print("└── capcut-mate/  (源码 + patches/)")
    print("\n详细说明请查看: docs/VENDOR_ORGANIZATION.md")


if __name__ == "__main__":
    main()

