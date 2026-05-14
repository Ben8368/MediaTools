# PS 自适应算法调优指南

本文档说明如何通过往返测试（Roundtrip Test）评估和改进
`vendor/adobe/photoshop/com/src/` 下的自适应算法。

---

## 目录结构

```
tuning/
├── README.md              ← 本文档
├── baseline.psd            ← 母版（52层），标准往返测试用，永远不动
├── smoke.psd               ← 快速测试（4层），快速往返测试用
├── roundtrip_test.py       ← 往返测试脚本（待写）
└── （测试过程产生的日志和对比文件）
```

| 文件 | 层数 | 用途 |
|------|------|------|
| `baseline.psd` | 52（含多层嵌套 SO） | 标准往返测试，全面评估跨字体场景 |
| `smoke.psd` | 4（2 直接 + 2 SO） | 快速往返测试，每次改代码后冒烟验证 |

---

## 一、两种往返测试的分工

| | 快速往返（Quick） | 标准往返（Standard） |
|---|---|---|
| **PSD** | `smoke.psd` | `baseline.psd` |
| **文本** | 每行镜像 | 每行镜像 |
| **字体** | **不改** | Noto Sans → Byte Sans → Noto Sans |
| **耗时** | ~2 分钟 | ~40 分钟 |
| **目的** | 验证算法正确性、发现 bug | 跨字体压力下优化时间效率 |
| **跑的条件** | 每次改代码后 | 快速往返通过、无严重 bug 后 |

### 为什么两种测试互补

**快速往返**不改字体，算法负担最小。镜像两次文本必然还原（`"abc" → "cba" → "abc"`），
如果文本还原率不是 100% 或者有层不收敛，说明代码有 bug，优先修复。

**标准往返**跨字体（Noto Sans ↔ Byte Sans），用 52 层充分暴露算法在真实场景下的压力。
Noto Sans 和 Byte Sans 的字形度量（x-height、字宽比例）差异明显，能检验字号自适应、
tracking 调整、REFINE 修正等全部环节。快速往返通过后才跑这个。

---

## 二、快速往返测试

### 原理

```
smoke.psd (不改字体)
  → Step 1: 每行文本镜像 → smoke-mirror.psd
  → Step 2: 再次镜像(文本还原) → smoke-mirror-mirror.psd
  → Step 3: 对比 smoke.psd vs smoke-mirror-mirror.psd
```

### 验证目标

1. 文本还原率是否 **100%**（不是 100% 就是镜像函数或执行管线的 bug）
2. 每层是否都 **收敛**（converged = true）
3. 往返后字号偏差、tracking 偏差是否在可接受范围
4. 是否存在 ERROR 日志

### 通过的判定标准

- `text_restoration_rate` = 100%
- 所有层 `converged` = true
- 所有层 `size_drift_pct` < 3%
- 所有层 `bounds_drift_px` ≤ 1px
- 零 ERROR 日志

---

## 三、标准往返测试

### 原理

```
baseline.psd (Noto Sans，正常文本)
  → Step 1: 每行镜像 + 字体换 Byte Sans → baseline-mirror.psd
  → Step 2: 再次镜像(文本还原) + 字体换回 Noto Sans → baseline-mirror-mirror.psd
  → Step 3: 逐层对比 baseline.psd vs baseline-mirror-mirror.psd
```

### 镜像文本函数

```python
def mirror_text(text: str) -> str:
    # Photoshop 内部用 \r 作为换行符
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return "\r".join(line[::-1] for line in lines)
```

### 字体填写规则

- `target_font` 只填家族名（`"Byte Sans"` 或 `"Noto Sans"`），不指定字重
- 字重由 `font_resolver.resolve_font()` 按数值距离自动匹配
- 这是测试字重自适应能力的关键，**不要手动指定字重**

---

## 四、评估指标

### 准确性指标（越小越好）

