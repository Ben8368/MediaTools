# filebrowser 集成说明

> [English](./INTEGRATION.md)

## 用途

工作区文件浏览和本地文件服务。

## 状态

**可选** - 增强文件管理体验。

## 维护

- 源码：`vendor/filebrowser/`（上游）
- 运行时：`backend/services/runtime/filebrowser.py`
- API：`backend/api/routes/filebrowser.py`
- CLI 封装：`modules/filebrowser/`

## 上游信息

- 官方：https://github.com/filebrowser/filebrowser
- 文档：`vendor/filebrowser/www/docs/`
- MediaTools 仅封装运行时；不修改上游代码

## 在 MediaTools 中的使用

- 提供工作区文件浏览
- 集成隔离在运行时服务层
- 配置通过 `.env` 和工作区设置管理
