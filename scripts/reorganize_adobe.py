#!/usr/bin/env python3
"""
重组 Adobe 工具模块

将 atom 和 photoshop 合并为统一的 adobe 模块
形成 Adobe 派系 vs 剪映派系的清晰对应
"""
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor"


def reorganize_adobe_tools():
    """重组 Adobe 工具"""
    print("=" * 60)
    print("重组 Adobe 工具模块...")
    print("=" * 60)

    # 创建 adobe 目录
    adobe_dir = VENDOR_DIR / "adobe"
    adobe_dir.mkdir(exist_ok=True)

    # 1. 移动 atom -> adobe/after-effects
    old_atom = VENDOR_DIR / "atom"
    new_ae = adobe_dir / "after-effects"

    if old_atom.exists() and not new_ae.exists():
        print("\n移动: atom -> adobe/after-effects")
        shutil.move(str(old_atom), str(new_ae))
        print("  [SUCCESS] After Effects 工具已移动")
    elif new_ae.exists():
        print("\n[SKIP] adobe/after-effects 已存在")
    else:
        print("\n[WARNING] atom 目录不存在")

    # 2. 移动 photoshop -> adobe/photoshop
    old_ps = VENDOR_DIR / "photoshop"
    new_ps = adobe_dir / "photoshop"

    if old_ps.exists() and not new_ps.exists():
        print("\n移动: photoshop -> adobe/photoshop")
        shutil.move(str(old_ps), str(new_ps))
        print("  [SUCCESS] Photoshop 工具已移动")
    elif new_ps.exists():
        print("\n[SKIP] adobe/photoshop 已存在")
    else:
        print("\n[WARNING] photoshop 目录不存在")

    # 3. 创建 adobe/README.md
    readme = adobe_dir / "README.md"
    readme.write_text("""# Adobe 工具集

## 概述

Adobe 工具集提供对 Adobe Creative Cloud 软件的自动化支持，包括 After Effects 和 Photoshop。

## 架构设计

```
adobe/
├── after-effects/      # After Effects 自动化
│   ├── Atom/           # CEP 扩展
│   └── README.md
│
├── photoshop/          # Photoshop 自动化
│   ├── src/            # Python 自动化脚本
│   └── README.md
│
└── README.md           # 本文档
```

## 工具对比

### Adobe 派系 vs 剪映派系

| 特性 | Adobe 工具集 | 剪映工具集 |
|------|-------------|-----------|
| **厂商** | Adobe | 字节跳动 |
| **定位** | 专业创作工具 | 大众剪辑工具 |
| **工具** | After Effects + Photoshop | CapCut (剪映) |
| **自动化方式** | CEP + Python | Python API |
| **适用场景** | 专业动效、平面设计 | 视频剪辑、特效 |

### After Effects (atom)

- **类型**: CEP 扩展
- **功能**:
  - 批量清理与整理图层
  - 快速创意探索
  - 表达式自动化
  - 控制器搭建
  - 生成图片素材
- **技术**: ExtendScript + AI (Codex)
- **官网**: https://tryatom.ai

### Photoshop

- **类型**: Python 自动化脚本
- **功能**:
  - PSD 文档扫描
  - 批量修改文案
  - 批量修改字体
  - 多语言支持
- **技术**: Python + pywin32 + COM
- **状态**: 自维护

## 技术架构

### CEP (Common Extensibility Platform)

Adobe 的官方扩展框架，支持：
- HTML/CSS/JavaScript 前端
- ExtendScript 后端（与 Adobe 软件通信）
- 跨平台（Windows + macOS）

### Python 自动化

通过 COM 接口控制 Adobe 软件：
- pywin32 库
- win32com.client
- 仅支持 Windows

## 集成方式

### 1. 独立使用

#### After Effects
```bash
# 安装 CEP 扩展
# Windows: C:\\Program Files\\Common Files\\Adobe\\CEP\\extensions\\
# macOS: /Library/Application Support/Adobe/CEP/extensions/

复制 after-effects/Atom/ 到扩展目录
```

#### Photoshop
```bash
# 通过 MediaTools 调用
python main.py photoshop status
python main.py photoshop scan <psd_path>
```

### 2. 与 MediaTools 集成

#### 工作流示例 1: 视频素材 -> AE 动效
```
1. MediaTools 下载视频素材
2. After Effects (Atom) 制作动效
3. 输出回 MediaTools 素材库
```

#### 工作流示例 2: PSD 批量处理
```
1. MediaTools 扫描 PSD 文件
2. Photoshop 自动化批量修改
3. 导出到素材库
```

## 未来规划

### 短期
- [ ] 统一 Adobe 工具的 API 接口
- [ ] 创建 `modules/adobe/` 统一模块
- [ ] 集成到 Agent

### 中期
- [ ] 考虑将 Photoshop 也改造成 CEP 扩展
- [ ] 统一使用 CEP 架构
- [ ] 提供统一的前端界面

### 长期
- [ ] 支持更多 Adobe 软件（Premiere Pro, Illustrator）
- [ ] 完整的 Adobe 工作流自动化
- [ ] 与剪映工具形成互补

## 对比：剪映工具集

```
vendor/capcut-mate/     # 剪映自动化
├── (Python 源码)
├── patches/
└── README.md
```

**特点**:
- 专注视频剪辑
- Python API 集成
- 需要追新（跟随剪映更新）

## 技术选型建议

### 何时使用 Adobe 工具
- 需要专业动效（AE）
- 需要批量处理 PSD
- 需要高质量输出
- 团队熟悉 Adobe 生态

### 何时使用剪映工具
- 快速视频剪辑
- 自动化特效
- 批量视频处理
- 需要 AI 辅助功能

## 维护说明

### After Effects (atom)
- **类型**: 第三方 CEP 扩展
- **更新**: 从官网下载新版本
- **维护**: 不需要追新

### Photoshop
- **类型**: 自维护脚本
- **更新**: 项目内维护
- **维护**: 版本锁定

## 相关文档

- [After Effects 集成指南](./after-effects/README.md)
- [Photoshop 集成指南](./photoshop/README.md)
- [ATOM_INTEGRATION.md](../../docs/ATOM_INTEGRATION.md)
- [剪映工具对比](../capcut-mate/README.md)

---

**维护者**: MediaTools Team
**最后更新**: 2026-04-24
**版本**: v1.0
""", encoding="utf-8")

    print("\n创建: adobe/README.md")

    # 4. 更新 after-effects/README.md
    ae_readme = new_ae / "README.md"
    if ae_readme.exists():
        content = ae_readme.read_text(encoding="utf-8")
        # 添加返回链接
        if "返回 Adobe 工具集" not in content:
            content = content.replace(
                "---\n\n**维护者**",
                "---\n\n## 相关文档\n\n- [返回 Adobe 工具集](../README.md)\n- [Photoshop 工具](../photoshop/README.md)\n- [剪映工具对比](../../capcut-mate/README.md)\n\n---\n\n**维护者**"
            )
            ae_readme.write_text(content, encoding="utf-8")
            print("  更新: after-effects/README.md")

    # 5. 更新 photoshop/README.md
    ps_readme = new_ps / "README.md"
    if ps_readme.exists():
        content = ps_readme.read_text(encoding="utf-8")
        # 添加返回链接
        if "返回 Adobe 工具集" not in content:
            content = content.replace(
                "---\n**最后更新**",
                "---\n\n## 相关文档\n\n- [返回 Adobe 工具集](../README.md)\n- [After Effects 工具](../after-effects/README.md)\n- [剪映工具对比](../../capcut-mate/README.md)\n\n---\n\n**最后更新**"
            )
            ps_readme.write_text(content, encoding="utf-8")
            print("  更新: photoshop/README.md")

    print("\n[SUCCESS] Adobe 工具重组完成")


