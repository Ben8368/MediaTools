#!/usr/bin/env python3
"""
自动更新外部工具到最新版本

用法:
    python scripts/update_tools.py              # 更新所有工具
    python scripts/update_tools.py --ytdlp      # 仅更新 yt-dlp
    python scripts/update_tools.py --capcut     # 仅更新 capcut-mate
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import get_logger
from modules.fetcher.ytdlp_manager import YtdlpManager

logger = get_logger(__name__)

CAPCUT_REPO_URL = "https://github.com/Hommy-master/capcut-mate.git"
CAPCUT_VENDOR_DIR = PROJECT_ROOT / "vendor" / "capcut-mate"


def update_ytdlp() -> bool:
    """更新 yt-dlp 到最新版本"""
    logger.info("=" * 60)
    logger.info("开始更新 yt-dlp...")
    logger.info("=" * 60)

    manager = YtdlpManager()

    if not manager.is_installed():
        logger.info("yt-dlp 未安装，正在下载...")
        success, msg = manager.download_latest()
    else:
        current_version = manager.get_version()
        logger.info(f"当前版本: {current_version}")
        logger.info("正在检查更新...")
        success, msg = manager.update()

    if success:
        logger.info(f"[SUCCESS] {msg}")
        new_version = manager.get_version()
        logger.info(f"最新版本: {new_version}")
        return True
    else:
        logger.error(f"[FAILED] {msg}")
        return False


def update_capcut_mate() -> bool:
    """更新 capcut-mate 到最新版本"""
    logger.info("=" * 60)
    logger.info("开始更新 capcut-mate...")
    logger.info("=" * 60)
    logger.info(f"目标目录: {CAPCUT_VENDOR_DIR}")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "capcut-mate"
        logger.info("\n1. 克隆最新版本到临时目录...")

        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", CAPCUT_REPO_URL, str(tmp_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("✅ 克隆成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 克隆失败: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("❌ git 未安装，请先安装 git")
            return False

        # 备份现有目录
        if CAPCUT_VENDOR_DIR.exists():
            backup_dir = CAPCUT_VENDOR_DIR.parent / "capcut-mate.backup"
            logger.info(f"\n2. 备份现有版本到: {backup_dir}")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(CAPCUT_VENDOR_DIR, backup_dir)
            logger.info("✅ 备份完成")

            # 删除旧版本
            logger.info("\n3. 删除旧版本...")
            shutil.rmtree(CAPCUT_VENDOR_DIR)
            logger.info("✅ 删除完成")

        # 复制新版本
        logger.info("\n4. 安装新版本...")
        shutil.copytree(tmp_path, CAPCUT_VENDOR_DIR, ignore=shutil.ignore_patterns(".git"))
        logger.info("✅ 安装完成")

    logger.info("\n✅ capcut-mate 更新成功！")
    logger.info("\n下一步:")
    logger.info("1. 检查 vendor/capcut-mate/pyproject.toml 的依赖")
    logger.info("2. 运行: cd vendor/capcut-mate && uv sync")
    logger.info("3. 测试: python main.py editor status")

    return True


def main():
    parser = argparse.ArgumentParser(description="更新外部工具到最新版本")
    parser.add_argument("--ytdlp", action="store_true", help="仅更新 yt-dlp")
    parser.add_argument("--capcut", action="store_true", help="仅更新 capcut-mate")
    parser.add_argument("--all", action="store_true", help="更新所有工具（默认）")

    args = parser.parse_args()

    # 如果没有指定任何选项，默认更新所有
    if not (args.ytdlp or args.capcut):
        args.all = True

    success_count = 0
    total_count = 0

    if args.ytdlp or args.all:
        total_count += 1
        if update_ytdlp():
            success_count += 1
        print()  # 空行分隔

    if args.capcut or args.all:
        total_count += 1
        if update_capcut_mate():
            success_count += 1
        print()

    # 总结
    logger.info("=" * 60)
    logger.info(f"更新完成: {success_count}/{total_count} 成功")
    logger.info("=" * 60)

    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()
