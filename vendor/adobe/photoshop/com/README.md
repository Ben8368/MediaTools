# Photoshop COM 连接器

## 概述

本目录存放通过 COM 接口从外部控制 Photoshop 的 Python 运行时。

## 目录结构

```text
com/
├── src/
│   ├── ps_connector.py
│   ├── text_modifier.py
│   ├── ticket_workflow.py
│   ├── ticket_json.py
│   ├── ticket_excel.py
│   ├── config_reader.py
│   ├── font_analyzer.py
│   ├── font_verifier.py
│   ├── font_weight_mapper.py
│   ├── font_metrics_cache.py
│   └── ...
└── README.md
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

## 相关文档

- [返回 Photoshop 总览](../README.md)
- [Photoshop CEP 扩展](../cep/README.md)
- [Adobe 工具集总览](../../README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-06
