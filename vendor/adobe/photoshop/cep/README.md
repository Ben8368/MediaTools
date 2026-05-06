# Photoshop CEP 扩展

## 基本信息

- **名称**: MediaTools Photoshop
- **用途**: 在 Photoshop 内调用 MediaTools 本地服务，完成 PSD 扫描、工单确认与批量执行
- **类型**: CEP 扩展

## 目录结构

```text
cep/
├── index.html
├── CSInterface.js
├── polyfills.js
├── .debug
├── CSXS/
│   └── manifest.xml
├── jsx/
│   └── Main.jsx
└── README.md
```

## 面板能力

- 连接 MediaTools API（`/api/photoshop/*`）
- 读取 Photoshop 自动化状态
- 扫描当前文档、单个 PSD、或 PSD 文件夹
- 加载并编辑 Photoshop 工单 JSON
- 执行、Dry Run、取消 Photoshop 任务
- 通过 `/ws/jobs` 查看扫描和执行进度

## 安装方式

### Windows
```text
复制 cep/ 目录到 Adobe CEP 扩展目录并重命名为 MediaTools:
C:\Program Files\Common Files\Adobe\CEP\extensions\MediaTools\
```

### macOS
```text
复制 cep/ 目录到 Adobe CEP 扩展目录并重命名为 MediaTools:
/Library/Application Support/Adobe/CEP/extensions/MediaTools/
```

## 使用方式

1. 启动 MediaTools API。
2. 启动 Photoshop。
3. 在菜单栏选择 `Window > Extensions > MediaTools`。
4. 在面板里填写 API 地址和 API Key。
5. 扫描、确认工单并执行任务。

## 依赖关系

- 前端面板：CEP / CEF / JavaScript
- 后端服务：MediaTools API
- Photoshop 自动化：`adapters/photoshop_runtime.py` + `../com/`

## 相关文档

- [返回 Photoshop 总览](../README.md)
- [Photoshop COM 连接器](../com/README.md)
- [Adobe 工具集总览](../../README.md)

---

**维护者**: MediaTools Team  
**最后更新**: 2026-05-06
