# Adobe 集成说明

> [English](./INTEGRATION.md)

## 用途

Photoshop 和 After Effects 自动化，用于专业工作流。

## 状态

**环境相关** - 需要本机安装 Adobe 软件。

## 维护

- 源码：`vendor/adobe/`（桥接材料）
- Photoshop：`modules/adobe/`、`backend/api/routes/photoshop.py`、`backend/services/photoshop.py`
- After Effects：`modules/adobe/`、`backend/api/routes/adobe.py`
- 前端：`frontend/src/apps/PhotoshopApp.tsx`、`frontend/src/apps/AEApp.tsx`

## 上游信息

- Adobe COM/CEP/ExtendScript 集成
- 依赖本机软件、权限和插件
- 高度环境相关

## 在 MediaTools 中的使用

| 功能 | 入口 |
|---|---|
| Photoshop 自动化 | `backend/services/photoshop.py` |
| After Effects | `backend/api/routes/adobe.py` |
| 状态管理 | `backend/services/photoshop_state.py` |

## 注意事项

- 验证软件已安装且允许自动化
- 检查端口和权限
- COM/ExtendScript/CEP 细节隔离在 Adobe 模块中
