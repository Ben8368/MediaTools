# 素材审计系统 (Auditor)

基于 Google Gemini AI 的自动化素材审计系统。通过**双盲审机制**（两个独立 AI 审计员同时分析同一素材），自动检测视频/图片素材中的合规问题，并将结果写入 Excel/飞书/Google Sheets。

---

## 核心特性

- **双盲审裁定**：AUDITOR_1（敏感型）和 AUDITOR_2（保守型）独立审计同一文件，通过裁定逻辑得出最终结论
- **智能文件监控**：基于 mtime/size/hash 的四层变化检测，确保文件传输完成后才启动审计
- **配置驱动**：所有配置（API Key、监控目录、规则、角色 Prompt 等）存储在 Excel 中，代码零硬编码
- **设计师归因**：从文件名自动匹配设计师，确定通知对象
- **多后端支持**：本地 Excel（已实现）、飞书多维表格（待实现）、Google Sheets（待实现）
- **GUI / CLI 双模式**：命令行常驻进程 或 PyQt5 图形界面

## 审计结论分级

| 结论 | 含义 |
|------|------|
| **CONFIRMED**（双审确认） | 两个审计员都判定为 fail |
| **DISPUTED**（一审发现） | 仅一审判定为 fail |
| **SECOND_FIND**（二审发现） | 仅二审判定为 fail |
| **CLEARED**（通过） | 两个审计员都判定为 pass |

## 审计流程

```
文件夹监控 (IDLE → WATCHING → SETTLED)
       │
       ▼
  发现新/修改的文件
       │
       ▼
  双盲审计 (并行请求)
  ┌─────────────┬─────────────┐
  │ AUDITOR_1   │ AUDITOR_2   │
  │ (敏感型)     │ (保守型)     │
  └──────┬──────┴──────┬──────┘
         │             │
         ▼             ▼
       裁定逻辑 (CONFIRMED / DISPUTED / SECOND_FIND / CLEARED)
         │
         ▼
  置信度计算 (证据 + 规则类型 + 语言 + 音频)
         │
         ▼
  设计师匹配 → 写入结果 (Excel/飞书/Sheets)
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install PyQt5             # 可选，如需 GUI 模式
```

### 2. 配置

编辑 `tao_config.xlsx`（首次运行会自动生成），填写以下必填项：

| Sheet | 必填字段 | 示例值 |
|-------|----------|--------|
| **系统配置** | `GCP_API_KEY` | 你的 AI Studio API Key（AIza... 或 AQ.Ab8R... 格式） |
| | `WATCH_FOLDERS` | `C:\素材\待审` (多个路径用英文逗号分隔) |
| | `SUPERVISOR_FEISHU_ID` | `ou_xxxxxxxx` (主管飞书 open_id，可选) |
| **角色定义** | `AUDITOR_1` / `AUDITOR_2` / `OUTPUT_FORMAT` | 各角色的 System Prompt |
| **审计规则** | 规则列表 | rule_id, 名称, 描述, 启用状态等 |
| **设计师表** | 设计师列表 | 姓名, PID, 飞书 open_id, 启用状态 |

> `GCP_API_KEY` 前往 https://aistudio.google.com/apikey 创建，需要为 Google Cloud 项目绑定计费账号。

### 3. 运行

```bash
# CLI 模式（后台常驻）
python main.py

# GUI 模式（图形界面）
python gui.py
```

### 4. 工具脚本

```bash
# 测试 API Key 是否可用
python test_apikey.py

# 重建/刷新 Excel 配置（保留已有数据）
python rebuild_config.py

# 刷新 Excel 中模型下拉选项
python refresh_model_dropdown.py
```

---

## 配置详解

### 系统配置 Sheet

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `GCP_API_KEY` | AI Studio API Key | — |
| `MODEL_VIDEO` | 视频分析模型 | gemini-2.5-pro |
| `MODEL_IMAGE` | 图片分析模型 | gemini-2.5-flash |
| `WATCH_FOLDERS` | 监控文件夹路径 | — |
| `SCAN_INTERVAL_SECONDS` | 扫描间隔（秒） | 120 |
| `STABLE_WAIT_SECONDS` | 文件稳定等待时间 | 120 |
| `MIN_FILE_SIZE_BYTES` | 最小文件大小 | 10240 |
| `ALLOWED_EXTENSIONS` | 允许的扩展名 | .mp4,.mov,.avi,.png,.jpg... |
| `RUN_MODE` | TEST / PRODUCTION | TEST |
| `MAX_CONCURRENCY` | 并发审计数 | 5 |
| `API_TIMEOUT_SECONDS` | API 超时（秒） | 300 |
| `API_RETRY_COUNT` | 失败重试次数 | 3 |
| `CONFIDENCE_W_EVIDENCE` | 置信度权重: 证据 | 0.40 |
| `CONFIDENCE_W_RULE_TYPE` | 置信度权重: 规则类型 | 0.25 |
| `CONFIDENCE_W_LANGUAGE` | 置信度权重: 语言确定性 | 0.20 |
| `CONFIDENCE_W_AUDIO` | 置信度权重: 音频清晰度 | 0.15 |

### 审计规则字段

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `rule_id` | 规则唯一标识 | 如 `RULE_001` |
| `rule_name` | 规则名称 | 中文简短描述 |
| `rule_description` | 规则详细描述 | 告诉模型检查什么、怎么判断 |
| `enabled` | 是否启用 | `TRUE` / `FALSE` |
| `strictness_level` | 严格度 | `STANDARD` / `STRICT` |
| `negative_check` | 缺失检查（缺失也算 fail） | `TRUE` / `FALSE` |
| `rule_type` | 规则类型（影响置信度） | `hard` / `soft` |
| `version` | 版本号 | 如 `v1.0` |

