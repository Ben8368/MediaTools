# After Effects COM 连接器

## 概述

本目录存放通过 COM 接口从外部控制 After Effects 的 Python 运行时。

## 目录结构

```text
com/
├── src/
│   ├── ae_connector.py
│   └── ae_connector_extensions.py
└── README.md
```

## 使用方式

```python
from adapters.after_effects_runtime import AfterEffectsAutomationAdapter

adapter = AfterEffectsAutomationAdapter()
runtime = adapter.load_runtime()
connector = runtime["AfterEffectsConnector"]()
```

## 说明

- 适配器根路径：`vendor/adobe/after-effects/com/src`
- 仅支持 Windows + pywin32
- 供 MediaTools 后端和服务层加载

## 相关文档

- [返回 After Effects 总览](../README.md)
- [After Effects CEP 扩展](../cep/README.md)
- [Adobe 工具集总览](../../README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-06
