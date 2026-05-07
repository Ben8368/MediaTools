# Changelog

> **[English](./CHANGELOG.md)**

所有重要变更记录在这里。历史上游工具变更请查看 `vendor/` 下对应项目的 CHANGELOG。

## 2026-05-06

### 文档整理

- 重写根 `README.md`，去掉失效徽章、乱码文本和旧 Gradio 入口说明。
- 重写 `WORKFLOW.md`，明确当前推荐主线：工作区、下载、字幕分析、FFmpeg 切片、工作台复核。
- 重写 `ARCHITECTURE.md`，按当前 FastAPI + React + services/modules 结构说明维护边界。
- 重写 `docs/README.md`，把自有文档、专题文档和第三方文档分开。
- 清理并重写核心专题文档：
  - `docs/API_OVERVIEW.md`
  - `docs/DIRECTORY_STRUCTURE.md`
  - `docs/MODULE_DEPENDENCIES.md`
  - `docs/NAMING_CONVENTIONS.md`
  - `docs/EXTERNAL_TOOLS.md`
  - `docs/FRONTEND_OVERVIEW.md`
  - `docs/VENDOR_ORGANIZATION.md`
  - `docs/PATCH_SYSTEM.md`
  - `docs/TASK_QUEUE.md`
  - `docs/TOOL_FACTIONS.md`
- 重写 `docs/adobe/` 下 Atom、AE、COM/CEP 专题，标明当前集成状态和参考边界。

## 2026-04-24

### 安全和服务入口

- 默认服务绑定调整为本机地址。
- 增加 `API_SECRET_KEY` 配置，用于非本机绑定时的 API 保护。
- 增强输入校验、错误处理和日志输出。

### 功能模块

- 增加 `modules/generator`，支持视频截图和图片生成类能力。
- 确认并整理 Photoshop、auditor、wechat moments 等扩展能力入口。
- 扩展媒体下载、字幕处理、分析和切片链路。

### 测试

- 增加 `tests/` 下的 API、媒体服务、工作区、转码、工具补丁等测试覆盖。

### 持续维护方向

- 继续收敛 Web 和 CLI 的能力边界。
- 保持 FFmpeg 主线稳定，实验性 CapCut/capcut-mate 联动作为扩展能力维护。
- 持续补齐外部工具状态检查、任务中心和自动化测试。