| 指标 | 计算方式 | 优秀 | 可接受 | 需优化 |
|------|---------|------|--------|--------|
| 字号偏差 | `abs(rt_size_pt - orig_size_pt) / orig_size_pt × 100%` | < 3% | < 8% | ≥ 8% |
| tracking 偏差 | `abs(rt_tracking - orig_tracking)` | < 10 | < 20 | ≥ 20 |
| bounds_h 偏差 | `abs(rt_bounds_h - orig_bounds_h)` px | ≤ 1 | ≤ 3 | > 3 |
| 字体还原率 | 字体匹配层数 / 总层数 | 100% | ≥ 90% | < 90% |
| 文本还原率 | 文本匹配层数 / 总层数 | **必须 100%** | — | < 100% = bug |

> 文本还原率低于 100% 是镜像函数或执行管线 bug，优先修复。

### 效率指标（越小越好）

| 指标 | 统计方式 | 优秀 | 可接受 | 需优化 |
|------|---------|------|--------|--------|
| Phase1 平均迭代 | 日志中 `[iter XX size]` 行数 / 总层数 | ≤ 4 | ≤ 7 | > 7 |
| REFINE 触发率 | 触发 REFINE 层数 / 总层数 | < 20% | < 50% | ≥ 50% |
| 单层平均耗时 | 总执行时间 / 总层数 | < 15s | < 25s | ≥ 25s |

**精确度优先于时间**：先确保准确性指标全部达标，再优化效率指标。

---

## 五、如何读执行日志

每层处理在日志中对应一个完整的块：

```
BEFORE [图层路径]: text='...' font=NotoSans-Bold size_pt=51.51 tracking=20.0 bounds_h=141.00px
APPLY:  [图层路径] target_h=141.00px font_resolved=ByteSans-Regular
INFO: CALIBRATE [图层路径]: real_h=141.00px lab_h=114.00px scale=1.2368
    [iter 01 size] tried=51.51pt → h=114.00px  target=114.00px CONVERGED   ← hint 准确，首次命中
INFO: BOUNDARY PROTECT [图层路径]: Expanded SO canvas by 34%
INFO: VERIFY [图层路径]: real_h=140.00px target=141.00px diff=-1.00px       ← 差 1px，触发 REFINE
INFO: REFINE 1 [图层路径]: size=52.10pt real_h=141.00px target=141.00px     ← REFINE 修正
RESULT [图层路径]: OK font=ByteSans-Regular size_pt=52.10 tracking=18.5 final_h=141.00px
AFTER  [图层路径] [OK]: ...
```

**关键观察点**：

- **CALIBRATE scale**：Lab 与真实文档的渲染比例差异。越接近 1.0 说明 Lab 环境与真实环境越一致
- **`[iter 01 size]` 是否 CONVERGED**：首次迭代命中说明 hint 预估准确；8+ 次才收敛说明 hint 偏差大
- **VERIFY diff**：Lab 阶段完成后真实图层上测量的偏差。> 5px 说明 scale 系数对当前层不准确
- **REFINE 次数**：在真实图层上微调，每次需要 PS 重新渲染代价高。触发率高说明 Lab 阶段结果不够准

---

## 六、分析 → 优化 → 验证循环

```
快速往返通过 ✓
  → 跑标准往返 baseline → comparison.json + 执行日志
    → 看偏差最大的层 → 读每层日志
      → 定位问题类型（见第七章）
        → 改代码 → 先跑快速往返验证无回归
          → 再跑标准往返 → 对比 baseline
            → 精确度改善 + 无退步 → 保留
            → 精确度不变 + 更快 → 保留
            → 退步 → 回滚
```

---

## 七、从对比数据定位问题

拿到 `comparison.json` 后，先看 summary，再按以下思路定位根因：

### 字号偏差大（avg_size_drift_pct ≥ 8%）

1. 检查执行日志的 `CALIBRATE scale` 值是否异常（远离 1.0）
2. 检查 Phase 1 迭代次数是否过多（hint 预估不准）
3. 检查 `VERIFY diff` 是否系统性偏正或偏负
   - 系统性偏正（real_h 总是大于 target）：Lab scale 偏小，字号偏大，REFINE 修正后仍有残差
   - 系统性偏负：反之