def update_adapters():
    """更新适配器路径"""
    print("\n" + "=" * 60)
    print("更新适配器路径...")
    print("=" * 60)

    # 更新 photoshop_runtime.py
    ps_adapter = PROJECT_ROOT / "adapters" / "photoshop_runtime.py"
    if ps_adapter.exists():
        content = ps_adapter.read_text(encoding="utf-8")
        old_path = 'BASE_DIR / "vendor" / "photoshop"'
        new_path = 'BASE_DIR / "vendor" / "adobe" / "photoshop"'

        if old_path in content:
            content = content.replace(old_path, new_path)
            ps_adapter.write_text(content, encoding="utf-8")
            print("  [SUCCESS] 更新 photoshop_runtime.py")
        else:
            print("  [SKIP] photoshop_runtime.py 已是最新")

    print("\n[SUCCESS] 适配器路径更新完成")


def main():
    print("\n开始重组 Adobe 工具模块...\n")

    reorganize_adobe_tools()
    update_adapters()

    print("\n" + "=" * 60)
    print("重组完成！")
    print("=" * 60)
    print("\n新的目录结构:")
    print("vendor/")
    print("├── adobe/              # Adobe 工具集")
    print("│   ├── after-effects/  # After Effects (atom)")
    print("│   ├── photoshop/      # Photoshop 自动化")
    print("│   └── README.md")
    print("│")
    print("└── capcut-mate/        # 剪映工具集")
    print("\n形成两大派系:")
    print("✅ Adobe 派系: After Effects + Photoshop")
    print("✅ 剪映派系: CapCut")
    print("\n详细说明请查看: vendor/adobe/README.md")


if __name__ == "__main__":
    main()
