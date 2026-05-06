# 工具路线和集成状态

本文说明 MediaTools 中几条外部工具路线的定位。它不是产品路线承诺，只用于判断当前应该优先依赖哪条链路。

## 总览

| 路线 | 当前定位 | 稳定性 | 主要入口 |
|---|---|---|---|
| FFmpeg + yt-dlp | 核心生产主线 | 高 | `fetcher`, `encoder`, `workbench` |
| AI 字幕分析 | 核心增强能力 | 中高，取决于模型和字幕 | `services/agent*`, `modules/fetcher/analyzer.py` |
| Adobe / Photoshop / After Effects | 专业软件自动化扩展 | 环境相关 | `modules/adobe`, `services/api_adobe_routes.py`, `services/api_photoshop_routes.py` |
| capcut-mate / CapCut | 实验剪辑联动 | 中低 | `modules/editor`, `services/editor_runtime.py` |
| auditor | 素材审核扩展 | 环境相关 | `modules/auditor`, `services/auditor.py` |
| filebrowser | 文件管理扩展 | 中 | `modules/filebrowser`, `services/filebrowser_runtime.py` |

## 推荐主线

日常可稳定依赖的链路是：

```text
yt-dlp 下载
-> 字幕清洗/分析
-> FFmpeg 切片或转码
-> 工作台复核
-> 工作区素材管理
```

这条路线的优点：

- 不依赖大型桌面软件
- 容易测试和排查
- CLI 和 Web 都能复用
- 失败时通常能通过日志和命令行复现

## Adobe 路线

适合：

- Photoshop 批量处理
- After Effects 工程扫描、票据化修改和执行
- 本机已安装并配置 Adobe 软件的专业工作流

特点：

- 能力强，但强依赖本机软件、权限、插件和版本。
- COM/ExtendScript/CEP 的细节应隔离在 Adobe 模块和 runtime 里。
- 相关专题见 `docs/adobe/`。

当前主要代码：

- `modules/adobe/`
- `modules/photoshop/`
- `services/api_adobe_routes.py`
- `services/api_photoshop_routes.py`
- `adapters/adobe_runtime.py`
- `adapters/photoshop_runtime.py`
- `adapters/after_effects_runtime.py`

## CapCut / capcut-mate 路线

适合：

- 快速剪辑实验
- 研究 CapCut/剪映自动化
- 非核心生产链路的辅助导出

当前限制：

- 上游接口和本机环境变化较多。
- 自动化稳定性不如 FFmpeg 主线。
- 不建议作为唯一导出路径。

当前主要代码：

- `modules/editor/`
- `services/editor_runtime.py`
- `vendor/capcut-mate/`

## 选择建议

- 只需要下载、分析、切片：选 FFmpeg + yt-dlp。
- 需要专业图像或 AE 工程处理：选 Adobe 路线。
- 需要探索剪映联动：使用 capcut-mate，但保留 FFmpeg 备选。
- 需要审查素材合规或质量：使用 auditor。
- 需要浏览、预览和整理工作区文件：使用内置文件管理和 filebrowser。

## 文档边界

- 当前实现状态以 `ARCHITECTURE.md` 和代码为准。
- 第三方工具自身能力以 `vendor/` 中上游文档为准。
- 本文只说明 MediaTools 对这些工具的集成定位。
