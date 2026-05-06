# Adobe 工具集

## 概述

Adobe 工具集提供对 Adobe Creative Cloud 软件的自动化支持，包括 After Effects 和 Photoshop。

## 目录结构

```text
adobe/
├── after-effects/
│   ├── cep/              # After Effects CEP 扩展
│   │   ├── Atom/
│   │   └── README.md
│   ├── com/              # After Effects COM 连接器
│   │   ├── src/
│   │   └── README.md
│   └── README.md
├── photoshop/
│   ├── cep/              # Photoshop CEP 扩展
│   │   ├── MediaTools/
│   │   └── README.md
│   ├── com/              # Photoshop COM 连接器
│   │   ├── src/
│   │   └── README.md
│   └── README.md
└── README.md
```

## 架构说明

每个产品目录都按两种集成方式拆分：

- **CEP 扩展**: 在 Adobe 应用内部运行，适合交互式操作
- **COM 连接器**: 从外部 Python 调用，适合批量处理和自动化任务

## 产品说明

### After Effects

- `after-effects/cep/`：AE 面板扩展，当前保留 `Atom/` 作为 CEP 载荷目录
- `after-effects/com/`：AE COM 连接器，供 `adapters/after_effects_runtime.py` 加载
- 详细说明：[`after-effects/README.md`](./after-effects/README.md)

### Photoshop

- `photoshop/cep/`：Photoshop 面板扩展，当前保留 `MediaTools/` 作为 CEP 载荷目录
- `photoshop/com/`：Photoshop COM 连接器，供 `adapters/photoshop_runtime.py` 加载
- 详细说明：[`photoshop/README.md`](./photoshop/README.md)

## 安装与调用

### 安装 CEP 扩展

```text
After Effects: 复制 after-effects/cep/ 整个目录到 Adobe CEP 扩展目录，重命名为 Atom
Photoshop:     复制 photoshop/cep/ 整个目录到 Adobe CEP 扩展目录，重命名为 MediaTools
```

常见 CEP 扩展目录：
- Windows: `C:\Program Files\Common Files\Adobe\CEP\extensions\`
- macOS: `/Library/Application Support/Adobe/CEP/extensions/`

### 调用 COM 连接器

```bash
python main.py adobe after_effects status
python main.py adobe photoshop status
python main.py adobe photoshop scan <psd_path>
```

## 相关文档

- [After Effects 总览](./after-effects/README.md)
- [After Effects CEP 扩展](./after-effects/cep/README.md)
- [After Effects COM 连接器](./after-effects/com/README.md)
- [Photoshop 总览](./photoshop/README.md)
- [Photoshop CEP 扩展](./photoshop/cep/README.md)
- [Photoshop COM 连接器](./photoshop/com/README.md)
- [ATOM_INTEGRATION.md](../../docs/ATOM_INTEGRATION.md)
- [剪映工具对比](../capcut-mate/README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-06  
**版本**: v3.0 - 产品优先目录结构
