#!/usr/bin/env python3
"""
恢复 Atom 模块并集成到项目

Atom 是 After Effects 自动化工具，用于：
- 批量清理与整理图层
- 快速尝试创意和动效
- 表达式自动化
- 生成图片素材
"""
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor"
ARCHIVED_ATOM = VENDOR_DIR / "_archived" / "atom"
NEW_ATOM = VENDOR_DIR / "atom"


def restore_atom():
    """恢复 Atom 到 vendor 目录"""
    print("=" * 60)
    print("恢复 Atom 模块...")
    print("=" * 60)

    if not ARCHIVED_ATOM.exists():
        print("[ERROR] 归档的 Atom 目录不存在")
        return False

    if NEW_ATOM.exists():
        print("[SKIP] Atom 目录已存在")
        return True

    # 移动回 vendor 目录
    print("\n移动: _archived/atom -> atom")
    shutil.move(str(ARCHIVED_ATOM), str(NEW_ATOM))

    # 创建 README.md
    readme = NEW_ATOM / "README.md"
    readme.write_text("""# Atom - After Effects 自动化工具

## 基本信息
- **官方网站**: https://tryatom.ai
- **官方文档**: https://tryatom.ai/docs/introduction
- **用途**: After Effects 自动化插件
- **类型**: 自维护模块（CEP 扩展）

## 功能特性

### 1. 批量清理与整理
- 重命名图层
- 重排图层顺序
- 批量编辑图层属性

### 2. 快速创意探索
- 快速尝试运动效果
- 调整节奏和配色
- 迭代动效方案

### 3. 表达式自动化
- 快速添加 wiggle 表达式
- 属性联动
- 解释现有表达式

### 4. 控制器搭建
- 用滑块统一控制
- 属性同步
- 快速搭建 rig

### 5. 生成图片素材
- 在聊天中生成纹理
- 生成精灵图
- 生成氛围图并自动导入工程

## 目录结构

```
atom/
├── Atom/               # CEP 扩展主体
│   ├── jsx/            # ExtendScript 脚本
│   ├── assets/         # 资源文件
│   ├── fonts/          # 字体文件
│   ├── CSXS/           # CEP 配置
│   └── META-INF/       # 扩展元数据
├── mcp/                # MCP 服务器（可能）
└── README.md
```

## 安装方式

### Windows
```
复制 Atom 文件夹到:
C:\\Program Files\\Common Files\\Adobe\\CEP\\extensions\\
```

### macOS
```
复制 Atom 文件夹到:
/Library/Application Support/Adobe/CEP/extensions/
```

## 使用方式

1. 启动 After Effects
2. 在菜单栏选择: Window > Extensions > Atom
3. 在 Atom 面板中用自然语言描述需求
4. Atom 会自动生成并执行脚本

## 典型使用场景

### 场景 1: 批量重命名图层
```
"将所有图层重命名为 layer_001, layer_002..."
```

### 场景 2: 添加运动效果
```
"给所有文字图层添加 wiggle 表达式，频率 2，幅度 50"
```

### 场景 3: 快速调色
```
"将所有图层的色调调整为暖色调"
```

### 场景 4: 生成素材
```
"生成一个科技感的背景纹理"
```

## 集成到 MediaTools

### 作为 AE 自动化模块
Atom 可以作为 MediaTools 的 After Effects 自动化能力：

1. **素材生成**: 生成动效素材
2. **批量处理**: 批量处理 AE 工程
3. **自动化工作流**: 与其他模块配合

### 潜在集成方式

```python
# modules/ae_automation/
# - 通过 Atom 的 API 或脚本接口
# - 批量处理 AE 工程
# - 自动化动效生成
```

## 技术架构

- **CEP (Common Extensibility Platform)**: Adobe 扩展框架
- **ExtendScript**: AE 脚本语言
- **AI 驱动**: 使用 Codex 理解自然语言

## 维护说明

- 这是第三方 CEP 扩展，不需要追新
- 版本锁定在项目中
- 如需更新，从官网下载新版本

## 相关链接

- [官方文档](https://tryatom.ai/docs/introduction)
- [CEP 开发指南](https://github.com/Adobe-CEP/CEP-Resources)
- [ExtendScript 文档](https://extendscript.docsforadobe.dev/)

---

**维护者**: MediaTools Team
**最后更新**: 2026-04-24
**状态**: 已恢复，待集成
""", encoding="utf-8")

    print("  创建: README.md")
    print("\n[SUCCESS] Atom 模块已恢复")
    return True


def update_docs():
    """更新相关文档"""
    print("\n" + "=" * 60)
    print("更新文档...")
    print("=" * 60)

    # 更新 VENDOR_ORGANIZATION.md
    vendor_org = PROJECT_ROOT / "docs" / "VENDOR_ORGANIZATION.md"
    if vendor_org.exists():
        content = vendor_org.read_text(encoding="utf-8")

        # 添加 atom 到自维护工具列表
        if "atom" not in content.lower() or "_archived" in content:
            print("\n需要手动更新 VENDOR_ORGANIZATION.md")
            print("  - 将 atom 从归档列表移除")
            print("  - 添加到自维护工具列表")

    # 更新 NAMING_CONVENTIONS.md
    naming = PROJECT_ROOT / "docs" / "NAMING_CONVENTIONS.md"
    if naming.exists():
        content = naming.read_text(encoding="utf-8")
        if "_archived/atom" in content:
            print("\n需要手动更新 NAMING_CONVENTIONS.md")
            print("  - 更新 atom 的状态")

    print("\n[INFO] 文档更新提示已显示")


def main():
    print("\n开始恢复 Atom 模块...\n")

    success = restore_atom()
    if success:
        update_docs()

        print("\n" + "=" * 60)
        print("恢复完成！")
        print("=" * 60)
        print("\nAtom 模块已恢复到: vendor/atom/")
        print("\n下一步:")
        print("1. 查看 vendor/atom/README.md 了解详情")
        print("2. 考虑是否需要创建 modules/ae_automation/ 模块")
        print("3. 更新相关文档")
        print("4. 考虑集成到 Agent 和前端")
    else:
        print("\n[FAILED] 恢复失败")


if __name__ == "__main__":
    main()
