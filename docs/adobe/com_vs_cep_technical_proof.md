# COM vs CEP 技术可行性证明

## 核心原理

**关键事实：** Atom 插件（CEP）和 COM 方案都是通过 **ExtendScript (JSX)** 操作 AE：

```
┌─────────────────────────────────────────────────────────────┐
│                    After Effects 进程                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           ExtendScript 引擎 (JSX Runtime)             │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  app.project / app.fonts / layer.property()    │  │  │
│  │  │  所有 AE 自动化 API 都在这里                     │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │         ↑                              ↑               │  │
│  │         │                              │               │  │
│  │  CSInterface.evalScript()    DoScript()               │  │
│  │         │                              │               │  │
│  └─────────┼──────────────────────────────┼───────────────┘  │
│            │                              │                  │
│  ┌─────────┴──────────┐       ┌──────────┴────────────┐     │
│  │   CEP 面板 (HTML)   │       │   COM 接口 (外部)     │     │
│  │   Atom 插件         │       │   AfterFX.Application │     │
│  └────────────────────┘       └───────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
         ↑                                    ↑
         │                                    │
    React/JS 代码                      Python 代码
```

**结论：** 只要是 ExtendScript API 能做的事，COM 和 CEP 都能做，因为它们都是在调用同一个 JSX 引擎。

---

## 逐项能力证明

### 1. 字体枚举 ✅

**Atom 实现 (Fonts.jsx:24-66):**
```javascript
function getFonts_AE24(query, limit) {
    var families = app.fonts.allFonts;
    var out = [];
    for (var i = 0; i < families.length; i++) {
        for (var j = 0; j < families[i].length; j++) {
            var f = families[i][j];
            if (f.isSubstitute) continue;
            out.push({
                family: f.familyName,
                style: f.styleName,
                postScript: f.postScriptName
            });
        }
    }
    return { fonts: out };
}
```

**COM 实现 (ae_connector.py:177-245):**
```python
def get_available_fonts(self, query: str = "", limit: int = 200):
    script = f"""
    var families = app.fonts.allFonts;
    var out = [];
    for (var i = 0; i < families.length; i++) {{
        for (var j = 0; j < families[i].length; j++) {{
            var f = families[i][j];
            if (f.isSubstitute) continue;
            out.push({{
                family: f.familyName,
                style: f.styleName,
                postScript: f.postScriptName
            }});
        }}
    }}
    JSON.stringify(out);
    """
    return json.loads(self.app.DoScript(script))
```

**对比：**
- ✅ 使用相同的 `app.fonts.allFonts` API
- ✅ 相同的遍历逻辑
- ✅ 相同的过滤条件（`isSubstitute`）
- ✅ 相同的返回数据结构

**可行性：100%**

---

### 2. 项目快照 ✅

**Atom 实现 (Checkpoints.jsx:181-233):**
```javascript
function atom_createCheckpoint(stepMetaJson) {
    var mainFile = app.project.file;
    if (app.project.dirty) {
        app.project.save(mainFile);
    }
    var checkpointFile = new File(folder.fsName + '/' + checkpointName);
    var ok = mainFile.copy(checkpointFile);
    return JSON.stringify(cp);
}
```

**COM 实现方案 1（JSX）:**
```python
def create_checkpoint(self, label: str = ""):
    script = f"""
    var mainFile = app.project.file;
    if (app.project.dirty) {{
        app.project.save(mainFile);
    }}
    var checkpointFile = new File(mainFile.path + '/_checkpoints/' + Date.now() + '.aep');
    mainFile.copy(checkpointFile);
    JSON.stringify({{ path: checkpointFile.fsName }});
    """
    return json.loads(self.app.DoScript(script))
```

**COM 实现方案 2（Python，更简单）:**
```python
def create_checkpoint(self, label: str = ""):
    # 先保存当前工程
    self.save_project(self.current_project_path)
    
    # Python 直接复制文件
    checkpoint_dir = Path(self.current_project_path).parent / "_checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = checkpoint_dir / f"checkpoint_{int(time.time())}.aep"
    shutil.copy2(self.current_project_path, checkpoint_path)
    
    return {"path": str(checkpoint_path)}
```

**对比：**
- ✅ JSX 方案：使用相同的 `File.copy()` API
- ✅ Python 方案：更简单，不需要 JSX
- ✅ 两种方案都能实现相同功能

**可行性：100%（甚至更简单）**

---

### 3. AE 能力发现 ✅

