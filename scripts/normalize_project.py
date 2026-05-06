#!/usr/bin/env python3
"""
项目规范化脚本

按照 NAMING_CONVENTIONS.md 规范化项目结构
"""
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor"
MODULES_DIR = PROJECT_ROOT / "modules"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def normalize_vendor():
    """规范化 vendor 目录"""
    print("=" * 60)
    print("规范化 Vendor 目录...")
    print("=" * 60)

    # 1. 重命名 auditor_source -> auditor
    old_auditor = VENDOR_DIR / "auditor_source"
    new_auditor = VENDOR_DIR / "auditor"

    if old_auditor.exists() and not new_auditor.exists():
        print("\n重命名: auditor_source -> auditor")
        new_auditor.mkdir(exist_ok=True)
        src_dir = new_auditor / "src"
        src_dir.mkdir(exist_ok=True)

        # 移动所有文件到 src/
        for item in old_auditor.iterdir():
            if item.is_file():
                dest = src_dir / item.name
                print(f"  移动: {item.name} -> src/{item.name}")
                shutil.move(str(item), str(dest))
            elif item.is_dir() and item.name not in [".git", "__pycache__"]:
                dest = src_dir / item.name
                print(f"  移动: {item.name}/ -> src/{item.name}/")
                shutil.move(str(item), str(dest))

        # 删除旧目录
        if not any(old_auditor.iterdir()):
            old_auditor.rmdir()
            print("  删除空目录: auditor_source")

        # 创建 README.md
        readme = new_auditor / "README.md"
        readme.write_text("""# Auditor

## 基本信息
- **用途**: 素材审核工具
- **类型**: 自维护模块
- **语言**: Python

## 目录结构
- `src/` - 源码

## 使用方式
```bash
python main.py auditor status
python main.py auditor scan
```

## 维护说明
- 这是自维护模块，不需要追新
- 版本锁定在项目中
- 修改后需要测试

---
**最后更新**: 2026-04-24
""", encoding="utf-8")
        print("  创建: README.md")
    else:
        print("\n[SKIP] auditor 已规范化或不存在")

    # 2. 重命名 photoshop_auto -> photoshop
    old_ps = VENDOR_DIR / "photoshop_auto"
    new_ps = VENDOR_DIR / "photoshop"

    if old_ps.exists() and not new_ps.exists():
        print("\n重命名: photoshop_auto -> photoshop")
        new_ps.mkdir(exist_ok=True)
        src_dir = new_ps / "src"
        src_dir.mkdir(exist_ok=True)

        # 移动所有文件到 src/
        for item in old_ps.iterdir():
            if item.is_file():
                dest = src_dir / item.name
                print(f"  移动: {item.name} -> src/{item.name}")
                shutil.move(str(item), str(dest))
            elif item.is_dir() and item.name not in [".git", "__pycache__"]:
                dest = src_dir / item.name
                print(f"  移动: {item.name}/ -> src/{item.name}/")
                shutil.move(str(item), str(dest))

        # 删除旧目录
        if not any(old_ps.iterdir()):
            old_ps.rmdir()
            print("  删除空目录: photoshop_auto")

        # 创建 README.md
        readme = new_ps / "README.md"
        readme.write_text("""# Photoshop

## 基本信息
- **用途**: Photoshop 自动化工具
- **类型**: 自维护模块
- **语言**: Python

## 目录结构
- `src/` - 源码

## 使用方式
```bash
python main.py photoshop status
python main.py photoshop scan
```

## 维护说明
- 这是自维护模块，不需要追新
- 版本锁定在项目中
- 修改后需要测试

---
**最后更新**: 2026-04-24
""", encoding="utf-8")
        print("  创建: README.md")
    else:
        print("\n[SKIP] photoshop 已规范化或不存在")

    # 3. 归档废弃模块
    archived_dir = VENDOR_DIR / "_archived"
    archived_dir.mkdir(exist_ok=True)

    # 归档 wechat_moments_source
    old_wechat = VENDOR_DIR / "wechat_moments_source"
    if old_wechat.exists():
        new_wechat = archived_dir / "wechat-moments"
        if not new_wechat.exists():
            print("\n归档: wechat_moments_source -> _archived/wechat-moments")
            shutil.move(str(old_wechat), str(new_wechat))

            # 创建说明文件
            readme = new_wechat.parent / "README.md"
            if not readme.exists():
                readme.write_text("""# 归档模块

这个目录包含已废弃或不再使用的模块。

## wechat-moments
- **原因**: 功能已整合到 modules/generator/
- **归档时间**: 2026-04-24
- **说明**: 朋友圈图片生成功能现在是 generator 模块的一部分

## atom
- **原因**: 用途不明确
- **归档时间**: 2026-04-24
- **说明**: 待确认用途后决定是否删除

---
**维护者**: MediaTools Team
""", encoding="utf-8")
        else:
            print("\n[SKIP] wechat_moments_source 已归档")

    # 归档 atom
    old_atom = VENDOR_DIR / "atom"
    if old_atom.exists():
        new_atom = archived_dir / "atom"
        if not new_atom.exists():
            print("\n归档: atom -> _archived/atom")
            shutil.move(str(old_atom), str(new_atom))
        else:
            print("\n[SKIP] atom 已归档")

    print("\n[SUCCESS] Vendor 目录规范化完成")


