# um-cli 集成说明

> [English](./INTEGRATION.md)

## 用途

音乐和媒体解密（如 `.ncm` 加密格式）。

## 状态

**可选** - 仅在解密流程中需要。

## 维护

- 位置：`bin/um-cli`
- 服务：`backend/services/decryptor.py`
- CLI 模块：`modules/decryptor/`
- 本地编译可能需要 Go

## 在 MediaTools 中的使用

| 功能 | 模块 |
|---|---|
| 解密 | `modules/decryptor/` |
| 服务 | `backend/services/decryptor.py` |

```powershell
python -m cli.main decryptor run -i song.ncm
```

## 上游信息

- 属于 Unlock Music 项目
- 基于 Go 的 CLI 工具
- 原始源码：`vendor/um-cli/`
