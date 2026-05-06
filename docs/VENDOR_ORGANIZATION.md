# Vendor 目录组织规范

## 📁 目录结构

```
vendor/
├── yt-dlp/                    # yt-dlp 源码和可执行文件
│   ├── source/                # 官方源码（从 GitHub 克隆）
│   ├── bin/                   # 编译后的可执行文件
│   ├── patches/               # 我们的补丁文件
│   └── README.md              # 工具说明和更新记录
│
├── ffmpeg/                    # FFmpeg 源码和可执行文件
│   ├── source/                # 官方源码（可选）
│   ├── bin/                   # 可执行文件（ffmpeg.exe, ffprobe.exe）
│   ├── patches/               # 我们的补丁文件
│   └── README.md              # 工具说明和更新记录
│
├── um-cli/                    # Unlock Music CLI
│   ├── source/                # Go 源码（unlock-music）
│   ├── bin/                   # 编译后的可执行文件
│   ├── patches/               # 我们的补丁文件
│   └── README.md              # 工具说明和更新记录
│
├── capcut-mate/               # 剪映自动化工具
│   ├── (源码文件)             # Python 源码
│   ├── patches/               # 我们的补丁文件
│   └── README.md              # 工具说明和更新记录
│
├── photoshop_auto/            # Photoshop 自动化（自维护）
│   └── (源码文件)
│
├── auditor_source/            # 素材审核（自维护）
│   └── (源码文件)
│
├── atom/                      # After Effects 自动化（自维护）
│   └── (CEP 扩展)
│
└── wechat_moments_source/     # 朋友圈生成（自维护，已整合到 generator）
    └── (源码文件)
```

## 🎯 组织原则

### 1. 需要追新的工具（4个）

这些工具需要保留**官方源码 + 我们的补丁 + 可执行文件**：

#### yt-dlp
```
vendor/yt-dlp/
├── source/          # 从 https://github.com/yt-dlp/yt-dlp 克隆
├── bin/             # 编译后的可执行文件或下载的二进制
├── patches/         # 我们的补丁（如果有）
└── README.md        # 更新记录
```

**更新方式**:
```bash
cd vendor/yt-dlp/source
git pull origin master
# 应用补丁（如果有）
# 编译或下载最新二进制到 bin/
```

#### FFmpeg
```
vendor/ffmpeg/
├── source/          # 官方源码（可选，因为编译复杂）
├── bin/             # ffmpeg.exe, ffprobe.exe
├── patches/         # 我们的补丁（如果有）
└── README.md        # 更新记录
```

**更新方式**:
```bash
# 下载预编译版本
# Windows: https://github.com/BtbN/FFmpeg-Builds/releases
# 解压到 vendor/ffmpeg/bin/
```

#### um-cli
```
vendor/um-cli/
├── source/          # unlock-music Go 源码
├── bin/             # um-cli.exe
├── patches/         # 我们的补丁（如果有）
└── README.md        # 更新记录
```

**更新方式**:
```bash
cd vendor/um-cli/source
git pull origin master
# 应用补丁（如果有）
go build -o ../bin/um-cli.exe
```

#### capcut-mate
```
vendor/capcut-mate/
├── (Python 源码)    # 从 https://github.com/Hommy-master/capcut-mate 克隆
├── patches/         # 我们的补丁（如果有）
└── README.md        # 更新记录
```

**更新方式**:
```bash
cd vendor/capcut-mate
git pull origin main
uv sync
```

### 2. 自维护工具

这些工具是我们自己的代码或稳定的第三方库，不需要追新：

- `photoshop/` - Photoshop 自动化脚本
- `auditor/` - 素材审核源码
- `atom/` - After Effects 自动化（CEP 扩展）
- `wechat_moments_source/` - 朋友圈生成（已整合到 generator，已归档）

**管理方式**: 直接在 vendor 目录下维护源码，不需要 source/bin 分离。

## 🔄 补丁管理

### 补丁文件结构

```
vendor/<tool>/patches/
├── 001-fix-encoding.patch
├── 002-add-feature.patch
└── README.md              # 补丁说明
```

### 补丁应用流程

1. **创建补丁**:
```bash
cd vendor/<tool>/source
# 修改代码
git diff > ../patches/00X-description.patch
```

2. **应用补丁**:
```bash
cd vendor/<tool>/source
git apply ../patches/00X-description.patch
```