def normalize_modules():
    """规范化 modules 目录"""
    print("\n" + "=" * 60)
    print("规范化 Modules 目录...")
    print("=" * 60)

    # 删除废弃的 wechat_moments 模块
    old_wechat = MODULES_DIR / "wechat_moments"
    if old_wechat.exists():
        print("\n删除废弃模块: wechat_moments")
        shutil.rmtree(str(old_wechat))
        print("  [SUCCESS] 已删除（功能已整合到 generator）")
    else:
        print("\n[SKIP] wechat_moments 已删除或不存在")

    print("\n[SUCCESS] Modules 目录规范化完成")


def normalize_scripts():
    """规范化 scripts 目录"""
    print("\n" + "=" * 60)
    print("规范化 Scripts 目录...")
    print("=" * 60)

    # 删除重复的 update_capcut_mate.py
    old_script = SCRIPTS_DIR / "update_capcut_mate.py"
    if old_script.exists():
        print("\n删除重复脚本: update_capcut_mate.py")
        old_script.unlink()
        print("  [SUCCESS] 已删除（功能已整合到 update_tools.py）")
    else:
        print("\n[SKIP] update_capcut_mate.py 已删除或不存在")

    # 创建 build 目录并移动构建脚本
    build_dir = SCRIPTS_DIR / "build"
    build_dir.mkdir(exist_ok=True)

    # 移动 build-um.ps1
    old_build = SCRIPTS_DIR / "build-um.ps1"
    if old_build.exists():
        new_build = build_dir / "build_um.ps1"
        if not new_build.exists():
            print("\n移动: build-um.ps1 -> build/build_um.ps1")
            shutil.move(str(old_build), str(new_build))
        else:
            print("\n[SKIP] build_um.ps1 已存在")

    # 处理 update.ps1
    old_update = SCRIPTS_DIR / "update.ps1"
    if old_update.exists():
        # 读取内容判断用途
        content = old_update.read_text(encoding="utf-8")
        if "uv" in content.lower() or "pip" in content.lower():
            new_update = build_dir / "update_deps.ps1"
            if not new_update.exists():
                print("\n移动: update.ps1 -> build/update_deps.ps1")
                shutil.move(str(old_update), str(new_update))
            else:
                print("\n[SKIP] update_deps.ps1 已存在")
        else:
            print("\n[WARNING] update.ps1 用途不明确，请手动检查")

    # 创建 build/README.md
    build_readme = build_dir / "README.md"
    if not build_readme.exists():
        build_readme.write_text("""# Build Scripts

构建和编译相关的脚本。

## 脚本说明

### build_um.ps1
- **用途**: 编译 um-cli (Windows)
- **使用**: `powershell scripts/build/build_um.ps1`

### update_deps.ps1
- **用途**: 更新 Python 依赖
- **使用**: `powershell scripts/build/update_deps.ps1`

---
**维护者**: MediaTools Team
**最后更新**: 2026-04-24
""", encoding="utf-8")
        print("\n创建: build/README.md")

    print("\n[SUCCESS] Scripts 目录规范化完成")


def update_adapters():
    """更新适配器路径"""
    print("\n" + "=" * 60)
    print("更新适配器路径...")
    print("=" * 60)

    # 需要更新的适配器文件
    adapter_files = [
        PROJECT_ROOT / "adapters" / "external_tools.py",
        PROJECT_ROOT / "modules" / "photoshop" / "adapter.py",
        PROJECT_ROOT / "modules" / "auditor" / "wrapper.py",
    ]

    updates = {
        "vendor/auditor_source": "vendor/auditor/src",
        "vendor/photoshop_auto": "vendor/photoshop/src",
    }

    for adapter_file in adapter_files:
        if not adapter_file.exists():
            continue

        content = adapter_file.read_text(encoding="utf-8")
        modified = False

        for old_path, new_path in updates.items():
            if old_path in content:
                print(f"\n更新: {adapter_file.name}")
                print(f"  {old_path} -> {new_path}")
                content = content.replace(old_path, new_path)
                modified = True

        if modified:
            adapter_file.write_text(content, encoding="utf-8")
            print("  [SUCCESS] 已更新")

    print("\n[SUCCESS] 适配器路径更新完成")


def main():
    print("\n开始项目规范化...\n")

    # 执行规范化
    normalize_vendor()
    normalize_modules()
    normalize_scripts()
    update_adapters()

    print("\n" + "=" * 60)
    print("规范化完成！")
    print("=" * 60)
    print("\n规范化内容:")
    print("[OK] Vendor 目录:")
    print("   - auditor_source -> auditor")
    print("   - photoshop_auto -> photoshop")
    print("   - wechat_moments_source -> _archived/wechat-moments")
    print("   - atom -> _archived/atom")
    print("\n[OK] Modules 目录:")
    print("   - 删除 wechat_moments（已整合到 generator）")
    print("\n[OK] Scripts 目录:")
    print("   - 删除 update_capcut_mate.py（功能已整合）")
    print("   - 移动构建脚本到 build/")
    print("\n[OK] 适配器:")
    print("   - 更新路径引用")
    print("\n详细说明请查看: docs/NAMING_CONVENTIONS.md")


if __name__ == "__main__":
    main()
