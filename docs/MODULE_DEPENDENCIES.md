# 模块依赖关系与架构优化

## 📊 模块分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    入口层 (Entry)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ main.py  │  │ app.py   │  │ scripts/             │  │
│  │  (CLI)   │  │  (Web)   │  │  (Tools)             │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   服务层 (Services)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ media.py │  │ agent.py │  │workspace │             │
│  │          │  │          │  │  .py     │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │workbench │  │api_server│  │其他服务  │             │
│  │  .py     │  │  .py     │  │          │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   模块层 (Modules)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ fetcher  │  │ encoder  │  │decryptor │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ assets   │  │workbench │  │generator │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │photoshop │  │ auditor  │  │ editor   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                  适配器层 (Adapters)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ YtdlpAdapter │ FFmpegAdapter │ UmcliAdapter │       │
│  └──────────┘  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐                            │
│  │PhotoshopAdapter │ WechatMomentsAdapter │            │
│  └──────────┘  └──────────┘                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                 外部工具层 (External)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ yt-dlp   │  │ FFmpeg   │  │ um-cli   │             │
│  │ (追新)   │  │ (追新)   │  │ (追新)   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│  ┌──────────┐  ┌──────────┐                            │
│  │capcut-mate│  │Photoshop │                           │
│  │ (追新)   │  │ (外部)   │                            │
│  └──────────┘  └──────────┘                            │
└─────────────────────────────────────────────────────────┘
```

---

## 🔗 模块依赖关系

### 核心模块（9个）

#### 1. fetcher（媒体获取）
**依赖**:
- 外部工具: `yt-dlp` ⚠️ 需追新
- 适配器: `YtdlpAdapter`, `FFmpegAdapter`
- 服务: `workspace`
- LLM: `openai` (字幕分析)

**被依赖**:
- `services/media.py`
- `services/agent.py`
- `workbench`

**解耦合状态**: ✅ 良好
- 通过适配器隔离外部工具
- 不直接依赖其他模块

---

#### 2. encoder（媒体编码）
**依赖**:
- 外部工具: `FFmpeg` ⚠️ 需追新
- 适配器: `FFmpegAdapter`
- 服务: `workspace`

**被依赖**:
- `services/media.py`
- `services/agent.py`
- `workbench`

**解耦合状态**: ✅ 良好
- 通过适配器隔离FFmpeg
- 职责单一

---

#### 3. decryptor（音乐解密）
**依赖**:
- 外部工具: `um-cli` ⚠️ 需追新
- 适配器: `UmcliAdapter`
- 服务: `workspace`

**被依赖**:
- `services/media.py`
- `services/agent.py`

**解耦合状态**: ✅ 良好
- 通过wrapper封装um-cli
- 独立性强

---

#### 4. assets（素材管理）
**依赖**:
- 服务: `workspace`
- 标准库: `pathlib`, `mimetypes`

**被依赖**:
- `services/agent.py`
- GUI层

**解耦合状态**: ✅ 优秀
- 无外部工具依赖
- 纯Python实现

---

#### 5. workbench（剪辑工作台）
**依赖**:
- 模块: `fetcher` (字幕分析)
- 模块: `encoder` (切片导出)
- 服务: `workspace`
- LLM: `openai`

**被依赖**:
- GUI层
- API层

**解耦合状态**: ⚠️ 中等
- 依赖fetcher和encoder
- 建议: 通过服务层调用，而非直接依赖

---

#### 6. generator（素材生成）✨ 重构后
**依赖**:
- 外部工具: `FFmpeg` ⚠️ 需追新
- 适配器: `FFmpegAdapter`, `WechatMomentsAdapter`
- 服务: `workspace`

**被依赖**:
- GUI层
- API层

**解耦合状态**: ✅ 良好
- 整合了截图和朋友圈生成
- 统一的素材生成接口

**子功能**:
- `screenshot.py` - 视频截图
- `wechat_moments.py` - 朋友圈图片

---

#### 7. photoshop（PSD处理）
**依赖**:
- 外部工具: `Photoshop` (外部应用)
- 适配器: `PhotoshopAutomationAdapter`
- 服务: `workspace`
- vendor: `photoshop_auto`

**被依赖**:
- GUI层
- API层

**解耦合状态**: ✅ 良好
- 通过适配器与Photoshop通信
- vendor代码独立维护

---

#### 8. auditor（素材审核）
**依赖**:
- 服务: `workspace`
- vendor: `auditor_source`

**被依赖**:
- GUI层
- API层

**解耦合状态**: ✅ 良好
- vendor代码独立
- 配置驱动

---

#### 9. editor（剪映集成）⚠️ 实验性
**依赖**:
- 外部工具: `capcut-mate` ⚠️ 需追新
- 适配器: `EditorRuntimeAdapter`
- 服务: `workspace`
- vendor: `capcut-mate`

**被依赖**:
- GUI层
- API层

**解耦合状态**: ⚠️ 实验性
- 依赖capcut-mate稳定性
- 需要持续追新

---

## 🎯 解耦合优化建议

### 已完成 ✅

1. **适配器模式**: 所有外部工具通过适配器隔离
2. **服务层抽象**: 业务逻辑集中在services/
3. **工作区统一**: 所有模块使用统一的workspace管理
4. **模块整合**: wechat_moments合并到generator

### 待优化 🔄

1. **workbench依赖优化**
   ```python
   # 当前（直接依赖）
   from modules.fetcher.analyzer import SubtitleAnalyzer
   from modules.encoder.transcoder import Transcoder
   
   # 建议（通过服务层）
   from services.media import analyze_subtitle, export_clips
   ```

2. **GUI层解耦**
   - 当前: GUI直接调用services和modules
   - 建议: 统一通过API层调用

3. **配置集中化**
   - 当前: 配置分散在各模块
   - 建议: 统一到config.py或环境变量

---

## 📦 外部工具依赖矩阵

| 模块 | yt-dlp | FFmpeg | um-cli | capcut-mate | Photoshop |
|------|--------|--------|--------|-------------|-----------|
| fetcher | ✅ 必需 | ✅ 可选 | - | - | - |
| encoder | - | ✅ 必需 | - | - | - |
| decryptor | - | - | ✅ 必需 | - | - |
| assets | - | - | - | - | - |
| workbench | - | ✅ 必需 | - | - | - |
| generator | - | ✅ 必需 | - | - | - |
| photoshop | - | - | - | - | ✅ 必需 |
| auditor | - | - | - | - | - |
| editor | - | - | - | ✅ 必需 | - |

**图例**:
- ✅ 必需: 模块核心功能依赖
- ✅ 可选: 部分功能依赖
- `-`: 无依赖

---

## 🔄 追新工具管理

### 需要追新（4个）

1. **yt-dlp** - 每2周检查
   - 影响模块: `fetcher`
   - 更新方式: `python scripts/update_tools.py --ytdlp`

2. **FFmpeg** - 每3-6月检查
   - 影响模块: `fetcher`, `encoder`, `workbench`, `generator`
   - 更新方式: 手动下载替换

3. **um-cli** - 按需检查
   - 影响模块: `decryptor`
   - 更新方式: `python main.py decrypt build`

4. **capcut-mate** - 按需检查
   - 影响模块: `editor`
   - 更新方式: `python scripts/update_tools.py --capcut`

### 自维护（其他所有）

- `photoshop_auto` - 稳定，无需追新
- `auditor_source` - 稳定，无需追新
- `wechat_moments_source` - 稳定，无需追新
- 所有Python模块 - 自有代码，自行维护

---

## 🛡️ 依赖隔离策略

### 1. 适配器模式
```python
# adapters/external_tools.py
class YtdlpAdapter:
    """隔离yt-dlp实现细节"""
    def run(self, args, context=None):
        # 应用补丁
        cmd = apply_command_patches(self.tool_name, args, context)
        return subprocess.run(cmd, ...)