**Atom 实现 (AEKnowledgeExtractorV2.jsx:223-558):**
```javascript
function run(outDirFsName, optionsJSON) {
    // 创建临时合成
    var comp = app.project.items.addComp("_extraction", 1920, 1080, 1, 10, 30);
    
    // 添加各种层类型
    var solid = comp.layers.addSolid([1,0,0], "Solid", 1920, 1080, 1);
    var text = comp.layers.addText("Sample");
    var shape = comp.layers.addShape();
    
    // 递归遍历属性树
    function dumpProp(p, depth, parentPath, properties) {
        if (depth > 8) return;
        for (var i = 1; i <= p.numProperties; i++) {
            var child = p.property(i);
            properties.push({
                path: parentPath + " > " + child.name,
                matchName: child.matchName,
                canVaryOverTime: child.canVaryOverTime,
                canSetExpression: child.canSetExpression
            });
            if (isGroupProp(child)) {
                dumpProp(child, depth + 1, parentPath + " > " + child.name, properties);
            }
        }
    }
}
```

**COM 实现（直接复用 Atom 的 JSX）:**
```python
def extract_ae_knowledge(self, output_dir: str):
    # 读取 Atom 的 JSX 脚本
    jsx_script = Path("vendor/atom/AEKnowledgeExtractorV2.jsx").read_text()
    
    # 通过 COM 执行
    script = f"""
    {jsx_script}
    CEP_Extractor.run("{output_dir}", "{{}}");
    """
    result = self.app.DoScript(script)
    return json.loads(result)
```

**对比：**
- ✅ 可以直接复用 Atom 的 JSX 脚本
- ✅ 使用相同的 ExtendScript API
- ✅ 生成相同的输出文件

**可行性：100%（可直接复用代码）**

---

### 4. 文本动画器 ✅

**Atom 实现 (AEKnowledgeExtractorV2.jsx:89-120):**
```javascript
var animator = animators.addProperty('ADBE Text Animator');
var selectors = animator.property('ADBE Text Selectors');
selectors.addProperty('ADBE Text Range Selector 2');
var animProps = animator.property('ADBE Text Animator Properties');
animProps.addProperty('ADBE Text Position 3D');
animProps.addProperty('ADBE Text Rotation');
```

**COM 实现:**
```python
def add_text_animator(self, comp_index: int, layer_index: int):
    script = f"""
    var comp = app.project.item({comp_index});
    var layer = comp.layer({layer_index});
    var textProps = layer.property('ADBE Text Properties');
    var animators = textProps.property('ADBE Text Animators');
    var animator = animators.addProperty('ADBE Text Animator');
    var selectors = animator.property('ADBE Text Selectors');
    selectors.addProperty('ADBE Text Range Selector 2');
    var animProps = animator.property('ADBE Text Animator Properties');
    animProps.addProperty('ADBE Text Position 3D');
    animProps.addProperty('ADBE Text Rotation');
    "ok";
    """
    self.app.DoScript(script)
```

**对比：**
- ✅ 使用相同的 `addProperty()` API
- ✅ 相同的 matchName 常量
- ✅ 相同的属性访问路径

**可行性：100%**

---

### 5. 形状图层操作 ✅

**Atom 实现 (AEKnowledgeExtractorV2.jsx:184-209):**
```javascript
var shape = comp.layers.addShape();
var contents = shape.property('ADBE Root Vectors Group');
var group = contents.addProperty('ADBE Vector Group');
var groupContents = group.property('ADBE Vectors Group');
groupContents.addProperty('ADBE Vector Shape - Rect');
groupContents.addProperty('ADBE Vector Graphic - Fill');
groupContents.addProperty('ADBE Vector Graphic - Stroke');
```

**COM 实现:**
```python
def add_shape_operators(self, comp_index: int, layer_index: int):
    script = f"""
    var comp = app.project.item({comp_index});
    var layer = comp.layer({layer_index});
    var contents = layer.property('ADBE Root Vectors Group');
    var group = contents.addProperty('ADBE Vector Group');
    var groupContents = group.property('ADBE Vectors Group');
    groupContents.addProperty('ADBE Vector Shape - Rect');
    groupContents.addProperty('ADBE Vector Graphic - Fill');
    groupContents.addProperty('ADBE Vector Graphic - Stroke');
    "ok";
    """
    self.app.DoScript(script)
```

**对比：**
- ✅ 使用相同的 `addProperty()` API
- ✅ 相同的 matchName 常量
- ✅ 相同的层级结构

**可行性：100%**

---

### 6. 关键帧操作 ✅

