# MediaTools 架构说明

这份文档描述**当前真实项目结构**，重点解释：

1. 入口层
2. 共享服务层
3. 功能模块层
4. GUI 页面与后端 service 的映射关系
5. 当前主工作流如何串起来

本文档不描述早期方案、废弃路径或理想化设计稿，只描述现在代码中已经存在的真实结构。

---

## 一、总体架构

当前项目可以理解成 4 层：

```text
用户入口
  ├─ CLI: main.py
  └─ GUI: app.py -> gui/interface.py

共享服务层 (services/)
  ├─ 媒体工作流
  ├─ AI Agent
  ├─ 工作区管理
  ├─ 剪辑工作台服务
  └─ capcut-mate 运行时管理

模块能力层 (modules/)
  ├─ fetcher
  ├─ encoder
  ├─ decryptor
  ├─ assets
  └─ editor

基础与外部依赖层
  ├─ core/
  ├─ vendor/
  ├─ bin/
  └─ runtime/
```

关键原则：

1. `modules/` 负责底层功能能力
2. `services/` 负责跨模块串工作流
3. GUI 和 CLI 应尽量调用 `services/`，而不是各自复制业务逻辑

---

## 二、入口层

### 1. CLI 入口
文件：`main.py`

职责：

1. 解析一级模块名：
   - `fetch`
   - `encode`
   - `decrypt`
   - `assets`
   - `edit`
2. 把参数转发到对应模块 CLI

路由关系：

```text
main.py
  -> modules.fetcher.cli
  -> modules.encoder.cli
  -> modules.decryptor.cli
  -> modules.assets.cli
  -> modules.editor.cli
```

说明：

当前 CLI 仍可用，但它不是项目能力最完整的入口。很多最新链路优先在 GUI + services 中体现。

### 2. GUI 入口
文件：`app.py`

职责：

1. 解析 `host / port / share`
2. 创建 Gradio 界面
3. 启动 Web 服务

调用关系：

```text
app.py -> gui.interface.create_interface()
```

说明：

GUI 是当前项目最完整的产品入口。

---

## 三、共享服务层

目录：`services/`

这是当前项目真正的后端核心层。

### 1. `services/media.py`
职责：媒体工作流核心服务

主要能力：

1. 获取视频信息
   - `fetch_video_info(...)`

2. 批量下载
   - `run_fetch_batch(...)`
   - `run_fetch_batch_stream(...)`

3. 转码
   - `run_transcode_job(...)`

4. 单段切片
   - `run_slice_job(...)`

5. 批量切片
   - `run_batch_slice_job(...)`

6. 下载 + 分析 + 自动切片
   - `run_fetch_analyze_slice_job(...)`

7. 解密
   - `run_decrypt_job(...)`

8. 工具状态
   - `get_ytdlp_status_text()`
   - `get_ffmpeg_status_text()`
   - `get_um_status_text()`

9. 构建 um-cli
   - `build_umcli()`

这是当前最重要的服务文件。

### 2. `services/agent.py`
职责：执行型 AI Agent

主要职责：

1. OpenAI 兼容 client 封装
2. 定义可调用工具
3. 处理工具调用轨迹
4. 对高频任务做本地直连路由

当前重点支持的直连任务：

1. 下载并自动切片
2. 扫描当前项目素材
3. 解密并加入素材库

### 3. `services/workspace.py`
职责：单项目工作区管理

主要能力：

1. 获取当前工作区
   - `get_current_workspace()`
2. 设置当前工作区
   - `set_current_workspace(...)`
3. 格式化工作区显示文本
   - `format_workspace_text(...)`

当前工作区持久化到：

```text
runtime/workspace.json
```

### 4. `services/workbench.py`
职责：剪辑工作台服务

主要能力：

1. 列当前工作区素材
   - `list_workspace_media()`
2. 分析字幕生成片段建议
   - `analyze_subtitle_for_workbench(...)`
3. 从工作台批量导出 clips
   - `export_clips_from_workbench(...)`

### 5. `services/editor_runtime.py`
职责：`capcut-mate` 服务运行时管理

主要能力：

1. 检查状态
2. 启动 / 停止 / 重启
3. 读取日志
4. 维护 PID

说明：

这个 service 解决的是 `capcut-mate` 进程管理问题，不代表 editor 主链路已经完全稳定。

---

## 四、模块层

目录：`modules/`

### 1. `modules/fetcher/`
职责：媒体获取与字幕处理

关键文件：

1. `downloader.py`
   - 下载视频
   - 下载原语言字幕
   - 支持视频编码偏好
   - 支持字幕格式

2. `subtitle.py`
   - VTT 解析
   - VTT -> SRT
   - 字幕清洗与保守去重

3. `analyzer.py`
   - 调用 LLM 分析字幕亮点
   - 输出结构化片段与中文简介

4. `csv_manager.py`
   - 下载记录 CSV 管理

5. `ytdlp_manager.py`
   - `yt-dlp` 下载 / 更新 / 状态

### 2. `modules/encoder/`
职责：FFmpeg 媒体处理

关键文件：

