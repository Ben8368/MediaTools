# PS 模块自适应算法优化开发文档

> 基于 test 目录往返测试数据（round1/round2）分析，提炼出三个可落地的纯算法优化方向。
> 不依赖任何缓存数据库，所有优化均通过算法逻辑实现，对未见字体同样有效。
>
> **测试背景**：test.psd 含 52 个文字层，往返流程 = 镜像文本 + 换字体 → 再次镜像 + 还原字体，比对原始参数。
> Round 1 问题根因已由 OPTIMIZATION_PLAN.md 解决；本文档针对 Round 2 仍存在的问题。

---

## Round 2 残留问题总结

| 指标 | Round 2 实测 | 期望 |
|------|-------------|------|
| Phase 1 平均迭代次数 | 8~11 次 | 4~6 次 |
| 字号偏差（rt vs orig） | 平均 10.08% | < 5% |
| Tracking 偏差 | 平均 24.61 | < 15 |
| SO 内 Lab 文档 | 每 DPI 组 1 个，但 process_so_level 内部仍各自创建 | 统一复用 |
| multi_style 检测 | 仅过滤了颜色无关样式，未区分"纯颜色多样式" | 更精确 |

---

## 优化一：Phase 1 初始预估改进（减少迭代次数）

### 问题定位

**文件**：`adaptive_lab.py`，`find_adapted_params()` 方法，第 159~175 行

```python
# 当前代码（第 159~175 行）
self._activate()
lab_layer, ti = self._create_text_layer(
    new_font_ps, new_text, 72.0, record.tracking, record.auto_leading, record.leading_pt
)

def get_h() -> float:
    return self._get_h(lab_layer)

def get_w() -> float:
    return self._get_w(lab_layer)

# Phase 1: binary search on size
# Compute initial size hint: orig_size × (target_h / orig_bounds_h)
hint_pt = record.size_pt * (target_h / max(record.bounds_h_px, 1.0))
hint_pt = max(1.0, min(500.0, hint_pt))
last_mid = phase1_binary_search(ti, get_h, target_h, iterations_log, logger,
                                initial_hint=hint_pt)
```

**文件**：`adaptive_algorithm.py`，`phase1_binary_search()` 函数，第 12~43 行

```python
# 当前代码
def phase1_binary_search(ti, get_h, target_h: float, iterations_log: list[str],
                         logger=None, initial_hint: float = 72.0) -> float:
    lo = max(1.0, initial_hint * 0.25)
    hi = min(500.0, initial_hint * 4.0)
    last_mid = initial_hint
    _safety = False
    for i in range(1, 11):
        mid = (lo + hi) / 2.0   # ← 问题在这里：第一次不用 hint，直接用 lo/hi 的中点
        try: ti.Size = mid
        except Exception: pass
        ...
```

### 根因分析

从日志提取的典型案例：

```
# 案例 1：按钮/Learn more（orig=92.26pt，target=19px）
hint_pt = 92.26 × (19/30) = 58.4pt
实际 lo=14.6, hi=232.9 → 第一次 mid=(14.6+232.9)/2 = 123.8pt → 产生 89px（偏离 4.7x）
最终收敛 ~26.8pt，需要 11 次迭代

# 案例 2：1080P High-Bitrate...（orig=108.93pt，target=43px）  
hint_pt 计算 = 108.93 × (43/43) = 108.9pt（target_h_override 是 lab 空间的值）
但由于 scale≈0.39，target_h_lab = 110px
hint = 108.93 × (110/43) = 278pt → 范围 [69.5, 500] → 第一次 mid=284pt → 281px（偏离 2.6x）
```

**核心问题有两个**：

1. `hint_pt` 计算中用的是 `record.size_pt * (target_h / record.bounds_h_px)`，但 `target_h` 在 `find_adapted_params()` 内部是经过 `scale` 修正后的 `target_h_lab`，而 `record.bounds_h_px` 是真实文档的像素高度。这两个量的坐标系不同（实际文档 vs Lab 文档），导致 hint 严重偏高。

2. 在 `phase1_binary_search()` 中，`last_mid = initial_hint` 但第一次迭代用的是 `mid = (lo + hi) / 2.0`，即 hint 只影响搜索范围，第一次尝试的值是区间中点而不是 hint 本身——这让 hint 的价值大打折扣。

