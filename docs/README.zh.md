# MediaTools 文档索引

> **[English](./README.md)**

优先阅读顺序：

1. [根 README](../README.zh.md)：项目用途、安装、启动和常用命令
2. [WORKFLOW.zh.md](../WORKFLOW.zh.md)：当前推荐工作流
3. [ARCHITECTURE.zh.md](../ARCHITECTURE.zh.md)：当前代码结构和维护边界
4. 本文档：专题资料索引和文档状态说明

## 当前维护文档

这些文档应与当前实现保持一致，后续改动优先更新：

| 文档 | 内容 |
|---|---|
| [API_OVERVIEW.zh.md](./API_OVERVIEW.zh.md) | FastAPI 路由分组和维护边界 |
| [DIRECTORY_STRUCTURE.zh.md](./DIRECTORY_STRUCTURE.zh.md) | 目录结构和职责边界 |
| [FRONTEND_OVERVIEW.zh.md](./FRONTEND_OVERVIEW.zh.md) | React 前端应用结构 |
| [MODULE_DEPENDENCIES.zh.md](./MODULE_DEPENDENCIES.zh.md) | 模块分层和依赖关系 |
| [NAMING_CONVENTIONS.zh.md](./NAMING_CONVENTIONS.zh.md) | 命名约定 |
| [EXTERNAL_TOOLS.zh.md](./EXTERNAL_TOOLS.zh.md) | yt-dlp、FFmpeg、um-cli 等外部工具管理 |
| [VENDOR_ORGANIZATION.zh.md](./VENDOR_ORGANIZATION.zh.md) | `vendor/` 目录组织规范 |
| [PATCH_SYSTEM.zh.md](./PATCH_SYSTEM.zh.md) | 外部工具补丁系统 |
| [TASK_QUEUE.zh.md](./TASK_QUEUE.zh.md) | 当前内置任务中心和长任务机制 |

## 设计和专题文档

这些文档记录设计背景、对比分析或阶段性方案。阅读时需要结合当前代码确认实现状态：

| 文档 | 状态 |
|---|---|
| [TOOL_FACTIONS.zh.md](./TOOL_FACTIONS.zh.md) | Adobe/剪映等工具路线对比资料 |

## Adobe 专题

| 文档 | 内容 |
|---|---|
| [adobe/ATOM_INTEGRATION.zh.md](./adobe/ATOM_INTEGRATION.zh.md) | Atom 插件集成说明 |
| [adobe/ae_capability_comparison.zh.md](./adobe/ae_capability_comparison.zh.md) | After Effects 能力对比 |
| [adobe/com_vs_cep_technical_proof.zh.md](./adobe/com_vs_cep_technical_proof.zh.md) | COM 与 CEP 技术可行性 |
| [adobe/atom_plugin_capabilities.zh.md](./adobe/atom_plugin_capabilities.zh.md) | Atom 插件能力说明 |

## 英文文档

所有文档均有对应的英文主版本。英文文档是项目默认入口：

| 中文版本 | 英文版本 |
|---|---|
| `README.zh.md` | [README.md](../README.md) |
| `ARCHITECTURE.zh.md` | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| `WORKFLOW.zh.md` | [WORKFLOW.md](../WORKFLOW.md) |
| `CHANGELOG.zh.md` | [CHANGELOG.md](../CHANGELOG.md) |
| `docs/API_OVERVIEW.zh.md` | [API_OVERVIEW.md](./API_OVERVIEW.md) |
| `docs/DIRECTORY_STRUCTURE.zh.md` | [DIRECTORY_STRUCTURE.md](./DIRECTORY_STRUCTURE.md) |
| `docs/FRONTEND_OVERVIEW.zh.md` | [FRONTEND_OVERVIEW.md](./FRONTEND_OVERVIEW.md) |
| `docs/MODULE_DEPENDENCIES.zh.md` | [MODULE_DEPENDENCIES.md](./MODULE_DEPENDENCIES.md) |
| `docs/NAMING_CONVENTIONS.zh.md` | [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) |
| `docs/EXTERNAL_TOOLS.zh.md` | [EXTERNAL_TOOLS.md](./EXTERNAL_TOOLS.md) |
| `docs/VENDOR_ORGANIZATION.zh.md` | [VENDOR_ORGANIZATION.md](./VENDOR_ORGANIZATION.md) |
| `docs/PATCH_SYSTEM.zh.md` | [PATCH_SYSTEM.md](./PATCH_SYSTEM.md) |
| `docs/TASK_QUEUE.zh.md` | [TASK_QUEUE.md](./TASK_QUEUE.md) |
| `docs/TOOL_FACTIONS.zh.md` | [TOOL_FACTIONS.md](./TOOL_FACTIONS.md) |

## 文档维护规则

- 面向用户的快速说明写在根 README。
- 操作流程写在 `WORKFLOW.md`。
- 代码结构、边界和数据流写在 `ARCHITECTURE.md`。
- 专题方案放在 `docs/`，并在本文标注状态。
- 第三方工具原文保留在 `vendor/`，不要混入项目主文档。
- 如果实现和文档冲突，优先修文档入口，再决定是否归档旧专题。
