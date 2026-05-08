# 项目上下文快照 (Context Snapshot)

> **更新规则：**
> 1. 代码或文档生成后 -> 标记为 [开发完成/待验证]
> 2. 用户回复【验证通过】后 -> 标记为 [已完成] 并打钩 [x]
> 3. 未获得用户验证前，严禁把验证状态写成“通过”

**当前状态：** [验证失败 / 待修复]
**最后更新：** 2026-05-08（治理文档复审：刷新下方验证摘要以匹配当前检出）

## 1. 实时目录结构
```text
MediaTools/
├── app.py                    # Web 服务入口，启动 backend/api/server.py
├── config.py                 # 兼容配置入口，代理到 backend/config
├── cli/                      # CLI 主入口
├── backend/                  # 后端代码：API、services、agent、config
│   ├── api/
│   │   ├── server.py         # FastAPI 应用、静态资源、WebSocket、兼容端点
│   │   ├── setup.py          # 路由注册
│   │   └── routes/           # system/media/workspace/workbench/assets/files 等路由
│   ├── services/             # 媒体流程、工作区、任务中心、运行时、外部工具服务
│   ├── agent/                # AI 助手服务、工具定义、直连路由
│   └── config/               # `.env` 和环境变量配置
├── frontend/                 # React + TypeScript + Vite 桌面式工作台
│   └── src/apps/             # 下载器、工作台、文件管理、AI 助手、Adobe、审核等应用窗口
├── modules/                  # CLI 可调用底层能力：fetcher/encoder/decryptor/assets/workbench 等
├── adapters/                 # 外部工具、本机软件、第三方运行时适配
├── core/                     # 通用基础能力：认证、校验、日志、FFmpeg 等
├── patches/                  # 外部工具补丁规则
├── scripts/                  # 开发、维护、更新脚本
├── tests/                    # pytest 测试套件
├── docs/                     # 项目自有文档
├── vendor/                   # 第三方源码或嵌入工具
├── bin/                      # 本地二进制工具，通常不提交
├── runtime/                  # 运行时状态，通常不提交
└── projects/                 # 用户工作区和媒体产物，通常不提交
```

## 2. 验证状态 (Verification Status)
> **当前模块：** 项目治理文档初始化（01-05）
> **状态流转：** [未开始] -> [开发中] -> [待验证] -> [失败]
> **最近一次验证时间：** 2026-05-08（本机：`Python 3.14.2` / 项目约定仍为 3.11+）
> **验证结果：** 失败，需修复后重新验证

### 已执行验证结果
- `python -m pytest`：失败，收集阶段 **12** 个错误（本会话：`509` 条用例意图收集但被阻断）；示例：`tests/test_agent_service.py` 仍 `import backend.services.agent`，当前实现位于 `backend/agent/`。
- `python -m ruff check .`：失败，共 **80** 个 lint 问题，其中 **45** 个可用 `--fix` 自动修复（另含可被 unsafe fix 隐藏的项）；主要包括导入排序、空白行、未使用导入、未定义变量和裸 `except`。
- `python -m black --check .`：失败，**98** 个 Python 文件需要格式化。
- `python -m mypy backend --ignore-missing-imports`：失败，**95** 个类型错误（**25** 个文件），类型集中在 Optional、`subprocess`、`no-any-return`、OpenAI SDK 重载匹配等。
- `npm install`：未在本次复审重复执行（历史记录：曾通过并完成安装）；若以干净环境为准请重跑。
- `npm run typecheck`：未在本次复审重跑（历史记录：通过）。
- `npm run build`：未在本次复审重跑（历史记录：通过）。
- `npm test`：失败，共 **53** 个测试中 **50** 个通过：**3** 个失败分布在 `src/LeftNavbar.test.tsx`（后端重启成功后确认态，`Lesson-003`）与 **`src/LogViewer.test.tsx`（级别筛选项文案/行为，如下拉中 `Debug` 选项未匹配）**。
- `python app.py --help`：通过，Web 入口可解析参数。
- `python main.py --help`：失败，根目录不存在 `main.py`。
- `python -m cli.main --help`：通过，CLI 实际入口可用。
- `python -m cli.main fetcher ytdlp status`：命令可运行，结果为 `yt-dlp` 未安装，预期路径为 `bin/yt-dlp.exe`。

### 建议验证命令
```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy backend --ignore-missing-imports
cd frontend
npm run typecheck
npm test
npm run build
```

### 快速运行检查
```powershell
python app.py
python -m cli.main --help
python -m cli.main fetcher ytdlp status
```

## 3. 知识库关联 (Knowledge Link)
> **本次开发新产生的教训：** `Lesson-001`、`Lesson-002`、`Lesson-003`
> **相关历史风险：** `Risk-001` 至 `Risk-008`

## 4. 当前任务焦点
- **正在进行：** 基础验证仍为红灯：pytest 收集失败、前端 3 个用例失败、ruff/black/mypy 未绿；需在修复后整套重跑并把本快照数字再次对齐。
- **下一步：** 先修复基础验证红灯项；通过验证后，用户确认【验证通过】时再把本次初始化标记为已完成。

## 5. 当前稳定主线
```text
设置工作区
-> yt-dlp 下载视频和字幕
-> 字幕清洗/AI 分析
-> FFmpeg 自动切片或转码
-> 工作台人工复核
-> 素材管理/文件管理查看产物
```

## 6. 维护边界备忘
- Web 服务是能力最完整入口，CLI 适合批处理、调试和最小复现。
- `vendor/` 不属于项目自有业务层，修改第三方能力时优先通过 adapter、runtime service 或 patch 隔离。
- Adobe、CapCut、auditor、filebrowser、浏览器控制等能力依赖本机环境，开发和验证时必须声明环境假设。
- 工作区路径、文件预览、导出、删除和外部命令执行必须优先考虑安全校验。