### 优化方案

**Step 1**：修正 `find_adapted_params()` 中的 hint 计算，用 Lab 坐标系的量：

```python
# 在 adaptive_lab.py 的 find_adapted_params() 中
# 位置：Phase 1 调用之前（当前第 169~175 行）

# 原有代码
hint_pt = record.size_pt * (target_h / max(record.bounds_h_px, 1.0))
hint_pt = max(1.0, min(500.0, hint_pt))

# 修改为：先在 lab 中用原始参数测量一次高度，以此为基准做比例预估
# 注意：这次测量使用新字体（new_font_ps），而非原字体
# 原因：我们想预估的是新字体在 target_h_lab 所需的字号
# 先用 record.size_pt 测量新字体的实际高度 → 得到 font_native_h
# 再做比例：hint_pt = record.size_pt × (target_h / font_native_h)
try:
    font_native_h = lab.measure_text(
        font_ps=new_font_ps,
        contents=new_text,
        size_pt=record.size_pt,          # 沿用原始字号作为探针
        tracking=record.tracking,
        auto_leading=record.auto_leading,
        leading_pt=record.leading_pt,
    )
    if font_native_h > 0.5:
        hint_pt = record.size_pt * (target_h / font_native_h)
    else:
        hint_pt = record.size_pt * (target_h / max(record.bounds_h_px, 1.0))
except Exception:
    hint_pt = record.size_pt * (target_h / max(record.bounds_h_px, 1.0))
hint_pt = max(1.0, min(500.0, hint_pt))
```

**重要**：`lab.measure_text()` 会调用 `_create_text_layer()` 再 `Delete()`，执行完后 lab 内没有残留图层，不影响后续的 `_create_text_layer()`（用于 Phase 1）。但要注意：此时 `self._activate()` 已经在第 158 行调用过，`measure_text()` 内部也会调用 `_activate()`，两次切换 active document 没有副作用。

**Step 2**：修改 `phase1_binary_search()`，让第一次迭代直接用 hint 而非区间中点：

```python
# 在 adaptive_algorithm.py 的 phase1_binary_search() 中
# 完整函数替换

def phase1_binary_search(ti, get_h, target_h: float, iterations_log: list[str],
                         logger=None, initial_hint: float = 72.0) -> float:
    lo = max(1.0, initial_hint * 0.25)
    hi = min(500.0, initial_hint * 4.0)
    last_mid = initial_hint
    _safety = False
    for i in range(1, 11):
        if i == 1:
            mid = initial_hint   # ← 第一次直接用 hint，而不是区间中点
        else:
            mid = (lo + hi) / 2.0
        try: ti.Size = mid
        except Exception: pass
        last_mid = mid
        h = get_h()
        if logger:
            logger.log_iteration(i, "size", mid, h, target_h)
        log_entry = f"[iter {i:02d} size] tried={mid:.4f} → h={h:.2f}px  target={target_h:.2f}px"
        iterations_log.append(log_entry)
        if h < target_h:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < 2.0 or (h > 0 and abs(h - target_h) / target_h < 0.04):
            if _safety:
                break
            _safety = True
    return last_mid
```

### 预期效果与原理

`measure_text()` 用新字体在 `record.size_pt` 下实际渲染一次，得到 `font_native_h`。无论目标字体的 x-height、ascender 比例如何，这个测量值都是准确的实物依据——不依赖任何字体度量数据库，对未见字体同样有效。

根据 Round 2 日志测算：
- `按钮/Learn more`：hint 从 58.4pt 修正为约 26pt，第一次迭代直接命中附近区间，迭代从 11 次降至约 4 次
- `1080P High-Bitrate...`：hint 从 278pt 修正为约 120pt 范围内的合理值，迭代从 9 次降至约 5 次

**代价**：每个图层多 1 次 `measure_text()`（约 0.5~1 秒），换来 3~5 次 Phase 1 迭代（每次约 2~3 秒）。净节省约 5~10 秒/层。

---

## 优化二：Tracking 偏差的算法改进

### 问题定位

**文件**：`adaptive_algorithm.py`，`phase3_tracking()` 函数，第 247~392 行

Round 2 仍有较大 tracking 偏差（平均 24.61），分析原因：

