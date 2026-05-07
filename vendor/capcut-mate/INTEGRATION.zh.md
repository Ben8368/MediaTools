# capcut-mate 集成说明

> [English](./INTEGRATION.md)

## 用途

实验性 CapCut（剪映）自动化集成。

## 状态

**实验性** - 不建议作为唯一生产导出路径。

## 维护

- 源码：`vendor/capcut-mate/`（上游）
- 适配器：`modules/editor/`
- 运行时：`backend/services/runtime/editor.py`
- 配置：`CAPCUT_MATE_BASE_URL=http://localhost:30000`

## 上游信息

- 项目：`vendor/capcut-mate/`
- 接口和本机环境经常变化
- 自动化稳定性不如 FFmpeg 流程

## 在 MediaTools 中的使用

- 提供 CapCut 的替代导出路径
- 稳定可复现的导出优先 FFmpeg
- 使用前验证本机环境
