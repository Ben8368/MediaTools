# After Effects

## 概述

After Effects 相关能力拆分为两部分：

- `cep/`：应用内 CEP 扩展
- `com/`：应用外 COM 自动化连接器

## 目录结构

```text
after-effects/
├── cep/
│   ├── Atom/
│   └── README.md
├── com/
│   ├── src/
│   └── README.md
└── README.md
```

## 使用方式

- 在 AE 内交互式使用面板时，查看 [`cep/README.md`](./cep/README.md)
- 从 MediaTools 或脚本调用自动化能力时，查看 [`com/README.md`](./com/README.md)

## 相关文档

- [返回 Adobe 工具集](../README.md)
- [After Effects CEP 扩展](./cep/README.md)
- [After Effects COM 连接器](./com/README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-06