```
# 从 round2_comparison.json 提取的典型案例

层: Input/Text/Video
  orig_tracking=18 → rt_tracking=72（偏差 +54）
  orig_size_pt=50 → rt_size_pt=46.6（字号缩小了 6.8%）

层: 进度条/97%
  orig_tracking=20 → rt_tracking=77（偏差 +57）
  orig_size_pt=56.66 → rt_size_pt=56.3（字号几乎不变）

层: BT/Learn more
  orig_tracking=20 → rt_tracking=52（偏差 +32）
```

**根因**：phase3_tracking() 的目标是让新字体的文本宽度匹配原字体（`orig_w`）。但往返测试中发生了两次字体互换，第二次换回来的字体（Noto）渲染宽度与原始 Noto 宽度本应一致，但 tracking 被算法主动调整了。

看当前 phase3 的逻辑（第 267~279 行）：

```python
# 当前代码（phase3_tracking 内部）
if orig_w > 1.0 and not tracking_adjustment_failed:
    lo_t = current_tracking - 50   # ← 在当前 tracking ±50 范围内搜索
    hi_t = current_tracking + 50
    for _ in range(5):
        mid_t = (lo_t + hi_t) / 2.0
        try: ti.Tracking = mid_t
        except Exception: pass
        w_test = get_w()
        if w_test < orig_w:
            lo_t = mid_t
        else:
            hi_t = mid_t
    current_tracking = (lo_t + hi_t) / 2.0
```

问题在于 `lo_t = current_tracking - 50, hi_t = current_tracking + 50`：搜索范围以「当前 tracking」为中心，但当前 tracking 是原始文档扫描出来的 `record.tracking`（如 20），因此搜索范围是 [-30, 70]。当字体换了之后新字体宽度若比原字体窄，算法会把 tracking 增大到 70+，远超原始值 20。

### 优化方案

**核心思想**：在 phase3 开始之前，先用原始 tracking 测量一次新字体宽度。如果新字体在原始 tracking 下宽度已经接近原始宽度（误差 < 10px），就不做 tracking 调整，直接保持原始值。只有当宽度差异较大时，才启动搜索——且搜索范围应以「原始 tracking」为锚点，而不是以「当前 tracking」为中心。

**文件**：`adaptive_algorithm.py`，修改 `phase3_tracking()` 函数

```python
# 当前函数签名（第 247 行）
def phase3_tracking(ti, get_h, get_w, phase2_h: float, orig_w: float,
                    record, last_mid: float, is_multiline: bool,
                    iterations_log: list[str], logger=None) -> Phase3Result:

# 函数开头，在 current_tracking = record.tracking 之后插入以下逻辑
# （位置：第 254 行之后）

    current_tracking = record.tracking
    best_tracking = current_tracking
    best_tracking_diff = float('inf')
    tracking_adjustment_failed = False
    width_hard_clamped = False

    # ↓↓↓ 新增：先测量原始 tracking 下新字体的宽度，判断是否需要调整
    if orig_w > 1.0:
        try:
            # 将 ti 的 tracking 设为原始值，测量宽度
            ti.Tracking = record.tracking
            w_at_orig_tracking = get_w()
            w_diff_at_orig = abs(w_at_orig_tracking - orig_w)
            log_entry = (
                f"[phase3 pre-check] tracking={record.tracking:.1f} "
                f"-> w={w_at_orig_tracking:.2f}px orig_w={orig_w:.2f}px "
                f"diff={w_diff_at_orig:.2f}px"
            )
            iterations_log.append(log_entry)

            if w_diff_at_orig < 10.0:
                # 原始 tracking 下宽度已足够接近，直接返回，不做调整
                log_entry = (
                    f"[phase3 skip] width diff {w_diff_at_orig:.2f}px < 10px, "
                    f"keeping original tracking={record.tracking:.1f}"
                )
                iterations_log.append(log_entry)
                return Phase3Result(record.tracking, last_mid, False, False)
        except Exception:
            pass
    # ↑↑↑ 新增结束

    _safety = False
    for track_iter in range(1, 6):
        try:
            current_size = float(safe_get(ti, "Size", last_mid) or last_mid)
            new_w = get_w()

            # ↓ 关键修改：搜索范围以 record.tracking（原始值）为锚，而非 current_tracking
            if orig_w > 1.0 and not tracking_adjustment_failed:
                anchor = record.tracking          # ← 原来是 current_tracking
                lo_t = anchor - 100              # ← 原来是 current_tracking - 50
                hi_t = anchor + 100              # ← 原来是 current_tracking + 50
                # 以下搜索逻辑不变
                for _ in range(5):
                    mid_t = (lo_t + hi_t) / 2.0
                    try: ti.Tracking = mid_t
                    except Exception: pass
                    w_test = get_w()
                    if w_test < orig_w:
                        lo_t = mid_t
                    else:
                        hi_t = mid_t
                current_tracking = (lo_t + hi_t) / 2.0
                current_tracking = max(-100, min(200, current_tracking))
                try: ti.Tracking = current_tracking
                except Exception: pass
            # ↑ 修改结束，后续代码不变
```

