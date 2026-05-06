# Atom After Effects 插件 - 完整能力清单

## 插件概述

**名称：** Atom  
**版本：** 3.1.1  
**类型：** CEP 11.0 插件（Common Extensibility Platform）  
**支持版本：** After Effects 22.0 - 99.0 (AE 2022+)  
**架构：** CEP Panel (HTML/JS/React) + ExtendScript (JSX)  
**通信方式：** `CSInterface.evalScript()` 调用 JSX 函数  

---

## 核心能力模块

### 1. 字体管理 (Fonts.jsx)

**功能：** 枚举 AE 中可用的字体

**API：**
- `Atom_getFontsJSON(optionsJSON)` — 主入口函数

**实现策略：**
- **AE 24+：** 使用 `app.fonts.allFonts` API（原生支持）
- **AE 旧版本：** 回退到 OS 字体 API
  - Windows: PowerShell + `System.Drawing.Text.InstalledFontCollection`
  - macOS: `/usr/bin/atsutil fonts -list`
- **混合模式（Mac）：** 合并 `app.fonts` 和 `atsutil` 结果，避免遗漏

**返回数据：**
```javascript
{
    api: "app-fonts" | "os-win" | "os-mac" | "hybrid",
    fonts: [
        {
            family: "Noto Sans",
            style: "Bold",
            postScript: "NotoSans-Bold"
        }
    ],
    count: 123,
    limited: false,
    atsutilAdded: 5  // 仅混合模式
}
```

**特性：**
- 支持查询过滤（`query` 参数）
- 支持结果限制（`limit` 参数，默认 200）
- 自动跳过替代字体（`isSubstitute`）
- 轮询非系统字体文件夹变化（AE 24.6+）

---

### 2. 项目快照管理 (Checkpoints.jsx)

**功能：** 创建/恢复/列出项目快照（类似 Git 版本管理）

**API：**
- `atom_createCheckpoint(stepMetaJson)` — 创建快照
- `atom_revertToCheckpoint(optionsJson)` — 恢复到快照
- `atom_listCheckpoints()` — 列出所有快照
- `atom_projectDirty()` — 检查项目是否有未保存修改
- `atom_saveProject()` — 保存项目

**数据结构：**

**快照记录：**
```javascript
{
    id: "A",  // 短 ID (A, B, C, ..., AA, AB, ...)
    label: "Step 1",
    stepIndex: 1,
    createdAt: "Mon, 01 Jan 2024 12:00:00 GMT",
    aeRevision: 42,  // AE 内部版本号
    checkpointPath: "/path/to/_atom_checkpoints/project_atom_step-001_1234567890.aep",
    relativePath: "_atom_checkpoints/project_atom_step-001_1234567890.aep",
    agentRunId: "run_123",  // AI Agent 运行 ID
    notes: "Before applying text changes",
    anchorMessageId: "msg_456",  // 关联的消息 ID
    scriptId: "script_789",  // 关联的脚本 ID
    branchFor: "B"  // 可选：如果是分支快照，指向原快照 ID
}
```

**清单文件（`.atom-agent.json`）：**
```javascript
{
    version: 1,
    project: {
        canonicalPath: "/path/to/project.aep",
        projectId: "proj_1234567890_123456",
        createdAt: "Mon, 01 Jan 2024 12:00:00 GMT"
    },
    checkpoints: [/* 快照记录数组 */]
}
```

**存储位置：**
- 快照文件：`_atom_checkpoints/` 目录（与主工程同级）
- 清单文件：`project_name.atom-agent.json`（与主工程同级）

**特性：**
- **原子写入：** temp → backup → rename 三步写入，防止崩溃损坏
- **智能保存：** 仅在 `project.dirty === true` 时保存，避免大工程的昂贵序列化（30-60秒）
- **分支保护：** 回滚前可自动创建当前状态的分支副本（`branchBeforeRevert: true`）
- **损坏恢复：** 检测到空清单时自动从 `.bak` 恢复
- **短 ID 生成：** 使用 base-62 编码（A-Z, a-z, 0-9）生成简短可读 ID

**工作流程：**
1. 创建快照：复制主工程 → 生成快照文件 → 更新清单
2. 回滚：（可选）创建分支 → 关闭工程 → 复制快照覆盖主工程 → 重新打开

---

### 3. AE 能力发现 (AEKnowledgeExtractorV2.jsx)

