# PS 模块自适应算法调优指南

本文档面向接手调优工作的开发者，说明如何通过往返测试（Roundtrip Test）评估和改进
`vendor/adobe/photoshop/com/src/` 下的自适应算法。

---

## 目录结构

```
C:\MediaTools\vendor\adobe\photoshop\com\
├── tuning\
│   ├── test.psd                ← 母版，永远不动
│   ├── README.md               ← 本文档
│   └── （测试过程产生的文件）
└── src\
    ├── main.py                 ← CLI 入口
    ├── adaptive_lab.py         ← Lab 文档 + find_adapted_params()
    ├── adaptive_algorithm.py   ← Phase 1/2/3 算法
    ├── psa_applier.py          ← 单层处理：calibrate → apply → verify/refine
    ├── document_scanner.py     ← 扫描 PSD，生成 TextLayerRecord 列表
    ├── smart_object_handler.py ← 智能对象递归处理
    ├── font_resolver.py        ← 字体索引 + 字重匹配
    ├── ticket_workflow.py      ← 工单扫描 / 执行
    └── text_models.py          ← TextLayerRecord、AdaptedParams 数据结构
```

---

## 一、往返测试的原理

往返测试通过两次对称变换来量化算法的还原能力：

```
test.psd  (Noto Sans，正常文本)
    │
    │  Step 1：每行文本镜像 + 字体换成 Byte Sans
    ▼
test-mirror.psd
    │
    │  Step 2：每行文本再次镜像（还原）+ 字体换回 Noto Sans
    ▼
test-mirror-mirror.psd
    │
    │  Step 3：逐层对比 test.psd vs test-mirror-mirror.psd
    ▼
偏差报告
```

**核心逻辑**：两次镜像后文本必然还原（`"abc"` → `"cba"` → `"abc"`），字体也经历了
Noto→Byte→Noto 的完整往返。如果算法完美，`test-mirror-mirror.psd` 的每一层字号、
字距、行高都应与 `test.psd` 完全一致。偏差越小、耗时越短，算法越优秀。

**为什么选这两个字体家族**：Noto Sans 和 Byte Sans 的字形度量（x-height、字宽比例）
存在明显差异，能充分暴露算法在跨字体场景下的适应能力。

---

## 二、测试脚本的职责

`main.py` 是通用 CLI，不直接支持往返测试逻辑。往返测试需要一个专用脚本
（参考历史版本 `roundtrip_test.py`），该脚本负责：

1. 调用 `scan_document_for_ticket()` 扫描 PSD，得到 `TicketScanRow` 列表
2. 对每一行自动填写 `target_text`（镜像文本）和 `target_font`（目标字体家族）
3. 调用 `execute_ticket()` 执行修改，输出新 PSD
4. 扫描原始 PSD 和最终 PSD，逐层对比，输出 JSON 报告

**镜像函数**（核心逻辑，必须正确处理换行符）：

```python
def mirror_text(text: str) -> str:
    # 统一换行符为 \n，再按行镜像，最后还原为 PS 使用的 \r
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return "\r".join(line[::-1] for line in lines)
```

注意：Photoshop 内部用 `\r` 作为换行符，`ti.Contents` 读出的是 `\r`，写入也必须用 `\r`。
如果镜像函数换行符处理有误，文本还原率会低于 100%，这是 bug 而非算法问题。

**字体填写规则**：
- `target_font` 只填字体家族名（`"Byte Sans"` 或 `"Noto Sans"`），不填字重
- 字重由 `font_resolver.py` 的 `resolve_font()` 根据原始字重数值自动匹配最近变体
- 这是测试算法字重自适应能力的关键，不要手动指定字重

---

## 三、执行步骤

### 前置条件

- Photoshop 已启动并处于前台（整个过程约 40 分钟，不要切换活动文档）
- Python 环境已配置，工作目录为 `C:\MediaTools\vendor\adobe\photoshop\com\src\`
- 测试文件位于 `C:\MediaTools\vendor\adobe\photoshop\com\tuning\test.psd`

### Step 1：test.psd → test-mirror.psd

测试脚本内部流程：

```
1. 扫描 test.psd
   → 调用 scan_document_for_ticket(ps, doc, "test.psd")
   → 得到 52 个 TicketScanRow，记录每层的 layer_id、layer_path、raw_text、
     source_font、font_size、tracking、height_px

2. 构造修改指令
   → 对每个 row：
       row.target_text = mirror_text(row.raw_text)   # 每行镜像
       row.target_font = "Byte Sans"                  # 换字体家族，不指定字重

3. 执行修改
   → 调用 execute_ticket(ps, "test.psd", rows, output_dir, params)
   → 内部对每层调用 psa_applier.process_layer()，走完整的
     CALIBRATE → find_adapted_params → APPLY → VERIFY → REFINE 流程
   → 输出 test-mirror.psd