### 文件名规范

系统从文件名自动解析信息，推荐格式：
```
[素材编号]-[客户]-[产品]-[创意类型]-[日期]-[设计师]-pid-[PID]-[尺寸].[扩展名]
```
示例：`ZCV001-BytePlus-Seedream5.0Lite-Ability-20250401-Clairo-pid-10623-1200x1200.mp4`

---

## 项目结构

```
Auditor/
├── main.py                     # CLI 入口，启动常驻监控进程
├── gui.py                      # GUI 入口（PyQt5），含实时日志和结果展示
├── settings.py                 # 从 .env 读取连接配置（后端类型等）
├── requirements.txt            # Python 依赖清单
├── .env / .env.example         # 环境变量配置
├── tao_config.xlsx             # 主配置文件（系统配置/角色/规则/设计师/结果）
│
├── audit/                      # 审计引擎
│   ├── engine.py               # 双盲审主流程 + 裁定逻辑
│   ├── prompt_builder.py       # 动态拼接 Prompt（从配置表读取，无硬编码）
│   └── gemini_client.py        # Google Gemini API 封装（google-genai SDK）
│
├── monitor/                    # 文件夹监控
│   ├── folder_monitor.py       # 状态机 + 四层变化检测（IDLE→WATCHING→SETTLED→AUDITING）
│   └── snapshot.py             # 快照 JSON 读写（记录上次审计时的文件状态）
│
├── output/                     # 配置/结果存储后端（工厂模式）
│   ├── base.py                 # 抽象接口 OutputBackend
│   ├── factory.py              # 根据 settings.BACKEND 创建对应实例
│   ├── local_backend.py        # 本地 Excel 后端（已实现，首次运行自动创建）
│   ├── feishu_backend.py       # 飞书多维表格后端（接口已定义，待实现）
│   └── google_backend.py       # Google Sheets 后端（接口已定义，待实现）
│
├── feishu/
│   └── designer_lookup.py      # 设计师归因模块（从文件名匹配设计师）
│
├── data/                       # 运行时数据（自动创建）
│   └── snapshot.json           # 文件快照
├── logs/                       # 日志目录（自动创建）
│   └── auditor.log
└── output/                     # 审计结果输出（自动创建）
    └── 结果写入 tao_config.xlsx 的"审计结果" Sheet
```

---

## 故障排查

### API 调用失败

| 错误 | 原因 | 解决 |
|------|------|------|
| `429 RESOURCE_EXHAUSTED` | 预付费额度已耗尽 | 前往 AI Studio 为项目绑定结算账号 |
| `400 INVALID_ARGUMENT - API key expired` | API Key 已过期 | 前往 aistudio.google.com/apikey 重新创建 |
| `GCP_API_KEY 未填写` | 配置表中未填写 Key | 在 `tao_config.xlsx` 系统配置 Sheet 中填写 |

### 依赖安装失败

```bash
# 常见依赖问题
pip install --upgrade pip
pip install -r requirements.txt
pip install PyQt5              # GUI 需要
pip install google-genai       # Gemini SDK（requirements.txt 中可能遗漏）
```

### 文件没有触发审计

- 检查 `WATCH_FOLDERS` 路径是否正确
- 检查文件大小是否大于 `MIN_FILE_SIZE_BYTES`（默认 10240 字节）
- 检查文件扩展名是否在 `ALLOWED_EXTENSIONS` 中
- 确保文件格式不是 `.tmp` 或以 `.` `~$` 开头
- 查看 `logs/auditor.log` 中的监控日志

### 清理快照重新扫描

```bash
# 删除快照文件，下次扫描将视为所有文件为新文件
rm data/snapshot.json
# 或在 GUI 中点击 "清空快照"
```

---

## 架构说明

### 双盲审原理

系统同时向 Gemini 发送两次请求，分别扮演两个不同角色的审计员：

- **AUDITOR_1（敏感型）**：倾向于发现更多问题
- **AUDITOR_2（保守型）**：只确认明显的问题

两次请求使用不同的人物设定，但分析同一素材。裁定逻辑：
```
一审: fail + 二审: fail → CONFIRMED（双审确认问题）
一审: fail + 二审: pass → DISPUTED（一审发现问题）
一审: pass + 二审: fail → SECOND_FIND（二审发现问题）
一审: pass + 二审: pass → CLEARED（通过）
```

### 置信度计算

综合四个维度计算 0~1 的置信度分数：

```
confidence = 0.40 × 证据具体性
           + 0.25 × 规则类型（硬规则得分高）
           + 0.20 × 语言确定性（不含"可能""似乎"等不确定词语）
           + 0.15 × 音频清晰度（视频素材）
```

### 监控状态机

```
IDLE ──发现变化──→ WATCHING ──连续稳定──→ SETTLED ──审计完成──→ IDLE
                      │                                         │
                      └── 仍在变化 ──→ 重置计时 ──→ WATCHING ───┘
```

- **IDLE**：空闲，与持久化快照比对
- **WATCHING**：发现变化，对比连续两次扫描结果判断是否稳定
- **SETTLED**：文件已稳定，提取新文件启动审计
- **AUDITING**：审计进行中，完成后保存快照返回 IDLE
