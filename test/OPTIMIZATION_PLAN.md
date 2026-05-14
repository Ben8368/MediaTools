# PS 自适应算法优化方案 — 最终版

---

## 前置知识

### 单位关系
- **72 是物理常量**：1 inch ≡ 72 points（排版学定义，与文档无关）
- `px = pt × dpi / 72`（`pt_to_px` 已实现）
- `pt = px × 72 / dpi`（`px_to_pt` 已实现）

### 字体名差异
- `font.Name` → 显示名，如 `"Noto Sans Regular"`（空格分隔，`ti.Font` **不接受**）
- `font.PostScriptName` → PS 名，如 `"NotoSans-Regular"`（连字符，`ti.Font` **接受**）
- 当前 bug：用 `font.Name` 赋值 `ti.Font` → PS 静默忽略 → 字体不生效

### 多样式文字层
- Photoshop 文字层可以有多个 TextRange，各有独立字号/字体/颜色
- `ti.Font`/`ti.Size` 只返回第一个 Range 的值
- 算法只能赋一种统一格式 → 破坏原始多格式设计 → 应跳过

---

## Round 1 基线数据

| 指标 | 数值 | 判定 |
|------|------|------|
| 文字还原 | 0 错 (100%) | 🟢 |
| 高度偏差 | 0.9px avg | 🟢 |
| 字号偏差 | 10.23% avg | 🔴 |
| 字间距偏差 | 50.5 avg | 🔴 |
| 字体还原 | 19/20 不匹配 | 🔴 全部变成 AdobeHeitiStd |
| 路径匹配 | 20/52 (38%) | 🟡 |

根因：`build_font_index()` 用显示名当 PS 名 → Step2 `ti.Font = "Noto Sans Regular"` 无效 → 全部回退默认字体 → 字号/字间距连锁偏差。

---

## Fix 1: 字体索引健壮化

### 涉及文件
`vendor/adobe/photoshop/com/src/font_resolver.py`
`vendor/adobe/photoshop/com/src/psa_applier.py`

### 1a. `build_font_index()` — 改用 PostScriptName

当前（第 64 行）:
```python
ps_name = font.Name    # 显示名，"Noto Sans Regular"
```

改为:
```python
try:
    ps_name = font.PostScriptName    # PS 名，"NotoSans-Regular"
except Exception:
    ps_name = font.Name              # 回退显示名
display_name = font.Name             # 保留显示名备用
```

`FontEntry` 新增字段 `display_name: str`。

### 1b. `apply_params_to_layer()` — 字体赋值失败时重试

当前:
```python
try:
    ti.Font = params.font_ps
except Exception as e:
    logger.log_error(...)
```

改为:
```python
try:
    ti.Font = params.font_ps    # PostScriptName
except Exception:
    try:
        ti.Font = params.display_name    # 显示名重试
    except Exception as e:
        logger.log_error(...)
```

### 1c. 字体名规范化辅助函数

新增 `_normalize_font_name(name: str) -> str`，统一处理：
- `"Noto Sans Regular"` ↔ `"NotoSans-Regular"`（空格 vs 连字符）
- `"NotoSansRegular"` ↔ `"Noto Sans Regular"`（无分隔符）

---

## Fix 2: Lab 文档复用 + 扩大 + 居中

### 涉及文件
`adaptive_lab.py`, `text_modifier.py`, `psa_applier.py`, `smart_object_handler.py`, `test/roundtrip_test.py`

### 2a. `adaptive_lab.py` — 尺寸扩大 + clear() + 居中

**尺寸**: `1000, 1000` → `4096, 4096`（构造函数参数，默认 4096）

**新增 `clear()` 方法**:
```python
def clear(self):
    """删除 lab 中所有图层，保留文档供复用"""
    try:
        for layer in list(self._doc.ArtLayers):
            layer.Delete()
    except Exception:
        pass
```

**`_create_text_layer()` 居中**:
```python
lab_layer = doc.ArtLayers.Add()
lab_layer.Kind = 2
# ... 设置字体、大小、内容 ...
# 居中到画布中央
half_w = self._doc_width / 2    # 默认 2048
half_h = self._doc_height / 2   # 默认 2048
bounds = lab_layer.Bounds
w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
lab_layer.Translate(half_w - w/2 - bounds[0], half_h - h/2 - bounds[1])
```

### 2b. 调用方 — 按 DPI 分组复用 Lab

`test/roundtrip_test.py` 的 `apply_changes()` 函数：

**当前逻辑**（每层一个 Lab）:
```python
with LabDocument(ps.app, dpi) as lab:
    for r in direct:
        process_layer(ps.app, doc, r, lab, logger)
```

**改为按 DPI 分组**:
```python
# 收集所有层及其所在文档的 DPI
layers_by_dpi = {}  # {dpi: [(doc, record), ...]}
for r in direct:
    layers_by_dpi.setdefault(dpi, []).append((doc, r))
for so_group in so_groups:
    so_dpi = ...  # SO 文档的分辨率
    layers_by_dpi.setdefault(so_dpi, []).extend(so_group_records)

# 每组 DPI 创建一个 Lab，复用
for group_dpi, items in layers_by_dpi.items():
    with LabDocument(ps.app, group_dpi) as lab:
        for doc, record in items:
            # 确认 DPI 匹配
            actual_dpi = float(safe_get(doc, "Resolution", 72.0))
            if abs(actual_dpi - group_dpi) > 0.1:
                continue  # 跳过 DPI 不匹配的（不应出现）
            process_layer(ps.app, doc, record, lab, logger)
            lab.clear()  # 清空 lab 供下一层复用
```