4. 保存执行日志到 step1_execute.log
```

### Step 2：test-mirror.psd → test-mirror-mirror.psd

与 Step 1 完全对称：

```
1. 扫描 test-mirror.psd（此时字体是 Byte Sans，文本是镜像状态）
2. 构造修改指令
   → row.target_text = mirror_text(row.raw_text)   # 再次镜像，还原原始文本
   → row.target_font = "Noto Sans"                  # 换回 Noto Sans
3. 执行修改，输出 test-mirror-mirror.psd
4. 保存执行日志到 step2_execute.log
```

### Step 3：对比分析

```
1. 扫描 test.psd，得到原始参数快照（orig_records）
2. 扫描 test-mirror-mirror.psd，得到往返后参数（rt_records）
3. 以 layer_path 为键逐层匹配（不能用 layer_id，两个文档的 id 不同）
4. 计算各项偏差，输出 comparison.json
```

---

## 四、产生的数据文件

每轮测试完成后，`tuning\` 目录下会有：

```
tuning\
├── test.psd                    ← 母版，不动
├── test-mirror.psd             ← Step 1 输出
├── test-mirror-mirror.psd      ← Step 2 输出，最终对比对象
├── step1_scan.log              ← Step 1 扫描日志
├── step1_execute.log           ← Step 1 执行日志（含迭代详情）
├── step2_scan.log              ← Step 2 扫描日志
├── step2_execute.log           ← Step 2 执行日志
└── comparison.json             ← 最终对比报告
```

多轮测试时建议按轮次命名，例如 `round3_step1_execute.log`、`round3_comparison.json`，
避免覆盖历史数据（历史数据是判断优化是否退步的依据）。

---

## 五、评估指标

### 准确性指标（越小越好）

| 指标 | 计算方式 | 优秀 | 可接受 | 需优化 |
|------|---------|------|--------|--------|
| 字号偏差 | `abs(rt_size_pt - orig_size_pt) / orig_size_pt × 100%` | < 3% | < 8% | ≥ 8% |
| 字距偏差 | `abs(rt_tracking - orig_tracking)` | < 10 | < 20 | ≥ 20 |
| 行高偏差 | `abs(rt_leading_pt - orig_leading_pt)` | < 2pt | < 5pt | ≥ 5pt |
| 边界高度偏差 | `abs(rt_bounds_h - orig_bounds_h)` px | ≤ 1px | ≤ 3px | > 3px |
| 字体还原率 | 字体匹配层数 / 总层数 | 100% | ≥ 90% | < 90% |
| 文本还原率 | 文本匹配层数 / 总层数 | **必须 100%** | — | < 100% = bug |

> 文本还原率低于 100% 是脚本 bug（镜像函数换行符处理有误），不是算法问题，优先修复。

### 性能指标（越小越好）

| 指标 | 如何统计 | 优秀 | 可接受 | 需优化 |
|------|---------|------|--------|--------|
| Phase 1 平均迭代次数 | 统计执行日志中 `[iter XX size]` 行数 / 总层数 | ≤ 4 | ≤ 7 | > 7 |
| REFINE 触发率 | 触发 `REFINE` 的层数 / 总层数 | < 20% | < 50% | ≥ 50% |
| 单层平均耗时 | 总执行时间 / 总层数 | < 15s | < 25s | ≥ 25s |

---

## 六、如何读执行日志

每个图层的处理在日志里对应一个完整的块，结构如下：

```
BEFORE [图层路径]: text='...' font=NotoSans-Bold size_pt=51.51 tracking=20.0 bounds_h=141.00px
APPLY:  [图层路径] target_h=141.00px font_resolved=ByteSans-Regular
INFO: CALIBRATE [图层路径]: real_h=141.00px lab_h=114.00px scale=1.2368
    [iter 01 size] tried=51.51pt → h=114.00px  target=114.00px CONVERGED   ← 第1次命中，hint 准确
