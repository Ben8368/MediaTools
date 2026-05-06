# After Effects 能力对比：Atom 插件 vs COM 实现

## 架构差异

| 维度 | Atom 插件 | 当前 COM 实现 |
|---|---|---|
| **通信方式** | CEP 11.0 + ExtendScript (插件内嵌) | COM + ExtendScript (外部进程) |
| **运行环境** | AE 内部面板（Node.js + React） | Python 外部进程 |
| **调用方式** | `CSInterface.evalScript()` | `AfterFX.Application.DoScript()` |
| **生命周期** | 随 AE 启动/关闭 | 按需连接/断开 |

---

## 功能对比

### ✅ 当前 COM 实现已有的能力

| 功能 | Atom | COM | 说明 |
|---|---|---|---|
| 打开/保存工程 | ✅ | ✅ | |
| 扫描文本图层 | ✅ | ✅ | |
| 修改文本内容 | ✅ | ✅ | |
| 修改字体 | ✅ | ✅ | |
| 修改字号 | ✅ | ✅ | |
| 修改 Tracking | ✅ | ✅ | |

---

### ❌ Atom 有但 COM 实现缺失的能力

#### 1. **字体枚举** (Fonts.jsx)
**Atom 实现：**
```javascript
// AE 24+ 使用 app.fonts.allFonts API
var families = app.fonts.allFonts;
for (var i = 0; i < families.length; i++) {
    for (var j = 0; j < families[i].length; j++) {
        var f = families[i][j];
        fonts.push({
            family: f.familyName,
            style: f.styleName,
            postScript: f.postScriptName
        });
    }
}
```

**影响：** 当前 COM 实现无法列出 AE 中可用的字体，用户需要手动输入 PostScript 字体名。

**优先级：** 🔴 高 — 这是 PS 实现有但 AE 缺失的核心能力

---

#### 2. **项目快照/检查点** (Checkpoints.jsx)
**Atom 实现：**
- 原子写入快照：`mainFile.copy(checkpointFile)`
- 清单管理：`.atom-agent.json` 记录所有快照
- 回滚支持：`atom_revertToCheckpoint()` 可恢复到任意快照
- 分支保护：回滚前可自动创建当前状态的分支副本

**数据结构：**
```javascript
{
    id: "A",  // 短 ID (A, B, C, ...)
    label: "Step 1",
    stepIndex: 1,
    createdAt: "2024-01-01T12:00:00Z",
    aeRevision: 42,
    checkpointPath: "/path/to/_atom_checkpoints/project_atom_step-001_1234567890.aep",
    agentRunId: "run_123",
    notes: "Before applying text changes",
    anchorMessageId: "msg_456",
    scriptId: "script_789"
}
```

**影响：** 当前 COM 实现无法管理工程版本历史，执行失败后无法回滚。

**优先级：** 🟡 中 — 对 AI Agent 工作流很重要，但对基础文本替换不是必需

---

#### 3. **AE 能力发现** (AEKnowledgeExtractorV2.jsx)
**Atom 实现：**
- 创建临时合成，生成所有层类型样本（solid、text、shape、null、camera、light、adjustment）
- 递归遍历属性树（深度 8 层，最多 300 子属性）
- 提取所有 effect 的 `matchName`、`displayName`、参数范围
- 输出 `knowledge.json`（层类型+属性）、`manifest.json`（元数据）

**用途：** 为 AI Agent 提供 AE 完整能力图谱，让 AI 知道可以操作哪些属性。

**影响：** 当前 COM 实现只能操作已知的文本属性，无法动态发现 AE 的其他能力。

**优先级：** 🟢 低 — 这是 AI Agent 专用功能，对人工工单流程不需要

---

#### 4. **文本动画器** (Text Animators)
**Atom 实现：**
```javascript
// 添加 Path Options
var pathOptions = textProps.addProperty('ADBE Text Path Options');

// 添加 Text Animator
var animator = animators.addProperty('ADBE Text Animator');

// 添加选择器（3 种类型）
selectors.addProperty('ADBE Text Range Selector 2');  // Range Selector
selectors.addProperty('ADBE Text Wiggly Selector 2'); // Wiggly Selector
selectors.addProperty('ADBE Text Expressible Selector 2'); // Expression Selector

// 添加动画属性（25+ 种）
animProps.addProperty('ADBE Text Anchor Point 3D');
animProps.addProperty('ADBE Text Position 3D');
animProps.addProperty('ADBE Text Scale 3D');
animProps.addProperty('ADBE Text Rotation');
// ... 等 20+ 种
```

**影响：** 当前 COM 实现无法操作文本动画器，只能改文本内容/字体/字号。

**优先级：** 🟢 低 — 文本动画是高级功能，基础工单流程不需要

---