**涉及代码**：`adaptive_lab.py:find_adapted_params()`，`psa_applier.py:process_layer()` 中 scale 计算

### tracking 偏差大（avg_tracking_drift ≥ 20）

1. 检查执行日志中 `[micro XX track]` 搜索过程
2. 看 `best_tracking` 是否总是偏某个方向（锚点有偏置）
3. 检查 `[phase3 pre-check]` 是否正确跳过了 tracking 已合适的层

**涉及代码**：`adaptive_algorithm.py:phase3_tracking()`

### 字体还原率低（< 90%）

1. 检查 `comparison.json` 中 `font_restored = false` 的层
2. 如果 `rt_font` 全是同一个回退字体，说明字体赋值失败
3. 检查 `font_resolver.build_font_index()` 是否正确读取了 PostScriptName

**涉及代码**：`font_resolver.py:build_font_index()`，`psa_applier.py:apply_params_to_layer()`

### REFINE 触发率高（≥ 50%）

根因通常是：
1. Lab DPI 与真实文档不一致（检查 CALIBRATE 中的 scale 值）
2. SO 内图层 canvas 尺寸影响文字渲染边界
3. `_create_text_layer()` 属性设置顺序导致 PS 以错误状态渲染

**涉及代码**：`adaptive_lab.py:_create_text_layer()`

---

## 八、多轮测试的对比方法

每轮测试后将 `comparison.json` 的 summary 整理成表格：

| 轮次 | 改动 | 字号偏差% | tracking 偏差 | bounds 偏差 | 字体还原率 | Phase1 迭代 | REFINE% | 单层耗时 |
|------|------|----------|-------------|------------|-----------|------------|---------|---------|
| R1 | baseline | 10.23% | 50.5 | 0.9px | 90% | ~10 | 55% | ~25s |
| R2 | 修复 PostScriptName | 10.08% | 24.6 | 1.1px | 95% | ~9 | 50% | ~23s |
| R3 | hint 优化 | — | — | — | — | — | — | — |

**判断优化是否有效**：
- 目标改善 + 其他无退步 → 有效
- 目标改善 + 其他退步 → 需权衡
- 全部退步 → 方向错误，回滚

---

## 九、roundtrip_test.py 用法

```bash
# 快速往返测试（smoke.psd，不改字体）
python roundtrip_test.py --psd smoke.psd --mode quick

# 标准往返测试（baseline.psd，换字体）
python roundtrip_test.py --psd baseline.psd --mode full

# 指定输出轮次名
python roundtrip_test.py --psd baseline.psd --mode full --round round3
```

每轮产生：
```
tuning/
├── {round}_step1_execute.log    ← Step 1 执行日志（含迭代详情）
├── {round}_step2_execute.log    ← Step 2 执行日志
├── {round}_comparison.json      ← 最终对比报告
├── baseline-mirror.psd          ← Step 1 输出（避免下次重跑 Step1）
└── baseline-mirror-mirror.psd   ← Step 2 输出
```

---

## 十、注意事项

1. **baseline.psd 是母版，永远不动**。每轮测试从它出发，不在它上面做任何修改。

2. **对比时用 `layer_path` 匹配，不用 `layer_id`**。两个不同 PSD 文件的同一图层 layer_id 不同。

3. **SO canvas 扩展是预期行为**。Step 1 后 SO 的 canvas 可能被 `BOUNDARY PROTECT` 扩展过，这会略微影响 Step 2 的 CALIBRATE scale，属于正常累积误差。

4. **multi_style 图层会被跳过**。如果某图层有多个 TextRange 且 font/size 不同，算法会跳过（日志有 `SKIP multi-style`），不计入统计。

5. **测试期间 Photoshop 必须保持前台**。不要手动操作 PS 或切换活动文档。

6. **历史数据按轮次保留**。多轮测试的日志和 comparison.json 是判断退步的依据，不要覆盖。