3. **更新时重新应用**:
```bash
cd vendor/<tool>/source
git pull origin master
# 重新应用所有补丁
for patch in ../patches/*.patch; do
    git apply "$patch"
done
```

## 📦 可执行文件管理

### bin/ 目录规范

项目根目录的 `bin/` 目录存放所有可执行文件的**符号链接或副本**：

```
bin/
├── yt-dlp.exe -> ../vendor/yt-dlp/bin/yt-dlp.exe
├── ffmpeg.exe -> ../vendor/ffmpeg/bin/ffmpeg.exe
├── ffprobe.exe -> ../vendor/ffmpeg/bin/ffprobe.exe
└── um-cli.exe -> ../vendor/um-cli/bin/um-cli.exe
```

**优点**:
- 统一的可执行文件入口
- 便于 PATH 管理
- 不影响 vendor 目录的源码组织

## 🛠️ 迁移计划

### 当前状态

```
vendor/
├── capcut-mate/           ✅ 已有源码
├── unlock-music/          ✅ 已有源码（需要重命名为 um-cli/source）
├── photoshop_auto/        ✅ 自维护
├── auditor_source/        ✅ 自维护
├── wechat_moments_source/ ✅ 自维护（已整合）
└── atom/                  ⚠️ 待确认

bin/
├── (可执行文件)           ⚠️ 需要组织
```

### 迁移步骤

#### 步骤 1: 重组 um-cli
```bash
mkdir -p vendor/um-cli/bin vendor/um-cli/patches
mv vendor/unlock-music vendor/um-cli/source
# 移动可执行文件到 vendor/um-cli/bin/
```

#### 步骤 2: 创建 yt-dlp 结构
```bash
mkdir -p vendor/yt-dlp/source vendor/yt-dlp/bin vendor/yt-dlp/patches
cd vendor/yt-dlp/source
git clone --depth 1 https://github.com/yt-dlp/yt-dlp.git .
# 移动可执行文件到 vendor/yt-dlp/bin/
```

#### 步骤 3: 创建 FFmpeg 结构
```bash
mkdir -p vendor/ffmpeg/bin vendor/ffmpeg/patches
# 移动 ffmpeg.exe 和 ffprobe.exe 到 vendor/ffmpeg/bin/
```

#### 步骤 4: 添加补丁目录
```bash
mkdir -p vendor/capcut-mate/patches
```

#### 步骤 5: 创建符号链接
```bash
# Windows (需要管理员权限)
mklink bin\yt-dlp.exe ..\vendor\yt-dlp\bin\yt-dlp.exe
mklink bin\ffmpeg.exe ..\vendor\ffmpeg\bin\ffmpeg.exe
mklink bin\ffprobe.exe ..\vendor\ffmpeg\bin\ffprobe.exe
mklink bin\um-cli.exe ..\vendor\um-cli\bin\um-cli.exe

# 或者直接复制（更简单）
copy vendor\yt-dlp\bin\yt-dlp.exe bin\
copy vendor\ffmpeg\bin\ffmpeg.exe bin\
copy vendor\ffmpeg\bin\ffprobe.exe bin\
copy vendor\um-cli\bin\um-cli.exe bin\
```

## 📝 工具 README 模板

每个工具目录下应该有一个 README.md：

```markdown
# <工具名称>

## 基本信息
- **官方仓库**: <GitHub URL>
- **用途**: <简要说明>
- **更新频率**: <每周/每月/按需>

## 目录结构
- `source/` - 官方源码
- `bin/` - 可执行文件
- `patches/` - 我们的补丁

## 更新方式
\`\`\`bash
<更新命令>
\`\`\`

## 补丁说明
- `001-xxx.patch` - <补丁说明>

## 更新历史
- 2026-04-24: 更新到版本 X.Y.Z
```

## 🎯 最佳实践

1. **源码和可执行文件分离**: 便于管理和更新
2. **补丁独立管理**: 便于追踪我们的修改
3. **统一的 bin/ 目录**: 便于 PATH 管理
4. **详细的 README**: 记录更新历史和补丁说明
5. **自动化脚本**: 使用 `scripts/update_tools.py` 自动更新

## 📚 相关文档

- [EXTERNAL_TOOLS.md](./EXTERNAL_TOOLS.md) - 外部工具管理策略
- [scripts/update_tools.py](../scripts/update_tools.py) - 自动更新脚本
- [scripts/apply_patches.py](../scripts/apply_patches.py) - 补丁应用脚本（待创建）

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**文档版本**: v1.0