INFO: BOUNDARY PROTECT [图层路径]: Expanded SO canvas by 34%
INFO: VERIFY [图层路径]: real_h=140.00px target=141.00px diff=-1.00px       ← 偏差 1px，触发 REFINE
INFO: REFINE 1 [图层路径]: size=52.10pt real_h=141.00px target=141.00px     ← REFINE 修正
RESULT [图层路径]: OK font=ByteSans-Regular size_pt=52.10 tracking=18.5 final_h=141.00px
AFTER  [图层路径] [OK]: ...
```

**关键观察点**：

- `CALIBRATE` 的 `scale` 值：反映 Lab 文档与真实文档的渲染比例差异。scale 越接近 1.0，
  说明 Lab 环境与真实环境越一致，后续 hint 预估越准确。

- `[iter 01 size]` 是否 `CONVERGED`：第一次迭代就命中说明 hint 预估非常准确；
  需要 8+ 次才收敛说明 hint 偏差大，是优化 Phase 1 的信号。

- `VERIFY diff`：CALIBRATE + find_adapted_params 完成后，在真实图层上测量的实际高度
  与目标高度的差值。diff 大（> 5px）说明 Lab 的 scale 系数对该图层不准确。

- `REFINE` 次数：REFINE 是在真实图层上做的微调，每次需要 PS 重新渲染，代价较高。
  REFINE 触发率高说明 Lab 阶段的结果不够准确。

---

## 七、从对比数据识别系统性问题

拿到 `comparison.json` 后，先看 `summary`，再按以下思路定位根因：

### 字号偏差大（avg_size_drift_pct ≥ 8%）

1. 检查执行日志的 `CALIBRATE scale` 值是否异常（远离 1.0）
2. 检查 Phase 1 迭代次数是否过多（hint 预估不准）
3. 检查 `VERIFY diff` 是否系统性偏正或偏负
   - 系统性偏正（real_h 总是大于 target）：Lab 的 scale 系数偏小，导致 find_adapted_params
     给出的字号偏大，REFINE 向下修正后仍有残差
   - 系统性偏负：反之

**涉及代码**：`adaptive_lab.py` 的 `find_adapted_params()`，`psa_applier.py` 的
`process_layer()` 中 scale 计算部分（第 66~87 行）

### 字距偏差大（avg_tracking_drift ≥ 20）

1. 检查执行日志中 `[micro XX track]` 的搜索过程
2. 看 `best_tracking` 是否总是偏向某个方向（正向漂移说明搜索锚点有偏置）
3. 检查 `[phase3 pre-check]` 是否正确跳过了原始 tracking 已经合适的图层

**涉及代码**：`adaptive_algorithm.py` 的 `phase3_tracking()`（第 250 行起）

### 字体还原率低（< 90%）

1. 检查 `comparison.json` 中 `font_restored=false` 的图层，看 `rt_font` 是什么
2. 如果 `rt_font` 全是同一个回退字体（如 `AdobeHeitiStd-Regular`），说明字体赋值失败
3. 检查 `font_resolver.py` 的 `build_font_index()` 是否正确读取了 `PostScriptName`

**涉及代码**：`font_resolver.py` 的 `build_font_index()`（第 55 行起），
`psa_applier.py` 的 `apply_params_to_layer()`（第 180 行起）

### REFINE 触发率高（≥ 50%）

说明 Lab 阶段的结果与真实文档差异较大，根因通常是：
1. Lab 文档的 DPI 与真实文档不一致（检查 `CALIBRATE` 日志中的 `scale` 值）
2. Smart Object 内的图层，SO canvas 尺寸影响了文字渲染边界
3. `_create_text_layer()` 的属性设置顺序导致 PS 以错误状态渲染

**涉及代码**：`adaptive_lab.py` 的 `_create_text_layer()`（第 57 行起）

---

## 八、多轮测试的对比方法

每轮测试后，将 `comparison.json` 的 `summary` 整理成表格：

| 轮次 | 改动内容 | 字号偏差 | 字距偏差 | 高度偏差 | 字体还原率 | Phase1 均迭代 | 单层耗时 |
|------|---------|---------|---------|---------|-----------|-------------|---------|
| Round 1 | 基线（字体索引 bug） | 10.23% | 50.5 | 0.9px | 5% | ~10 | ~25s |
| Round 2 | 修复 PostScriptName | 10.08% | 24.61 | 1.09px | 65% | ~9 | ~23s |
| Round 3 | hint 优化 + tracking 锚点 | — | — | — | — | — | — |

**判断优化是否有效**：
- 目标指标改善，其他指标没有明显退步 → 有效
- 目标指标改善，但其他指标退步 → 需要权衡，分析退步原因
- 所有指标都退步 → 优化方向有误，回滚并重新分析

---

## 九、注意事项

1. **test.psd 是母版，永远不动**。每轮测试都从这个文件出发，不要在它上面做任何修改。

2. **对比时用 `layer_path` 匹配，不用 `layer_id`**。两个不同 PSD 文件的同一图层，
   `layer_id` 不同，但 `layer_path`（图层路径）相同。

3. **Smart Object 的 canvas 扩展是预期行为**。Step 1 执行后，SO 的 canvas 可能被
   `BOUNDARY PROTECT` 扩展过，Step 2 扫描时读到的 `bounds_h` 可能与 Step 1 前不同。
   这不是 bug，但会影响 Step 2 的 CALIBRATE scale，属于正常的累积误差。

4. **multi_style 图层会被跳过**。如果某图层有多个 TextRange 且 font 或 size 不同，
   算法会跳过该层（日志中有 `SKIP multi-style` 记录）。这类图层不计入偏差统计。

5. **测试期间 Photoshop 必须保持前台**。整个过程约 40 分钟，不要手动操作 PS，
   不要切换活动文档，否则 `app.ActiveDocument` 会被打乱导致图层找不到。

6. **历史数据不要覆盖**。每轮测试的日志和 comparison.json 是判断优化是否退步的依据，
   建议按轮次命名保留。