#### 5. **形状图层操作** (Shape Layer)
**Atom 实现：**
- 创建 Vector Group
- 添加 18 种形状操作符：矩形、椭圆、星形、填充、描边、渐变填充、渐变描边、合并路径、偏移路径、圆角、修剪路径、扭曲、摆动路径、摆动变换、中继器、扭曲变换、Pucker & Bloat、Zig Zag

**影响：** 当前 COM 实现完全不支持形状图层。

**优先级：** 🟢 低 — 形状图层不是文本工单的目标

---

#### 6. **关键帧支持**
**Atom 实现：**
- 检测属性是否支持关键帧：`canVaryOverTime`
- 检测属性是否支持表达式：`canSetExpression`

**影响：** 当前 COM 实现只能设置静态值，无法操作关键帧动画。

**优先级：** 🟢 低 — 关键帧动画不是文本替换的目标

---

#### 7. **3D 变换**
**Atom 实现：**
- Position 3D (x, y, z)
- Rotation X/Y/Z
- Orientation

**影响：** 当前 COM 实现无法操作 3D 属性。

**优先级：** 🟢 低 — 3D 变换不是文本工单的目标

---

#### 8. **渲染队列访问**
**Atom 实现：**
- 通过 Effect Parade 访问渲染队列
- 可以添加/修改渲染项

**影响：** 当前 COM 实现无法操作渲染队列（但可以通过 `app.project.renderQueue` 访问，只是没实现）。

**优先级：** 🟡 中 — 渲染是 AE 自动化的重要环节，但当前工单流程不需要

---

## 优先级建议

### 🔴 高优先级（应该补充）

1. **字体枚举** — 对标 PS 的 `get_available_weights()`
   - 实现：在 `ae_connector.py` 添加 `get_available_fonts()` 方法
   - JSX 脚本：调用 `app.fonts.allFonts` (AE 24+) 或 OS 字体 API (旧版本)
   - 用途：让用户可以从下拉列表选择字体，而不是手动输入 PostScript 名

### 🟡 中优先级（可选补充）

2. **项目快照** — 对标 Git 的版本管理
   - 实现：在 `service.py` 添加 `create_checkpoint()` / `revert_to_checkpoint()` / `list_checkpoints()`
   - 用途：执行前自动快照，失败后可回滚
   - 注意：需要处理大文件（.aep 可能几百 MB）

3. **渲染队列** — 完整的 AE 自动化闭环
   - 实现：在 `ae_connector.py` 添加 `add_to_render_queue()` / `start_render()`
   - 用途：修改文本后自动渲染输出视频

### 🟢 低优先级（暂不需要）

4. **AE 能力发现** — AI Agent 专用
5. **文本动画器** — 超出文本替换范畴
6. **形状图层** — 不是文本工单目标
7. **关键帧/表达式** — 静态文本替换不需要
8. **3D 变换** — 不是文本工单目标

---

## 实现建议

### 立即补充：字体枚举

```python
# ae_connector.py
def get_available_fonts(self, query: str = "", limit: int = 200) -> list[dict[str, str]]:
    """
    枚举 AE 中可用的字体
    返回 [{"family": str, "style": str, "postScript": str}, ...]
    """
    script = f"""
    var query = "{query}";
    var limit = {limit};
    var families = app.fonts.allFonts;
    var out = [];
    for (var i = 0; i < families.length; i++) {{
        for (var j = 0; j < families[i].length; j++) {{
            var f = families[i][j];
            if (f.isSubstitute) continue;
            var ps = f.postScriptName || "";
            if (query && ps.toLowerCase().indexOf(query.toLowerCase()) === -1) continue;
            out.push({{
                family: f.familyName || "",
                style: f.styleName || "",
                postScript: ps
            }});
            if (out.length >= limit) break;
        }}
        if (out.length >= limit) break;
    }}
    JSON.stringify(out);
    """
    raw = self.app.DoScript(script)
    import json
    return json.loads(raw) if raw else []
```

### 可选补充：项目快照

```python
# service.py
def create_ae_checkpoint(
    ticket_id: str,
    label: str = "",
    workspace: dict | None = None,
) -> dict[str, Any]:
    """创建工程快照"""
    # 实现类似 Atom 的 atom_createCheckpoint
    pass

def revert_ae_checkpoint(
    checkpoint_id: str,
    workspace: dict | None = None,
) -> dict[str, Any]:
    """回滚到快照"""
    # 实现类似 Atom 的 atom_revertToCheckpoint
    pass
```

---

## 总结

**当前 COM 实现的核心能力（文本内容/字体/字号/tracking 修改）已经完整**，与 Atom 插件在基础文本替换上是对等的。

**主要缺失：**
1. **字体枚举** — 这是唯一应该立即补充的功能，对标 PS 实现
2. **项目快照** — 对 AI Agent 工作流有价值，但对人工工单流程不是必需
3. **其他高级功能**（动画器、形状、关键帧等）— 超出文本工单范畴，暂不需要

**建议：** 先补充字体枚举，让 AE 实现与 PS 实现在核心能力上完全对等。项目快照可以作为后续增强功能。