### 为什么这样改

1. **Pre-check 逻辑**：若新字体在原始 tracking 下宽度就对，说明两种字体的字形宽度接近，不需要调整。这是最理想的情况，直接跳过 phase3 的循环，既节省时间又避免无谓的 tracking 漂移。

2. **锚点从 current_tracking 改为 record.tracking**：`current_tracking` 在第一次迭代时等于 `record.tracking`，但后续迭代中会被更新为上一次搜索的结果。以原始值为锚点，保证每次迭代都在「原始 tracking 的合理邻域」内搜索，而不是越漂越远。搜索范围从 ±50 扩大到 ±100 是为了弥补范围调整带来的覆盖损失。

3. **不改变其他逻辑**：width_hard_clamped、tracking_adjustment_failed 的判断、Step 2 的 size 缩减逻辑均保持不变，这些是正确的兜底机制。

---

## 优化三：process_so_level 内部的 Lab 文档复用

### 问题定位

**文件**：`smart_object_handler.py`，`process_so_level()` 函数，第 82~120 行

当前代码（第 104~107 行）：

```python
if direct_here:
    with LabDocument(app, dpi) as lab:
        for r in direct_here:
            _process_layer_func(app, doc, r, lab, logger, in_so=True)
```

这段代码对 `direct_here` 列表里的图层复用了 1 个 Lab——这是好的。但问题出在**递归调用**部分（第 109~末尾）：

```python
for nkey, ngroup in nested.items():
    # ...找到 so_layer，enter_smart_object...
    try:
        so_doc = enter_smart_object(app, so_layer)
        so_dpi = float(safe_get(so_doc, "Resolution", dpi))
        process_so_level(app, so_doc, ngroup, logger, so_dpi, depth + 1,
                         _process_layer_func)  # ← 每个嵌套 SO 组都会递归进入，内部又创建新 Lab
```

每个 `nested` 分组在下一层 `process_so_level` 调用时会再次执行 `with LabDocument(app, dpi) as lab`。在有多个 SO 组的情况下，虽然每个 SO 组内部复用，但组间并不共享。

从 Round 2 日志可以观察到：
```
Creating LabDocument(DPI=72.0) for 41 work items   ← roundtrip_test.py 层面的 Lab
```
而 `process_so_level` 内部的 Lab 创建没有被日志记录，因为是在 `_process_layer_func`（即 `process_layer`）内部通过 `LabDocument` context manager 创建的。

实际上，roundtrip_test.py 已经在外层按 DPI 分组创建了 Lab 并传入 `process_layer`（直接层），但对于 SO 内的层，调用路径是：

```
roundtrip_test.py → process_so_level → _process_layer_func(app, doc, r, lab, ...) 
                                                                    ↑
                                         这里的 lab 是 process_so_level 内部创建的
```

`process_so_level` 传入的 `_process_layer_func` 就是 `process_layer`，`process_layer` 本身接受 `lab` 参数并直接使用，不会自己创建 Lab。所以 Lab 的创建责任在 `process_so_level` 的 `with LabDocument(...)` 上。

**问题**：目前 `process_so_level` 对 `direct_here` 共用 1 个 Lab，对每个递归的 nested group 又在下一层各自创建 1 个 Lab。当一个 SO 有多个 nested group（不同 DPI 的子 SO）时，创建次数 = nested 组数量。

### 优化方案

**思路**：在 `process_so_level` 层面，对同 DPI 的 `direct_here` 层和 `nested` 递归共用一个 Lab，`nested` 组下钻之前不新建 Lab，而是把外层 Lab 传入递归。

