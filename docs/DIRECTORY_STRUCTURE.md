# MediaTools 目录结构说明

## 📁 项目根目录

```
MediaTools/
├── adapters/           # 外部工具适配器
├── bin/                # 可执行文件（统一入口）
├── core/               # 核心功能（日志、验证、认证等）
├── docs/               # 项目文档
├── frontend/           # Vue 前端
├── gui/                # Gradio GUI（待废弃）
├── modules/            # 功能模块（9个）
├── patches/            # 全局补丁配置
├── projects/           # 工作区目录
├── runtime/            # 运行时状态
├── scripts/            # 工具脚本
├── services/           # 服务层
├── vendor/             # 外部工具和依赖
├── app.py              # FastAPI 服务入口
├── main.py             # CLI 入口
├── config.py           # 配置文件
└── requirements.txt    # Python 依赖
```

## 🔧 核心目录详解

### 1. adapters/ - 适配器层

隔离外部工具的实现细节。

```
adapters/
├── external_tools.py       # 外部工具基础适配器
├── ytdlp_adapter.py        # yt-dlp 适配器
├── ffmpeg_adapter.py       # FFmpeg 适配器
├── umcli_adapter.py        # um-cli 适配器
├── photoshop_runtime.py    # Photoshop 适配器
├── auditor_runtime.py      # Auditor 适配器
└── editor_runtime.py       # CapCut 适配器
```

### 2. modules/ - 功能模块（9个）

每个模块都是独立的功能单元。

```
modules/
├── fetcher/            # 媒体获取
│   ├── __init__.py
│   ├── cli.py
│   ├── downloader.py
│   ├── subtitle_handler.py
│   └── ytdlp_manager.py
│
├── encoder/            # 媒体编码
│   ├── __init__.py
│   ├── cli.py
│   └── transcoder.py
│
├── decryptor/          # 音乐解密
│   ├── __init__.py
│   ├── cli.py
│   └── wrapper.py
│
├── assets/             # 素材管理
│   ├── __init__.py
│   ├── cli.py
│   └── library.py
│
├── workbench/          # 剪辑工作台
│   ├── __init__.py
│   ├── cli.py
│   ├── analyzer.py
│   └── timeline.py
│
├── generator/          # 素材生成
│   ├── __init__.py
│   ├── cli.py
│   ├── screenshot.py
│   └── wechat_moments.py
│
├── photoshop/          # PSD 处理
│   ├── __init__.py
│   ├── cli.py
│   └── automation.py
│
├── auditor/            # 素材审核
│   ├── __init__.py
│   ├── cli.py
│   └── wrapper.py
│
└── editor/             # 剪映集成（实验性）
    ├── __init__.py
    ├── cli.py
    └── capcut_wrapper.py
```

### 3. vendor/ - 外部工具

#### 需要追新的工具（4个）

```
vendor/
├── yt-dlp/             # 视频下载引擎
│   ├── source/         # 官方源码（git clone）
│   ├── bin/            # 可执行文件
│   ├── patches/        # 我们的补丁
│   └── README.md
│
├── ffmpeg/             # 媒体处理引擎
│   ├── bin/            # 可执行文件
│   ├── patches/        # 我们的补丁
│   └── README.md
│
├── um-cli/             # 音乐解密工具
│   ├── source/         # Go 源码
│   ├── bin/            # 可执行文件
│   ├── patches/        # 我们的补丁
│   └── README.md
│
└── capcut-mate/        # 剪映自动化
    ├── (Python 源码)
    ├── patches/        # 我们的补丁
    └── README.md
```

#### 自维护工具（2个）

```
vendor/
├── auditor/            # 素材审核
│   ├── src/            # 源码
│   └── README.md
│
├── photoshop/          # PSD 处理
│   ├── src/            # 源码
│   └── README.md
│
└── atom/               # After Effects 自动化
    ├── Atom/           # CEP 扩展
    └── README.md
```

#### 归档目录

```
vendor/
└── _archived/          # 废弃模块
    ├── wechat-moments/ # 已整合到 generator
    ├── atom/           # 用途不明
    └── README.md
```

### 4. scripts/ - 工具脚本

```
scripts/
├── apply_patches.py        # 补丁管理
├── reorganize_vendor.py    # Vendor 重组
├── normalize_project.py    # 项目规范化
├── update_tools.py         # 工具更新
├── dev.py                  # 开发工具
└── build/                  # 构建脚本
    ├── build_um.ps1        # 构建 um-cli (Windows)
    ├── build_um.sh         # 构建 um-cli (Linux/Mac)
    └── README.md
```