```

### 2. 服务层抽象
```python
# services/media.py
def run_transcode_job(...):
    """统一的转码接口，隔离encoder模块"""
    transcoder = Transcoder()
    return transcoder.transcode(...)
```

### 3. 配置驱动
```python
# patches/tool_patches.json
{
  "ytdlp": {
    "rules": [...]
  }
}
```

---

## 📈 模块成熟度评估

| 模块 | 成熟度 | 稳定性 | 测试覆盖 | 文档完整度 |
|------|--------|--------|----------|-----------|
| fetcher | ⭐⭐⭐⭐⭐ | 高 | 中 | 高 |
| encoder | ⭐⭐⭐⭐⭐ | 高 | 中 | 高 |
| decryptor | ⭐⭐⭐⭐ | 高 | 低 | 中 |
| assets | ⭐⭐⭐⭐ | 高 | 低 | 中 |
| workbench | ⭐⭐⭐⭐ | 中 | 低 | 中 |
| generator | ⭐⭐⭐⭐ | 高 | 中 | 高 |
| photoshop | ⭐⭐⭐ | 中 | 低 | 中 |
| auditor | ⭐⭐⭐ | 中 | 低 | 中 |
| editor | ⭐⭐ | 低 | 无 | 低 |

---

## 🎯 优化路线图

### 短期（1-2周）
- [x] 合并wechat_moments到generator
- [x] 创建外部工具管理文档
- [ ] 优化workbench依赖
- [ ] 添加更多单元测试

### 中期（1-2月）
- [ ] 统一GUI通过API调用
- [ ] 配置集中化
- [ ] 完善editor模块
- [ ] 提升测试覆盖率

### 长期（3-6月）
- [ ] 插件化架构
- [ ] 模块热更新
- [ ] 分布式任务处理

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**文档版本**: v1.0