这需要修改函数签名，增加可选的 `lab` 参数：

**修改 `smart_object_handler.py`，`process_so_level()` 函数**：

```python
# 当前函数签名（第 82 行）
def process_so_level(app, doc, records: list[TextLayerRecord], logger, dpi: float, depth: int,
                     _process_layer_func):

# 新增 lab 参数（可选，向后兼容）
def process_so_level(app, doc, records: list[TextLayerRecord], logger, dpi: float, depth: int,
                     _process_layer_func, lab=None):
    """Recursively process records inside an SO document.
    
    lab: 外层传入的 LabDocument 实例（可选）。若传入，则本层直接复用，
         不新建 Lab。若为 None，本层负责创建并在退出时关闭。
    """
    direct_here: list[TextLayerRecord] = []
    nested: dict[str, list[TextLayerRecord]] = {}

    for r in records:
        chain_len = len(r.so_chain)
        if chain_len <= depth or depth >= 3:
            direct_here.append(r)
        else:
            next_entry = r.so_chain[depth]
            psb = next_entry.get("psb_name", "unknown")
            lpath = next_entry.get("layer_path", "unknown")
            nkey = f"{psb}@|@{lpath}"
            nested.setdefault(nkey, []).append(r)

    # 决定是否需要自己创建 Lab
    _own_lab = False
    if lab is None:
        lab = LabDocument(app, dpi)
        lab.__enter__()
        _own_lab = True

    try:
        if direct_here:
            for r in direct_here:
                _process_layer_func(app, doc, r, lab, logger, in_so=True)

        for nkey, ngroup in nested.items():
            entry = ngroup[0].so_chain[depth]
            so_layer = None
            if entry.get("layer_path"):
                so_layer = find_layer_by_path(doc, entry["layer_path"].split("/"))
            if so_layer is None and entry.get("layer_id") is not None:
                so_layer = find_layer_by_id(doc, entry["layer_id"])
            if so_layer is None:
                psb_name = entry.get("psb_name", "")
                if psb_name:
                    so_layer = _find_so_by_psb(app, doc, psb_name)
            if so_layer is None:
                logger.log_error(f"SO layer not found for key '{nkey}'", Exception("not found"))
                continue
            try:
                so_doc = enter_smart_object(app, so_layer)
                so_dpi = float(safe_get(so_doc, "Resolution", dpi))

                # 判断 DPI 是否一致：一致则传入当前 lab 复用，不一致则让下层自己创建
                if abs(so_dpi - dpi) < 0.1:
                    process_so_level(app, so_doc, ngroup, logger, so_dpi, depth + 1,
                                     _process_layer_func, lab=lab)   # ← 传入 lab
                else:
                    process_so_level(app, so_doc, ngroup, logger, so_dpi, depth + 1,
                                     _process_layer_func, lab=None)  # ← DPI 不同，下层自建

                try:
                    so_doc.Close(2)
                except Exception:
                    pass
            except SOEnterError as e:
                logger.log_error(f"enter SO for key '{nkey}'", e)
    finally:
        if _own_lab:
            try:
                lab.__exit__(None, None, None)
            except Exception:
                pass
```

**注意事项**：

1. 原来的 `with LabDocument(app, dpi) as lab:` 改成了手动 `__enter__`/`__exit__`，因为 `lab` 现在可能是外部传入的，不能在 `with` 块退出时关闭外部 Lab。这是唯一会增加代码复杂度的地方，需要确保 finally 块里的判断正确。

2. 递归传入 `lab` 的前提是 DPI 相同（即 Lab 文档的分辨率匹配）。Lab 文档创建时绑定了 DPI（`self._resolution`），用于 `find_adapted_params()` 内部的 `pt_to_px` 换算。DPI 不一致传入会导致字号换算错误，所以加了 `abs(so_dpi - dpi) < 0.1` 的判断。

3. 调用方（`roundtrip_test.py`、`psa_applier.py`）中调用 `process_so_level` 时不传 `lab` 参数，保持向后兼容，函数会自己创建 Lab。

### 预期效果