1. `transcoder.py`
   - H.264 / H.265 转码
   - 音频提取
   - 单段切片
   - 字幕烧录切片

### 3. `modules/decryptor/`
职责：解密加密音频

关键文件：

1. `wrapper.py`
   - 单文件解密
   - 批量目录解密
   - 状态检测

### 4. `modules/assets/`
职责：素材扫描与索引

关键文件：

1. `library.py`
   - 扫描媒体文件
   - 搜索
   - 统计

说明：

当前更像“工作区扫描器”，不是完整数据库型素材库。

### 5. `modules/editor/`
职责：`capcut-mate` 适配

关键文件：

1. `adapter.py`
   - HTTP 调用 `capcut-mate`

说明：

这是实验链路，当前不是项目最稳定的主生产链路。

---

## 五、基础与依赖层

### 1. `core/`

#### `core/ffmpeg.py`
职责：

1. FFmpeg 路径管理
2. 版本读取
3. 通用 FFmpeg 命令执行

#### `core/logger.py`
职责：

1. 简单日志配置

### 2. `vendor/`

1. `vendor/capcut-mate/`
2. `vendor/unlock-music/`

说明：

这些是第三方源码，不是项目自有后端核心。

### 3. `bin/`

存放外部二进制：

1. `ffmpeg`
2. `ffprobe`
3. `yt-dlp`
4. `um-cli`

### 4. `runtime/`

存放运行时状态：

1. `workspace.json`
2. `capcut-mate.pid`
3. `capcut-mate.log`
4. `youtube_videos.csv`

---

## 六、GUI 页面与后端映射

### 1. 总览页
文件：`gui/tabs/dashboard.py`

对应服务：

1. `services.editor_runtime`
2. `services.media` 工具状态接口
3. `services.workspace`

### 2. 媒体获取
文件：`gui/tabs/fetcher.py`

对应服务：

1. `run_fetch_batch_stream(...)`
2. `fetch_video_info(...)`
3. `CSVManager`

### 3. 媒体编码
文件：`gui/tabs/encoder.py`

对应服务：

1. `run_transcode_job(...)`
2. `run_slice_job(...)`

### 4. 音乐解密
文件：`gui/tabs/decryptor.py`

对应服务：

1. `run_decrypt_job(...)`
2. `build_umcli()`

### 5. 素材管理
文件：`gui/tabs/assets.py`

对应服务：

1. `get_current_workspace()`
2. `set_current_workspace(...)`
3. `AssetLibrary`

### 6. 剪辑工作台
文件：`gui/tabs/workbench.py`

对应服务：

1. `list_workspace_media()`
2. `analyze_subtitle_for_workbench(...)`
3. `export_clips_from_workbench(...)`

### 7. 剪映剪辑
文件：`gui/tabs/editor.py`

对应服务：

1. `services.editor_runtime`
2. `modules.editor.adapter`
3. `run_slice_job(...)`（FFmpeg 备选切片）

### 8. AI 助手
文件：`gui/tabs/agent.py`

对应服务：

1. `MediaAgentService`

说明：

AI 助手是全局浮窗，不是单独 tab。

---

## 七、当前主工作流

### 主工作流 1：下载 -> 分析 -> 自动切片

```text
媒体获取 / AI 助手
  -> 下载视频
  -> 下载原语言字幕
  -> 转换成可分析字幕
  -> LLM 分析亮点
  -> 生成片段建议
  -> 自动扩边
  -> FFmpeg 精确切片
  -> 导出带原字幕 clips
```

关键函数：

```text
run_fetch_analyze_slice_job(...)
```

这是当前最关键、最稳定的自动化生产链路。

### 主工作流 2：工作台编辑

```text
剪辑工作台
  -> 查看当前工作区视频/字幕
  -> 分析字幕
  -> 得到片段建议
  -> 时间轴概览查看
  -> 微调开始/结束/中文简介/原文
  -> 批量导出 clips
```

关键函数：

```text
analyze_subtitle_for_workbench(...)
export_clips_from_workbench(...)
```

### 主工作流 3：解密并入素材库

```text
音乐解密 / AI 助手
  -> run_decrypt_job(...)
  -> 识别输出产物
  -> 加入当前项目素材库
```

---

## 八、当前最重要的真实能力

当前项目后端已经具备：

1. 视频下载
2. 原语言字幕下载
3. 字幕分析
4. 批量切片
5. 自动扩边
6. 原字幕烧录导出
7. 工作区管理
8. 素材扫描
9. 解密并入素材库
10. AI 助手执行链路
11. 剪辑工作台支撑

---

## 九、当前主要限制

1. `capcut-mate` 仍属实验链路
2. CLI 和 GUI 的能力同步还没完全收口
3. 素材库更像工作区扫描器，不是数据库型资产系统
4. 工作台已具备简化时间轴，但还不是完整 NLE
5. 项目仍缺自动化测试

---

## 十、维护建议

后续若继续扩展，请优先遵守：

1. 先把新能力做进 `services/`
2. 再分别接 GUI 和 CLI
3. 避免在 GUI 事件函数里复制业务逻辑
4. 所有新的“下载 -> 分析 -> 切片 -> 导出”流程优先走工作区模型
