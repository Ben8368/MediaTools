# 补丁系统使用指南

## 📋 概述

补丁系统允许我们在保持官方源码更新的同时，维护自己的定制修改。这对于需要追新的工具（yt-dlp、FFmpeg、um-cli、capcut-mate）特别重要。

## 🎯 工作原理

```
官方源码 + 我们的补丁 = 定制版本
    ↓           ↓            ↓
  更新      重新应用      使用
```

### 补丁 + 官方源码模式的优势

1. **追踪上游更新**: 可以随时拉取官方最新代码
2. **保留定制修改**: 补丁文件记录了我们的所有修改
3. **版本控制友好**: 补丁文件小巧，易于版本控制
4. **可重现构建**: 任何人都可以从官方源码 + 补丁重建相同版本

## 📁 目录结构

每个需要补丁管理的工具都有以下结构：

```
vendor/<tool>/
├── source/              # 官方源码（git clone）
├── bin/                 # 编译后的可执行文件
├── patches/             # 我们的补丁文件
│   ├── 001-fix-encoding.patch
│   ├── 002-add-feature.patch
│   └── README.md
└── README.md
```

## 🔧 使用方法

### 1. 创建补丁

当你修改了工具的源码后，创建补丁文件：

```bash
# 在源码目录中进行修改
cd vendor/yt-dlp/source
# ... 修改代码 ...

# 创建补丁
python scripts/apply_patches.py create yt-dlp fix-encoding -d "修复中文编码问题"
```

这会创建 `vendor/yt-dlp/patches/001-fix-encoding.patch`

### 2. 应用补丁

从官方源码应用所有补丁：

```bash
# 应用单个工具的补丁
python scripts/apply_patches.py apply yt-dlp

# 检查补丁是否可以应用（不实际应用）
python scripts/apply_patches.py apply yt-dlp --dry-run
```

### 3. 列出补丁

查看所有补丁：

```bash
# 列出所有工具的补丁
python scripts/apply_patches.py list

# 列出特定工具的补丁
python scripts/apply_patches.py list yt-dlp
```

### 4. 重置源码

撤销所有补丁，恢复到官方原始状态：

```bash
python scripts/apply_patches.py reset yt-dlp
```

## 🔄 更新工作流

### 场景 1: 更新官方源码

```bash
# 1. 进入源码目录
cd vendor/yt-dlp/source

# 2. 拉取最新代码
git pull origin master

# 3. 重新应用我们的补丁
cd ../../..
python scripts/apply_patches.py apply yt-dlp

# 4. 如果补丁冲突，手动解决后重新创建补丁
# 5. 重新编译/构建
python main.py fetch ytdlp update
```

### 场景 2: 添加新的定制修改

```bash
# 1. 确保源码是最新的
cd vendor/yt-dlp/source
git pull origin master

# 2. 应用现有补丁
cd ../../..
python scripts/apply_patches.py apply yt-dlp

# 3. 进行新的修改
cd vendor/yt-dlp/source
# ... 修改代码 ...

# 4. 创建新补丁
cd ../../..
python scripts/apply_patches.py create yt-dlp new-feature -d "添加新功能"

# 5. 重新编译
python main.py fetch ytdlp update
```

### 场景 3: 修改现有补丁

```bash
# 1. 重置到原始状态
python scripts/apply_patches.py reset yt-dlp

# 2. 应用除了要修改的补丁之外的所有补丁
# （手动操作，或者删除要修改的补丁文件）

# 3. 进行修改
cd vendor/yt-dlp/source
# ... 修改代码 ...

# 4. 重新创建补丁（使用相同的名称）
cd ../../..
python scripts/apply_patches.py create yt-dlp fix-encoding -d "修复中文编码问题（更新）"

# 5. 删除旧的补丁文件，重命名新补丁
```

## 📝 补丁文件规范

### 命名规范

```
<编号>-<描述>.patch

例如:
001-fix-encoding.patch
002-add-proxy-support.patch
003-improve-error-handling.patch
```

- **编号**: 3位数字，从001开始
- **描述**: 简短的英文描述，使用连字符分隔
- **扩展名**: 必须是 `.patch`

### 补丁内容格式