以 Round 2 为例，38 个 SO 组中大多数 DPI=72，目前每个组在 `direct_here` 处已经共用 1 个 Lab；加入此优化后，同 DPI 的嵌套 SO 也会复用上层 Lab，Lab 创建次数可进一步减少。具体减少量取决于文档的嵌套 SO 结构，预计节省 20~40% 的 Lab 开关时间。

---

## 优化四：multi_style 检测精度提升

### 问题定位

**文件**：`document_scanner.py`，`_extract_text_record()` 函数，第 257~268 行

当前代码：

```python
# Detect multi-style text layers (multiple formatting ranges)
multi_style = False
try:
    runs = ti.Runs
    if runs.Count > 1:
        multi_style = True
except Exception:
    try:
        _ = ti.Font
        _ = ti.Size
    except Exception:
        multi_style = True
```

**问题**：`runs.Count > 1` 会把「同字体同字号，只是颜色不同」的图层也标记为 multi_style 并跳过。颜色变化对自适应算法（只调字号/字距/行距）完全没有影响，不应该跳过。

从 test.psd 的实际图层来看，部分品牌色图层（如渐变文字、双色 Logo 文字）会因为颜色 runs 被误标为 multi_style，导致这些层完全不被处理。

### 优化方案

**修改 `document_scanner.py`，`_extract_text_record()` 函数中的 multi_style 检测段**：

将当前第 257~268 行替换为：

```python
# Detect multi-style text layers: only flag as multi_style when
# font or size differs across runs (color-only differences are irrelevant
# to the adaptive algorithm and should NOT cause the layer to be skipped).
multi_style = False
try:
    runs = ti.Runs
    if runs.Count > 1:
        # 读取第一个 run 的关键排版属性
        try:
            first_font = runs[0].Font
            first_size = float(runs[0].Size)
        except Exception:
            # 连第一个 run 都读不了，保守认定为多样式
            multi_style = True
            first_font = None
            first_size = None

        if not multi_style and first_font is not None:
            for idx in range(1, runs.Count):
                try:
                    r_font = runs[idx].Font
                    r_size = float(runs[idx].Size)
                    if r_font != first_font or abs(r_size - first_size) > 0.5:
                        multi_style = True
                        break
                except Exception:
                    # 某个 run 读不了，保守认定为多样式
                    multi_style = True
                    break
except Exception:
    # ti.Runs 本身不可用时，退回到原来的兜底逻辑
    try:
        _ = ti.Font
        _ = ti.Size
    except Exception:
        multi_style = True
```

### 为什么这样改

1. **只检测字体和字号**：这两个属性直接影响 bounds_h 和 bounds_w，是自适应算法的操作对象。tracking 的差异理论上也有影响，但 per-run tracking 在 Photoshop COM 接口中较难稳定读取，且边界情况复杂，暂不纳入判断，保守处理。

2. **不检测颜色**：颜色改变不影响文本的排版尺寸，跳过颜色差异可以避免误标。

3. **异常保守处理**：任何 run 属性读取异常都认定为多样式，这保持了原有的安全语义（宁可跳过，不要错改）。

4. **向后兼容**：`ti.Runs` 不可用时的 fallback 逻辑（尝试读 `ti.Font`/`ti.Size`）保持不变。

---

## 优化五：`_create_text_layer` 中 tracking 单位潜在问题

### 问题定位

**文件**：`adaptive_lab.py`，`_create_text_layer()` 方法，第 57~89 行

当前代码（第 66~78 行）：

```python
ti = lab_layer.TextItem
try: ti.Font = font_ps
except Exception: pass
try: ti.Contents = contents
except Exception: pass
try: ti.Tracking = tracking           # ← tracking 先于 Size 被设置
except Exception: pass
try: ti.UseAutoLeading = auto_leading
except Exception: pass
if not auto_leading and leading_pt > 0:
    try: ti.Leading = leading_pt
    except Exception: pass
try: ti.Size = size_pt                # ← Size 最后设置
except Exception: pass
```

**潜在问题**：Photoshop COM 中，`ti.Tracking` 的值是以当前 `ti.Size` 为基准的字符间距（单位：1/1000 em）。如果 tracking 在 Size 之前设置，理论上 PS 内部是以默认字号（通常 12pt 或当前文档默认）作为基准来解释这个值的；Size 设置后，PS 会重新渲染，但 tracking 数值本身不会被自动缩放。

