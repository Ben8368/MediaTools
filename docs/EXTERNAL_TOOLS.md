# 外部工具管理策略

## 📋 工具分类

### 🔄 需要追新的工具（4个）

这些工具需要定期更新以跟进平台变化和功能改进。

#### 1. yt-dlp
**用途**: 视频下载引擎  
**更新频率**: 约每14天一个版本  
**更新原因**: 
- 平台反爬策略变化
- 新平台支持
- Bug修复

**管理方式**:
- 使用独立二进制（`bin/yt-dlp.exe`）
- 通过 `YtdlpManager` 管理
- 支持自更新：`yt-dlp -U`

**更新命令**:
```bash
# 自动更新
python scripts/update_tools.py --ytdlp

# 手动更新
python main.py fetch ytdlp update
```

**版本检查**:
```bash
python main.py fetch ytdlp status
```

---

#### 2. capcut-mate
**用途**: 剪映自动化  
**更新频率**: 不定期（跟随剪映更新）  
**更新原因**:
- 剪映API变化
- 新功能支持
- Bug修复

**管理方式**:
- Git子模块方式（`vendor/capcut-mate/`）
- 从上游仓库拉取：https://github.com/Hommy-master/capcut-mate

**更新命令**:
```bash
# 自动更新
python scripts/update_tools.py --capcut

# 手动更新
cd vendor/capcut-mate
git pull origin main
uv sync
```

**版本检查**:
```bash
python main.py editor status
```

**注意事项**:
- ⚠️ 当前为实验性功能
- 更新前建议备份（自动备份到 `vendor/capcut-mate.backup/`）
- 更新后需要运行 `uv sync` 安装依赖

---

#### 3. um-cli (Unlock Music CLI)
**用途**: 音乐解密  
**更新频率**: 不定期  
**更新原因**:
- 新加密格式支持
- 解密算法改进
- Bug修复

**管理方式**:
- Go源码编译（`vendor/unlock-music/`）
- 编译产物：`bin/um-cli.exe`

**更新命令**:
```bash
# 重新编译
python main.py decrypt build

# 或使用脚本
.\scripts\build-um.ps1  # Windows
./scripts/build-um.sh   # Linux/macOS
```

**版本检查**:
```bash
python main.py decrypt status
```

**注意事项**:
- 需要Go 1.21+环境
- 编译时间约1-2分钟
- 源码位于 `vendor/unlock-music/`

---

#### 4. FFmpeg
**用途**: 媒体处理引擎  
**更新频率**: 约每3-6个月  
**更新原因**:
- 新编码器支持
- 性能优化
- Bug修复

**管理方式**:
- 独立二进制（`bin/ffmpeg.exe`, `bin/ffprobe.exe`）
- 手动下载更新

**更新方式**:
```bash
# Windows
# 1. 下载最新版本：https://github.com/BtbN/FFmpeg-Builds/releases
# 2. 解压 ffmpeg.exe 和 ffprobe.exe 到 bin/ 目录

# Linux
sudo apt update && sudo apt upgrade ffmpeg

# macOS
brew upgrade ffmpeg
```

**版本检查**:
```bash
bin/ffmpeg -version
# 或
python main.py encode status
```

**推荐版本**: FFmpeg 6.0+

---

## 🔒 不需要追新的工具（自维护）

这些是项目自有代码或稳定的第三方库，可以维护自己的分支。

### 核心模块（自有代码）
- `modules/fetcher/` - 视频下载逻辑
- `modules/encoder/` - 转码切片逻辑
- `modules/decryptor/` - 解密封装
- `modules/assets/` - 素材管理
- `modules/workbench/` - 剪辑工作台
- `modules/generator/` - 素材生成
- `modules/photoshop/` - PSD处理
- `modules/auditor/` - 素材审核

### 服务层（自有代码）
- `services/media.py` - 媒体工作流
- `services/agent.py` - AI Agent
- `services/workspace.py` - 工作区管理
- `services/api_server.py` - FastAPI服务

### 第三方库（通过pip管理）
- `fastapi` - Web框架
- `openai` - LLM客户端
- `pydantic` - 数据验证
- 其他Python依赖

**管理方式**:
- 版本锁定在 `requirements.txt`
- 仅在需要新功能时手动升级
- 升级前充分测试

---

## 🔄 更新流程

### 自动更新（推荐）

```bash
# 更新所有需要追新的工具
python scripts/update_tools.py

# 仅更新特定工具
python scripts/update_tools.py --ytdlp
python scripts/update_tools.py --capcut
```

### 手动更新

#### yt-dlp
```bash
python main.py fetch ytdlp update
```

#### capcut-mate
```bash
cd vendor/capcut-mate
git pull origin main
uv sync
cd ../..
python main.py editor status  # 验证
```

#### um-cli
```bash
python main.py decrypt build
```

#### FFmpeg
手动下载并替换 `bin/ffmpeg.exe` 和 `bin/ffprobe.exe`

---

## 📊 更新检查清单

### 每周检查
- [ ] yt-dlp 版本（平台变化频繁）

### 每月检查
- [ ] capcut-mate 更新（如果使用editor模块）
- [ ] FFmpeg 版本

### 按需检查
- [ ] um-cli（新加密格式出现时）
- [ ] Python依赖（安全漏洞或新功能需求）

---

## 🛡️ 更新安全策略

### 更新前
1. ✅ 备份当前版本
2. ✅ 查看更新日志
3. ✅ 在测试环境验证

### 更新中
1. ✅ 使用自动更新脚本（自动备份）
2. ✅ 记录更新日志

### 更新后
1. ✅ 运行测试套件
2. ✅ 验证核心功能
3. ✅ 更新文档

---

## 📝 版本记录

### 当前版本（2026-04-24）

| 工具 | 版本 | 状态 |
|------|------|------|
| yt-dlp | 2026.03.17 | ✅ 最新 |
| capcut-mate | - | ⚠️ 需检查 |
| um-cli | - | ✅ 稳定 |
| FFmpeg | - | ✅ 稳定 |

### 更新历史

```
2026-04-24: yt-dlp 更新到 2026.03.17
2026-04-24: 创建外部工具管理策略文档
```

---

## 🔧 故障排查

### yt-dlp 下载失败
```bash
# 1. 更新到最新版本
python scripts/update_tools.py --ytdlp

# 2. 检查网络连接
# 3. 查看错误日志
```

### capcut-mate 启动失败
```bash
# 1. 检查依赖
cd vendor/capcut-mate
uv sync

# 2. 查看日志
python main.py editor status
```

### um-cli 编译失败
```bash
# 1. 检查Go版本
go version  # 需要 1.21+

# 2. 清理缓存重新编译
python main.py decrypt build
```

### FFmpeg 未找到
```bash
# 1. 检查文件是否存在
ls bin/ffmpeg.exe bin/ffprobe.exe

# 2. 重新下载
# Windows: https://github.com/BtbN/FFmpeg-Builds/releases
```

---

## 📚 相关文档

- [QUICKSTART.md](../QUICKSTART.md) - 快速开始指南
- [scripts/update_tools.py](../scripts/update_tools.py) - 自动更新脚本
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 架构设计文档

---

## 🎯 最佳实践

1. **定期更新**: 每周检查yt-dlp，每月检查其他工具
2. **自动化优先**: 使用 `scripts/update_tools.py` 而非手动更新
3. **测试验证**: 更新后运行测试套件验证功能
4. **版本记录**: 在 `CHANGELOG.md` 中记录重要更新
5. **备份策略**: 更新前自动备份（脚本已实现）

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**文档版本**: v1.0