**功能：** 提取 AE 的完整能力图谱，为 AI Agent 提供操作指南

**API：**
- `CEP_Extractor.run(outDirFsName, optionsJSON)` — 执行提取

**提取内容：**

#### 3.1 图层类型样本
创建临时合成，生成所有层类型：
- Solid Layer（纯色层）
- Text Layer（文本层）
- Shape Layer（形状层）
- Null Object（空对象）
- Camera（摄像机）
- Light（灯光）
- Adjustment Layer（调整层）

#### 3.2 文本层增强
- **Path Options：** 文本路径选项
- **Text Animators：** 文本动画器
  - 3 种选择器类型：
    - Range Selector（范围选择器）
    - Wiggly Selector（摆动选择器）
    - Expressible Selector（表达式选择器）
  - 25+ 种动画属性：
    ```
    Anchor Point 3D, Position 3D, Scale 3D, Skew, Skew Axis,
    Rotation X/Y/Z, Opacity, Fill Color/Opacity/Hue/Saturation/Brightness,
    Stroke Color/Opacity/Hue/Saturation/Brightness/Width,
    Line Anchor, Track Type, Tracking Amount, Character Replace/Offset,
    Line Spacing, Blur
    ```
- **Mask Parade：** 遮罩样本

#### 3.3 形状层增强
创建 Vector Group，添加 18 种形状操作符：
```
Rectangle, Ellipse, Star, Group,
Fill, Stroke, Gradient Fill, Gradient Stroke,
Merge Paths, Offset Paths, Pucker & Bloat, Round Corners,
Trim Paths, Twist, Wiggle Paths, Wiggle Transform,
Repeater, Zig Zag
```

#### 3.4 属性树遍历
- **深度：** 最多 8 层
- **广度：** 每层最多 300 个子属性
- **提取信息：**
  ```javascript
  {
      path: "Transform > Position",
      name: "Position",
      matchName: "ADBE Position",
      valueType: "ThreeD_SPATIAL",
      dimension: 3,
      canVaryOverTime: true,  // 支持关键帧
      canSetExpression: true,  // 支持表达式
      minValue: null,
      maxValue: null,
      defaultValue: [960, 540, 0]
  }
  ```

#### 3.5 效果清单
遍历所有可用效果（Effects），提取：
- `matchName`（唯一标识符）
- `displayName`（显示名称）
- 参数范围和默认值

**输出文件：**
- `knowledge.jsonl` — 每行一个图层的属性树（JSONL 格式）
- `manifest.json` — 元数据（版本、时间戳、统计信息）

**用途：**
- 为 AI Agent 提供 AE 完整能力图谱
- 让 AI 知道可以操作哪些属性、支持哪些效果
- 动态发现 AE 版本差异

---

### 4. 日志系统 (Logger.jsx)

**功能：** 统一的日志记录和错误处理

**API：**
- `Logger.log(level, message)` — 通用日志
- `Logger.info(...)` — 信息日志
- `Logger.warn(...)` — 警告日志
- `Logger.error(...)` — 错误日志
- `Logger.testError()` — 测试错误捕获

**特性：**
- **日志文件：** 写入 `~/Library/Application Support/atom/atom.log` (Mac) 或 `%APPDATA%/atom/atom.log` (Win)
- **CEP 事件：** 通过 `com.atom-ae.jsx.log` 事件推送到 CEP 面板
- **全局错误捕获：** 劫持 `$.global.Error` 和 `$.writeln`，自动记录所有错误
- **ISO 时间戳：** 每条日志带 ISO 8601 格式时间戳
- **错误堆栈：** 捕获 `fileName` 和 `lineNumber`

---

### 5. 模态对话框桥接 (ModalBridge.jsx)

**功能：** 在 CEP 面板中显示美观的模态对话框（替代原生 `alert`/`confirm`）

**API：**
- `modalAlert(message, title)` — 警告框
- `modalConfirm(message, title)` — 确认框（返回 Promise）
- `setupModalResponseListener()` — 设置响应监听器

**实现原理：**
- JSX 通过 `com.atom-ae.jsx.modal` 事件发送请求到 CEP
- CEP 显示自定义 UI 对话框
- 用户操作后，CEP 通过 `com.atom-ae.jsx.modal.response` 事件返回结果
- JSX 通过 Promise 异步等待结果