从 Round 2 的数据看，tracking 偏差（平均 24.61）虽然比 Round 1（50.5）好了很多，但仍然偏大。这个潜在的设置顺序问题可能是原因之一。

### 优化方案

**在 `_create_text_layer()` 中调整属性设置顺序**，确保 Size 在 tracking 之前被设置：

```python
# 修改后的属性设置顺序（第 65~89 行）
ti = lab_layer.TextItem
try: ti.Font = font_ps
except Exception: pass
try: ti.Size = size_pt               # ← Size 提前到 tracking 之前
except Exception: pass
try: ti.Contents = contents
except Exception: pass
try: ti.Tracking = tracking          # ← tracking 在 Size 之后
except Exception: pass
try: ti.UseAutoLeading = auto_leading
except Exception: pass
if not auto_leading and leading_pt > 0:
    try: ti.Leading = leading_pt
    except Exception: pass
# Center the text layer to prevent boundary overflow
try:
    bounds = lab_layer.Bounds
    w = float(bounds[2]) - float(bounds[0])
    h = float(bounds[3]) - float(bounds[1])
    cx = (self._doc_width / 2.0) - (w / 2.0) - float(bounds[0])
    cy = (self._doc_height / 2.0) - (h / 2.0) - float(bounds[1])
    lab_layer.Translate(cx, cy)
except Exception:
    pass
return lab_layer, ti
```

同样的调整也需要在 `apply_params_to_layer()`（`psa_applier.py`，第 180~221 行）中做一致的检查：

```python
# 当前 apply_params_to_layer（第 193~216 行）
ti = art_layer.TextItem
try:
    ti.Font = params.font_ps         # Font
except Exception: ...
try:
    ti.Size = params.size_pt         # Size ← 已经在 tracking 前，这里没问题
except Exception: ...
try:
    ti.UseAutoLeading = params.auto_leading
except Exception: ...
if not params.auto_leading:
    try:
        ti.Leading = params.leading_pt
    except Exception: ...
try:
    ti.Tracking = params.tracking    # tracking 在 Size 后 ← 顺序正确
except Exception: ...
```

`apply_params_to_layer` 的顺序已经是正确的（Size 在 tracking 前），无需修改。只需修改 `_create_text_layer`。

---

## 修改文件汇总

| 文件 | 改动位置 | 改动内容 |
|------|---------|---------|
| `adaptive_lab.py` | `find_adapted_params()`，第 169~175 行 | 用新字体实测一次 measure_text 得到 hint，替代比例估算 |
| `adaptive_algorithm.py` | `phase1_binary_search()`，第 25~29 行 | i==1 时直接用 initial_hint 作为第一次尝试值 |
| `adaptive_algorithm.py` | `phase3_tracking()`，第 254 行后 | 新增 pre-check；搜索锚点从 current_tracking 改为 record.tracking |
| `smart_object_handler.py` | `process_so_level()`，第 82 行 | 新增 lab 可选参数，同 DPI 时向下传递 lab 复用 |
| `document_scanner.py` | `_extract_text_record()`，第 257~268 行 | multi_style 检测改为只对比 font/size，忽略颜色差异 |
| `adaptive_lab.py` | `_create_text_layer()`，第 66~78 行 | 将 ti.Size 提前到 ti.Tracking 之前设置 |

---

## 优先级建议

1. **优化一（Phase 1 预估）**：影响最大，每层节省约 5~10 秒，建议优先实施
2. **优化五（属性设置顺序）**：改动最小（2 行），风险低，可与优化一一起改
3. **优化四（multi_style 检测）**：修复误判，不影响性能，改动清晰，建议同步实施
4. **优化二（Tracking 锚点）**：改善往返 tracking 精度，需 Round 3 验证效果
5. **优化三（SO Lab 复用）**：收益依赖文档 SO 嵌套结构，改动涉及函数签名，建议最后实施

---

## 验证方法

实施后用 `roundtrip_test.py` 跑 Round 3，对比：
- `round3_comparison.json` 中 `avg_tracking_drift` 是否 < 15
- `round3_step1.log` 中单层 Phase 1 迭代次数是否普遍降至 4~6 次
- 检查原来被 multi_style 跳过的图层是否被正确处理（看 SKIP 日志条目减少）
- 总执行时间是否缩短（对比 round2_step1.log 的起止时间戳）