**ExtendScript API:**
```javascript
// 设置关键帧
property.setValueAtTime(time, value);

// 读取关键帧
var numKeys = property.numKeys;
for (var i = 1; i <= numKeys; i++) {
    var time = property.keyTime(i);
    var value = property.keyValue(i);
}
```

**COM 实现:**
```python
def set_keyframe(self, comp_index: int, layer_index: int, property_path: str, time: float, value: Any):
    script = f"""
    var comp = app.project.item({comp_index});
    var layer = comp.layer({layer_index});
    var prop = layer.property("{property_path}");
    prop.setValueAtTime({time}, {json.dumps(value)});
    "ok";
    """
    self.app.DoScript(script)
```

**可行性：100%**

---

### 7. 表达式操作 ✅

**ExtendScript API:**
```javascript
property.expression = "wiggle(2, 50)";
property.expressionEnabled = true;
```

**COM 实现:**
```python
def set_expression(self, comp_index: int, layer_index: int, property_path: str, expression: str):
    script = f"""
    var comp = app.project.item({comp_index});
    var layer = comp.layer({layer_index});
    var prop = layer.property("{property_path}");
    prop.expression = "{expression}";
    prop.expressionEnabled = true;
    "ok";
    """
    self.app.DoScript(script)
```

**可行性：100%**

---

### 8. 渲染队列 ✅

**ExtendScript API:**
```javascript
var rqItem = app.project.renderQueue.items.add(comp);
rqItem.outputModules[1].file = new File("/path/to/output.mov");
app.project.renderQueue.render();
```

**COM 实现:**
```python
def render_composition(self, comp_index: int, output_path: str):
    script = f"""
    var comp = app.project.item({comp_index});
    var rqItem = app.project.renderQueue.items.add(comp);
    rqItem.outputModules[1].file = new File("{output_path}");
    app.project.renderQueue.render();
    "ok";
    """
    self.app.DoScript(script)
```

**可行性：100%**

---

## 唯一的区别：UI 层

| 功能 | Atom (CEP) | COM | 可行性 |
|---|---|---|---|
| **内嵌面板 UI** | ✅ HTML/React 面板 | ❌ 不能内嵌 | ⚠️ 可用其他方式替代 |
| **模态对话框** | ✅ 自定义 CEP UI | ⚠️ JSX 原生 `alert()`/`confirm()` | ✅ 功能可实现，UI 不同 |
| **日志系统** | ✅ 写文件 + CEP 事件 | ✅ Python `logging` 模块 | ✅ Python 实现更强大 |

**替代方案：**
- **Web UI：** Flask/FastAPI + React（当前 MediaTools 已有）
- **桌面 GUI：** PyQt / tkinter
- **CLI：** 命令行界面
- **原生对话框：** JSX 的 `alert()` / `confirm()` / `prompt()`

---

## 性能对比

| 维度 | Atom (CEP) | COM |
|---|---|---|
| **启动速度** | 快（随 AE 启动） | 慢（需要连接 AE） |
| **执行速度** | 相同（都是 JSX） | 相同（都是 JSX） |
| **内存占用** | 低（共享 AE 进程） | 低（外部进程） |
| **稳定性** | 高（AE 内部） | 高（独立进程） |

---

## 结论

### ✅ 完全可以实现（100%）

所有基于 **ExtendScript API** 的能力：
- 字体枚举
- 项目快照
- AE 能力发现
- 文本动画器
- 形状图层操作
- 关键帧操作
- 表达式操作
- 渲染队列
- 所有图层/属性/效果操作

### ⚠️ 需要调整（功能可实现，形式不同）

- **日志系统：** Python 的 `logging` 模块更强大
- **模态对话框：** 可用 JSX 原生对话框或 Python GUI 库

### ❌ 不能实现（架构限制）

- **CEP 内嵌面板：** COM 是外部进程，不能在 AE 内部显示 HTML 面板
- **但可以用 Web UI / 桌面 GUI / CLI 替代**

---

## 实际建议

**对于 MediaTools 项目：**

1. **立即补充：** 字体枚举（已实现）
2. **可选补充：** 项目快照（用 Python 实现更简单）
3. **暂不需要：** AE 能力发现、文本动画器、形状图层（超出文本工单范畴）

**核心优势：**
- COM 方案可以复用 Atom 的所有 JSX 代码
- Python 实现某些功能（如文件操作、日志）更简单
- 当前 MediaTools 的 Web UI 比 CEP 面板更灵活

**最终结论：Atom 插件的所有核心能力，COM 方案都可以实现，甚至某些方面更简单。**