**Toast 通知：**
- 支持批量 Toast 消息队列
- 通过 `com.atom-ae.jsx.toast` 事件推送

---

### 6. 工具函数库

#### 6.1 JSON 支持 (JSON.jsx)
- `JSON.stringify(obj)` — 序列化
- `JSON.parse(s)` — 反序列化
- `JSON.writeJSON(path, obj)` — 写入 JSON 文件
- `JSON.writeJSONL(path, records)` — 写入 JSONL 文件
- `JSON.appendJSONLRecord(path, obj)` — 追加 JSONL 记录
- `JSON.readJSON(path)` — 读取 JSON 文件

#### 6.2 ES5 Polyfills (Polyfills.jsx)
为 ExtendScript 提供现代 JS API：
- `Array.prototype.indexOf/includes/forEach/map/filter/reduce/find`
- `Array.isArray`
- `Object.keys/values/entries`

#### 6.3 UTF-8 文件读取 (Main.jsx)
- `readUtf8File(path)` — 强制 UTF-8 编码读取，避免 Windows 日文环境下的乱码

---

## 架构特性

### CEP 配置
- **Bundle ID：** `com.atom-ae.extension`
- **CSXS 版本：** 11.0
- **Node.js：** 启用（`--enable-nodejs`）
- **混合上下文：** 启用（`--mixed-context`）
- **面板类型：** Panel（主面板）+ Modeless（设置面板）

### 事件系统
- **事件前缀：** `com.atom-ae.jsx`
- **日志事件：** `com.atom-ae.jsx.log`
- **模态框事件：** `com.atom-ae.jsx.modal` / `com.atom-ae.jsx.modal.response`
- **Toast 事件：** `com.atom-ae.jsx.toast`

### 初始化流程
1. 加载 Polyfills（ES5 兼容）
2. 加载 ModalBridge（对话框）
3. 加载 JSON 支持
4. 加载 Logger（日志系统）
5. 加载 AEKnowledgeExtractorV2（能力发现）
6. 加载 Checkpoints（快照管理）
7. 加载 Fonts（字体枚举）
8. 执行 `aeCheck()`（版本检查、路径初始化）

---

## 与当前 COM 实现的对比

| 能力 | Atom 插件 | 当前 COM 实现 | 优先级 |
|---|---|---|---|
| **字体枚举** | ✅ | ❌ | 🔴 高 |
| **项目快照** | ✅ | ❌ | 🟡 中 |
| **AE 能力发现** | ✅ | ❌ | 🟢 低（AI Agent 专用） |
| **文本动画器** | ✅ | ❌ | 🟢 低（超出文本替换范畴） |
| **形状图层操作** | ✅ | ❌ | 🟢 低（不是文本工单目标） |
| **关键帧支持** | ✅ | ❌ | 🟢 低（静态文本替换不需要） |
| **表达式支持** | ✅ | ❌ | 🟢 低（静态文本替换不需要） |
| **模态对话框** | ✅ | ❌ | 🟢 低（UI 增强） |
| **日志系统** | ✅ | ❌ | 🟢 低（调试辅助） |
| **基础文本操作** | ✅ | ✅ | ✅ 已对等 |

---

## 建议补充的能力

### 🔴 高优先级：字体枚举
**理由：** PS 实现有此能力，AE 应保持一致

**实现：** 在 `ae_connector.py` 添加 `get_available_fonts()` 方法，调用 `app.fonts.allFonts` API

### 🟡 中优先级：项目快照
**理由：** 对 AI Agent 工作流有价值，执行失败后可回滚

**实现：** 在 `service.py` 添加 `create_ae_checkpoint()` / `revert_ae_checkpoint()` / `list_ae_checkpoints()`

### 🟢 低优先级：其他高级功能
**理由：** 超出文本工单范畴，暂不需要

---

## 总结

Atom 插件是一个为 **AI Agent** 设计的 AE 自动化工具，核心能力包括：

1. **字体枚举** — 让 AI 知道可用字体
2. **项目快照** — 让 AI 可以安全试错和回滚
3. **能力发现** — 让 AI 知道 AE 的完整操作空间

当前 COM 实现专注于 **人工工单流程**，核心能力（文本内容/字体/字号/tracking 修改）已完整。唯一应该补充的是**字体枚举**，以保持与 PS 实现的一致性。
