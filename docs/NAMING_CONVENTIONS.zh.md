# 命名规范

> **[English](./NAMING_CONVENTIONS.md)**

本文记录项目内推荐命名，保持 CLI、API、服务和前端概念一致。

## 模块名

使用小写单词，必要时用下划线。CLI 顶层模块保持稳定：

- `fetcher`
- `encoder`
- `decryptor`
- `assets`
- `workbench`
- `editor`
- `photoshop`
- `auditor`
- `generator`

旧别名仅用于兼容：

- `fetch`
- `encode`
- `decrypt`
- `edit`

新文档和新代码应使用规范模块名。

## Python

- 文件名：`snake_case.py`
- 函数名：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- API 路由文件：`api_<domain>_routes.py`
- 服务文件：按业务域命名，例如 `media_fetch.py`、`task_center.py`

示例：

```python
def run_fetch_analyze_slice_job(...):
    ...

class MediaAgentService:
    ...
```

## 前端

- React 组件：`PascalCase.tsx`
- hooks：`useSomething.ts`
- 普通工具：`camelCase.ts`
- 测试：与被测文件同名，后缀 `.test.ts` 或 `.test.tsx`
- 应用窗口组件：`<Name>App.tsx`

示例：

```text
DownloaderApp.tsx
WorkbenchApp.tsx
useDownloaderTaskData.ts
DownloaderTaskTable.tsx
```

## API

REST 路径使用短横线或清晰的业务名，避免暴露内部文件名。响应字段使用 JSON 常见的 `snake_case`，与后端模型保持一致。

建议：

- `/api/media/...`
- `/api/workspace/...`
- `/api/task-center/...`
- `/api/filebrowser/...`

## 工作区目录

工作区子目录使用小写复数名：

- `inputs`
- `downloads`
- `decrypted`
- `transcoded`
- `clips`
- `subtitles`
- `analysis`
- `assets`
- `imports`
- `cache`
- `logs`
- `manifests`
- `exports`

## 外部工具

工具名按上游官方写法：

- `yt-dlp`
- `FFmpeg`
- `ffmpeg`
- `ffprobe`
- `um-cli`
- `capcut-mate`
- `filebrowser`

代码中的变量名使用安全形式：

```python
ytdlp_path
ffmpeg_path
umcli_path
capcut_mate_base_url
```

## 文档

- 根入口：`README.md`
- 当前工作流：`WORKFLOW.md`
- 当前架构：`ARCHITECTURE.md`
- 专题文档：放在 `docs/`，文件名使用大写下划线或清晰小写目录。
- 第三方原文：保留在 `vendor/`，不改名以便跟随上游。