**`process_layer()` 需适配**: 不再在内部操作 Lab 的开关，只使用传入的 lab 对象（当前已符合）。

### 2c. `smart_object_handler.py` `process_so_level()` — 同样改造

接收外部传入的 lab（或内部按 DPI 创建），不再每层创建新 lab。

---

## Fix 3: 多样式文字层检测与跳过

### 涉及文件
`document_scanner.py`, `text_models.py`, `psa_applier.py`

### 3a. `text_models.py` — TextLayerRecord 新增字段

```python
@dataclass
class TextLayerRecord:
    # ... 现有字段 ...
    multi_style: bool = False  # 新增：文字层包含多种格式
```

`to_dict()` / `from_dict()` 对应增加此字段。

### 3b. `document_scanner.py` — `_extract_text_record()` 检测

在提取文字属性后，检测是否为多样式：

```python
# 检测多样式文字层
multi_style = False
try:
    # 方法1: Photoshop COM TextItem.Runs
    runs = ti.Runs
    if runs.Count > 1:
        multi_style = True
except Exception:
    try:
        # 方法2: 检查是否能稳定读取 Font（多样式层常抛异常）
        test_font = ti.Font
        test_size = ti.Size
        # 如果能读到但值不一致，仍可能多样式
        # 启发式: 多行且行间文本长度差异 > 5x
        lines = text.split('\r')
        if len(lines) > 1:
            lens = [len(l.strip()) for l in lines if l.strip()]
            if lens and max(lens) > min(lens) * 5:
                multi_style = True
    except Exception:
        multi_style = True  # 读属性失败，很可能是多样式
```

传给 `TextLayerRecord`:
```python
return TextLayerRecord(
    # ... 现有字段 ...
    multi_style=multi_style,
)
```

### 3c. `psa_applier.py` — `process_layer()` 跳过逻辑

函数开头增加判断：
```python
def process_layer(app, doc, record, lab, logger, in_so=False):
    if record.multi_style:
        logger.log_warning(
            f"SKIP multi-style layer [{record.layer_path}]: "
            f"layer has multiple text formatting ranges, cannot safely modify"
        )
        return None
    # ... 原有逻辑 ...
```

---

## Fix 4: 字号初始预估加速

### 涉及文件
`adaptive_algorithm.py`, `adaptive_lab.py`

### 4a. `adaptive_lab.py` — `find_adapted_params()` 计算预估

在 Phase 1 之前计算初始预估：
```python
# 预估: 新字体大致需要的字号
# hint_pt = orig_size_pt × (target_h_px / orig_bounds_h_px)
# 虽然换字体后相同 pt 渲染高度不同，但比例相近，起点远优于固定 72pt
hint_pt = record.size_pt * (target_h / max(record.bounds_h_px, 1.0))
hint_pt = max(1.0, min(500.0, hint_pt))  # 夹紧到合法范围
```

传入 Phase 1:
```python
last_mid = phase1_binary_search(
    ti, get_h, target_h, iterations_log, logger,
    initial_hint=hint_pt
)
```

### 4b. `adaptive_algorithm.py` — `phase1_binary_search()` 支持 hint

新增参数 `initial_hint: float = 72.0`:

```python
def phase1_binary_search(ti, get_h, target_h, iterations_log,
                         logger=None, initial_hint=72.0):
    # 用预估缩小搜索范围
    lo = max(1.0, initial_hint * 0.25)
    hi = min(500.0, initial_hint * 4.0)
    last_mid = initial_hint  # 起点改为预估，而非固定 72
    # ... 后续二分逻辑不变 ...
```

若 hint=72（默认值），行为与原来完全一致（向后兼容）。

---

## 修改文件清单

| # | 文件 | 改动 | 行数估计 |
|---|------|------|---------|
| 1 | `font_resolver.py` | PostScriptName + display_name + 规范化 | ~15 |
| 2 | `psa_applier.py` | `ti.Font` 重试 + 多样式跳过 + `display_name` 传递 | ~20 |
| 3 | `adaptive_lab.py` | 4096×4096 + clear() + 居中 + hint 计算 | ~25 |
| 4 | `document_scanner.py` | 多样式检测（Runs.Count / 启发式） | ~20 |
| 5 | `text_models.py` | `multi_style` 字段 + to_dict/from_dict | ~10 |
| 6 | `adaptive_algorithm.py` | `phase1_binary_search` 支持 `initial_hint` | ~8 |
| 7 | `text_modifier.py` | `modify_text_layer` 传 `display_name` | ~5 |
| 8 | `smart_object_handler.py` | `process_so_level` Lab 复用 | ~15 |
| 9 | `test/roundtrip_test.py` | `apply_changes` 按 DPI 分组 + `layer_id` 比对 | ~30 |

## 不修改
- `C:\PSA\*` — 参考源，永不动
- `ps_connector.py` — TypeUnits 与本次无关
- `execution.py` — 执行管线不动
- `adaptive_algorithm.py` Phase 2/3 — R2 数据出来再定
- `ticket_workflow.py` — 本次测试不走 ticket 路径

---

## 验证（Round 2 期望）

| 指标 | R1 | R2 目标 |
|------|-----|---------|
| 字体还原 | 1/20 | **20/20** |
| 字号偏差 | 10.23% | **< 5%** |
| 字间距偏差 | 50.5 | **< 25** |
| 高度偏差 | 0.9px | 保持 |
| 文字还原 | 100% | 保持 |
| 路径匹配 | 38% | **100%**（改用 layer_id） |
| 多样式层 | 被错误修改 | **正确跳过** |
| Lab 创建次数 | 52 | **~2-4** |
| Phase1 迭代 | ~10 | **~5-6** |
