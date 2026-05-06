# MediaTools 文档索引

优先阅读顺序：

1. [根 README](../README.md)：项目用途、安装、启动和常用命令
2. [WORKFLOW.md](../WORKFLOW.md)：当前推荐工作流
3. [ARCHITECTURE.md](../ARCHITECTURE.md)：当前代码结构和维护边界
4. 本文档：专题资料索引和文档状态说明

## 当前维护文档

这些文档应与当前实现保持一致，后续改动优先更新：

| 文档 | 内容 |
|---|---|
| [DIRECTORY_STRUCTURE.md](./DIRECTORY_STRUCTURE.md) | 目录结构和职责边界 |
| [MODULE_DEPENDENCIES.md](./MODULE_DEPENDENCIES.md) | 模块分层和依赖关系 |
| [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) | 命名约定 |
| [EXTERNAL_TOOLS.md](./EXTERNAL_TOOLS.md) | yt-dlp、FFmpeg、um-cli 等外部工具管理 |
| [VENDOR_ORGANIZATION.md](./VENDOR_ORGANIZATION.md) | `vendor/` 目录组织规范 |
| [PATCH_SYSTEM.md](./PATCH_SYSTEM.md) | 外部工具补丁系统 |

## 设计和专题文档

这些文档记录设计背景、对比分析或阶段性方案。阅读时需要结合当前代码确认实现状态：

| 文档 | 状态 |
|---|---|
| [TASK_QUEUE.md](./TASK_QUEUE.md) | 任务队列设计资料，当前实现以 `services/task_center.py` 为准 |
| [TOOL_FACTIONS.md](./TOOL_FACTIONS.md) | Adobe/剪映等工具路线对比资料 |

## Adobe 专题

| 文档 | 内容 |
|---|---|
| [adobe/ATOM_INTEGRATION.md](./adobe/ATOM_INTEGRATION.md) | Atom 插件集成说明 |
| [adobe/ae_capability_comparison.md](./adobe/ae_capability_comparison.md) | After Effects 能力对比 |
| [adobe/com_vs_cep_technical_proof.md](./adobe/com_vs_cep_technical_proof.md) | COM 与 CEP 技术可行性 |
| [adobe/atom_plugin_capabilities.md](./adobe/atom_plugin_capabilities.md) | Atom 插件能力说明 |

## 第三方文档

`vendor/` 下还有大量 README、CHANGELOG、LICENSE 和上游文档。它们属于第三方项目，不纳入 MediaTools 自有文档索引。需要排查某个外部工具时，再进入对应目录阅读。

常见第三方目录：

- `vendor/yt-dlp/`
- `vendor/filebrowser/`
- `vendor/capcut-mate/`
- `vendor/adobe/`
- `vendor/auditor/`

## 文档维护规则

- 面向用户的快速说明写在根 README。
- 操作流程写在 `WORKFLOW.md`。
- 代码结构、边界和数据流写在 `ARCHITECTURE.md`。
- 专题方案放在 `docs/`，并在本文标注状态。
- 第三方工具原文保留在 `vendor/`，不要混入项目主文档。
- 如果实现和文档冲突，优先修文档入口，再决定是否归档旧专题。
