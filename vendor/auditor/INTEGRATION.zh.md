# auditor 集成说明

> [English](./INTEGRATION.md)

## 用途

素材审核流程，用于材料合规性和质量检查。

## 状态

**环境相关** - 需要本机软件配置。

## 维护

- 源码：`vendor/auditor/`（上游）
- 服务：`backend/services/auditor.py`
- API：`backend/api/routes/auditor.py`
- CLI 封装：`modules/auditor/`
- 前端：`frontend/src/apps/AuditorApp.tsx`

## 上游信息

- 项目：`vendor/auditor/`
- 依赖本机配置
- 原始文档：`vendor/auditor/src/README.md`

## 在 MediaTools 中的使用

- 提供素材合规性检查
- 通过服务层和 API 路由集成
- 使用前验证本机环境
