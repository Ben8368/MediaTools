# Photoshop COM 连接器

## 概述

本目录存放通过 COM 接口从外部控制 Photoshop 的 Python 运行时。

## 目录结构

```text
com/
├── src/                        ← 源代码
│   ├── ps_connector.py
│   ├── text_modifier.py
│   ├── ticket_workflow.py
│   ├── adaptive_lab.py
│   ├── adaptive_algorithm.py
│   ├── psa_applier.py
│   ├── document_scanner.py
│   ├── smart_object_handler.py
│   ├── font_resolver.py
│   └── ...
├── tuning/                     ← 调优测试
│   ├── test.psd                ← 测试母版
│   └── README.md               ← 调优指南
└── README.md                   ← 本文档
```

## 使用方式

```python
from adapters.photoshop_runtime import PhotoshopAutomationAdapter

adapter = PhotoshopAutomationAdapter()
runtime = adapter.load_runtime()
connector = runtime["PhotoshopConnector"]()
```

## 说明

- 适配器根路径：`vendor/adobe/photoshop/com/src`
- 仅支持 Windows + pywin32
- 供 MediaTools 后端和服务层加载

## 核心模块

### PSA 自适应算法

位于 `src/adaptive_*.py`，负责跨字体的文字图层参数自适应：

- `adaptive_lab.py` - Lab 文档环境 + `find_adapted_params()` 核心算法
- `adaptive_algorithm.py` - Phase 1/2/3 迭代算法（字号、行高、字距）
- `psa_applier.py` - 单层处理流程：CALIBRATE → APPLY → VERIFY → REFINE

**调优指南**：[tuning/README.md](tuning/README.md) - 往返测试方法、评估指标、问题定位

## 相关文档

- [返回 Photoshop 总览](../README.md)
- [Photoshop CEP 扩展](../cep/README.md)
- [Adobe 工具集总览](../../README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-14