```patch
# 修复中文编码问题
# 
# 原因: 默认使用 ASCII 编码导致中文乱码
# 影响: 所有包含中文的文件名和路径

diff --git a/yt_dlp/utils.py b/yt_dlp/utils.py
index 1234567..abcdefg 100644
--- a/yt_dlp/utils.py
+++ b/yt_dlp/utils.py
@@ -100,7 +100,7 @@ def sanitize_filename(s):
-    return s.encode('ascii', 'ignore').decode('ascii')
+    return s.encode('utf-8', 'ignore').decode('utf-8')
```

### patches/README.md 模板

每个工具的 patches 目录应该有一个 README.md：

```markdown
# <工具名称> 补丁说明

## 补丁列表

### 001-fix-encoding.patch
- **目的**: 修复中文编码问题
- **影响**: utils.py
- **创建日期**: 2026-04-24
- **状态**: 活跃

### 002-add-proxy-support.patch
- **目的**: 添加代理支持
- **影响**: downloader.py
- **创建日期**: 2026-04-24
- **状态**: 活跃

## 应用顺序

补丁按编号顺序应用。如果有依赖关系，请在补丁说明中注明。

## 维护说明

- 更新官方源码后，需要重新应用所有补丁
- 如果补丁冲突，需要手动解决并重新创建补丁
- 定期检查补丁是否仍然需要（官方可能已经修复）
```

## 🛡️ 最佳实践

### 1. 补丁应该小而专注

❌ 不好:
```
001-various-fixes.patch  # 包含多个不相关的修改
```

✅ 好:
```
001-fix-encoding.patch
002-add-proxy-support.patch
003-improve-error-handling.patch
```

### 2. 补丁应该有清晰的描述

每个补丁文件开头应该有注释说明：
- 修改的目的
- 修改的原因
- 影响的范围

### 3. 定期检查补丁是否仍然需要

官方可能已经修复了我们的补丁所解决的问题。定期检查：

```bash
# 1. 更新官方源码
cd vendor/yt-dlp/source
git pull origin master

# 2. 不应用补丁，直接测试
cd ../../..
python main.py fetch ytdlp status

# 3. 如果功能正常，说明补丁可能不再需要
# 4. 删除不需要的补丁
```

### 4. 版本控制补丁文件

补丁文件应该纳入版本控制：

```bash
git add vendor/*/patches/*.patch
git commit -m "Add patches for external tools"
```

### 5. 文档化补丁

在 `vendor/<tool>/README.md` 中记录：
- 当前应用的补丁
- 补丁的目的
- 最后更新时间

## 🔍 故障排查

### 补丁应用失败

```bash
# 错误信息
error: patch failed: yt_dlp/utils.py:100
error: yt_dlp/utils.py: patch does not apply
```

**解决方法**:

1. 检查官方源码是否有冲突的修改
2. 手动应用补丁内容
3. 重新创建补丁

```bash
# 1. 重置源码
python scripts/apply_patches.py reset yt-dlp

# 2. 更新源码
cd vendor/yt-dlp/source
git pull origin master

# 3. 手动应用修改
# ... 编辑文件 ...

# 4. 重新创建补丁
cd ../../..
python scripts/apply_patches.py create yt-dlp fix-encoding -d "修复中文编码问题（更新）"
```

### 补丁顺序问题

如果补丁之间有依赖关系，确保编号正确：

```bash
# 重命名补丁文件以调整顺序
mv vendor/yt-dlp/patches/003-base-feature.patch vendor/yt-dlp/patches/001-base-feature.patch
mv vendor/yt-dlp/patches/001-dependent-feature.patch vendor/yt-dlp/patches/002-dependent-feature.patch
```

## 📊 补丁管理状态

### 当前状态（2026-04-24）

| 工具 | 补丁数量 | 状态 |
|------|---------|------|
| yt-dlp | 0 | ✅ 无需补丁 |
| FFmpeg | 0 | ✅ 使用预编译版本 |
| um-cli | 0 | ✅ 无需补丁 |
| capcut-mate | 0 | ✅ 无需补丁 |

### 未来可能需要的补丁

- **yt-dlp**: 如果需要支持特定平台或添加自定义功能
- **um-cli**: 如果需要支持新的加密格式
- **capcut-mate**: 如果需要适配特定的剪映版本

## 📚 相关文档

- [VENDOR_ORGANIZATION.md](./VENDOR_ORGANIZATION.md) - Vendor 目录组织规范
- [EXTERNAL_TOOLS.md](./EXTERNAL_TOOLS.md) - 外部工具管理策略
- [scripts/apply_patches.py](../scripts/apply_patches.py) - 补丁管理脚本

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**文档版本**: v1.0
