# vendor 目录组织

> **[English](./VENDOR_ORGANIZATION.md)**

`vendor/` 用于存放第三方源码、嵌入工具和上游文档。这里不是 MediaTools 自有业务代码的主要维护位置。

## 当前常见目录

| 目录 | 用途 |
|---|---|
| `vendor/yt-dlp/` | yt-dlp 上游源码、二进制或相关资料 |
| `vendor/ffmpeg/` | FFmpeg 相关说明或本地资源 |
| `vendor/filebrowser/` | filebrowser 上游项目 |
| `vendor/capcut-mate/` | capcut-mate 上游项目 |
| `vendor/adobe/` | Adobe 桥接、插件、COM/CEP 资料 |
| `vendor/auditor/` | 素材审核工具 |
| `vendor/um-cli/` | Unlock Music CLI 相关资料 |

## 原则

- 上游源码尽量保持原样，便于更新和对比。
- MediaTools 自己的适配代码优先放在 `adapters/`、`modules/` 或 `services/`。
- 第三方 README、CHANGELOG、LICENSE 属于上游文档，不进入项目主文档索引。
- 对上游的本地修改应尽量通过补丁或清晰提交记录维护。
- 不把运行时产物、缓存和本机私有配置提交到 `vendor/`。

## 推荐结构

复杂第三方工具可按需采用：

```text
vendor/<tool>/
├── README.md                 # 上游或本地简要说明
├── source/                   # 上游源码
├── bin/                      # 构建产物或可执行文件
├── patches/                  # 本地补丁
└── LICENSES.txt              # 许可汇总
```

不是每个工具都必须完全匹配该结构。以可维护、可更新、可审计为准。

## 更新流程

1. 确认要更新的工具和上游来源。
2. 记录当前版本或 commit。
3. 更新上游源码或二进制。
4. 重新应用本地补丁。
5. 跑最小状态检查和相关测试。
6. 更新 `LICENSES/` 或工具说明。

## 文档边界

项目自有文档放在：

- 根 `README.md`
- `WORKFLOW.md`
- `ARCHITECTURE.md`
- `docs/`

第三方文档保留在：

- `vendor/<tool>/README.md`
- `vendor/<tool>/CHANGELOG.md`
- `vendor/<tool>/docs/`

引用第三方行为时，应注明该说明来自上游或当前本机集成。