### 5. docs/ - 文档

```
docs/
├── NAMING_CONVENTIONS.md       # 命名规范
├── DIRECTORY_STRUCTURE.md      # 本文档
├── VENDOR_ORGANIZATION.md      # Vendor 组织规范
├── PATCH_SYSTEM.md             # 补丁系统
├── EXTERNAL_TOOLS.md           # 外部工具管理
├── MODULE_DEPENDENCIES.md      # 模块依赖
├── ARCHITECTURE_OPTIMIZATION.md # 架构优化
├── PROJECT_EVALUATION.md       # 项目评估
└── IMPROVEMENTS_SUMMARY.md     # 改进总结
```

### 6. services/ - 服务层

```
services/
├── media.py            # 媒体工作流
├── agent.py            # AI Agent
├── workspace.py        # 工作区管理
├── workbench.py        # 剪辑工作台服务
└── api_server.py       # FastAPI 路由
```

### 7. core/ - 核心功能

```
core/
├── logger.py           # 日志系统
├── validation.py       # 输入验证
└── auth.py             # API 认证
```

## 📊 目录统计

### 模块数量
- **功能模块**: 9个
- **外部工具（追新）**: 4个
- **外部工具（自维护）**: 3个
- **归档模块**: 1个

### 文件类型
- **Python 模块**: ~50个
- **文档文件**: 9个
- **脚本文件**: 6个
- **配置文件**: 3个

## 🎯 命名规范

### Python 模块/包
- 使用 `snake_case`（小写+下划线）
- 例如: `fetcher`, `encoder`, `workbench`

### 外部工具目录
- 追新工具: 使用 `kebab-case`（小写+连字符）
  - 例如: `yt-dlp`, `capcut-mate`, `um-cli`
- 自维护工具: 使用 `snake_case`
  - 例如: `auditor`, `photoshop`

### 文档文件
- 使用 `UPPER_SNAKE_CASE.md`
- 例如: `NAMING_CONVENTIONS.md`, `PATCH_SYSTEM.md`

### 脚本文件
- 使用 `snake_case.py` 或 `kebab-case.sh`
- 例如: `apply_patches.py`, `build_um.ps1`

## 🔍 目录用途说明

### adapters/
**用途**: 隔离外部工具的实现细节  
**原则**: 所有外部工具调用必须通过适配器  
**好处**: 便于替换工具、统一错误处理、应用补丁

### modules/
**用途**: 功能模块，每个模块负责一个核心功能  
**原则**: 模块间低耦合、高内聚  
**结构**: 每个模块都有 `__init__.py` 和 `cli.py`

### vendor/
**用途**: 存放外部工具和依赖  
**分类**:
- 追新工具: 需要定期更新以跟进上游
- 自维护工具: 稳定版本，不需要追新
- 归档: 废弃或不再使用的模块

### scripts/
**用途**: 开发和维护工具  
**分类**:
- 补丁管理: `apply_patches.py`
- 工具更新: `update_tools.py`
- 开发工具: `dev.py`
- 构建脚本: `build/`

### services/
**用途**: 业务逻辑层，协调多个模块  
**原则**: 模块不直接相互调用，通过服务层协调  
**好处**: 降低模块间耦合度

### docs/
**用途**: 项目文档  
**分类**:
- 规范文档: 命名、目录结构
- 技术文档: 补丁系统、外部工具管理
- 评估文档: 项目评估、改进总结

## 📝 维护指南

### 添加新模块
1. 在 `modules/` 下创建新目录
2. 添加 `__init__.py` 和 `cli.py`
3. 在 `main.py` 中注册模块
4. 更新 `MODULE_DEPENDENCIES.md`

### 添加新的外部工具
1. 确定是否需要追新
2. 在 `vendor/` 下创建目录
3. 按照规范组织 `source/`, `bin/`, `patches/`
4. 创建适配器在 `adapters/`
5. 更新 `EXTERNAL_TOOLS.md`

### 更新文档
1. 修改后更新"最后更新"日期
2. 保持文档间的一致性
3. 使用 `UPPER_SNAKE_CASE.md` 命名

## 🔗 相关文档

- [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) - 命名规范
- [VENDOR_ORGANIZATION.md](./VENDOR_ORGANIZATION.md) - Vendor 组织
- [MODULE_DEPENDENCIES.md](./MODULE_DEPENDENCIES.md) - 模块依赖
- [PATCH_SYSTEM.md](./PATCH_SYSTEM.md) - 补丁系统

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**文档版本**: v1.0
