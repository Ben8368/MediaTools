# 新功能构思池 (Feature Backlog)

**说明：** 本文存放待评估功能、工程化改进和模块影响预判。任何新功能开发前，必须先补齐“前置依赖检查”和“模块影响评估”；依赖未满足时禁止进入编码。

## 1. 提交流程
1. 填写功能卡片。
2. 明确是否属于核心主线、工程化改进或环境相关扩展。
3. 完成前置依赖检查。
4. 完成预计影响模块和风险评估。
5. 给出最小验证命令或人工验证路径。
6. 经用户确认优先级后进入开发。

## 2. 功能卡片模板
- **功能 ID：** Feature-XXX
- **功能名称：**
- **提交时间：**
- **类型：** [核心主线 / 工程化 / 前端体验 / 外部工具 / 实验能力 / 文档]
- **描述：**
- **用户价值：**
- **前置依赖检查：**
  - 技术依赖：
  - 本机环境依赖：
  - API/密钥依赖：
  - 相关模块是否已初始化：
- **预计影响模块：**
  - 后端：
  - 前端：
  - CLI：
  - 测试：
  - 文档：
- **数据与安全影响：**
  - 工作区路径：
  - 文件读写：
  - 外部命令：
  - 敏感配置：
- **验证思路：**
  - 自动化测试：
  - 手工验证：
  - 回归范围：
- **降级/回滚策略：**
- **状态：** [待评估]

---

## 3. 当前优先级原则
- 优先保护稳定主线：`yt-dlp + 字幕分析 + FFmpeg 切片 + 工作台复核 + 工作区素材管理`。
- 环境相关能力（Adobe、CapCut、auditor、filebrowser、浏览器控制）必须先补状态检查和缺失依赖提示。
- Web、CLI、AI 助手应尽量复用同一 service，不为单一入口复制业务流程。
- 新增前端应用或大型 UI 必须按领域拆分组件，并复用窗口、任务、日志、路径选择等现有能力。
- 测试覆盖优先覆盖路径安全、失败分支、外部工具缺失、长任务状态和 API 合约。

## 4. 功能列表

### Feature-001：稳定主线端到端回归
- **提交时间：** 2026-05-07 16:56
- **类型：** 核心主线
- **描述：** 为下载、字幕清洗/AI 分析、FFmpeg 切片、工作台复核、素材查看建立端到端回归清单。
- **用户价值：** 保证最常用生产链路稳定，减少外部扩展对核心能力的干扰。
- **前置依赖检查：**
  - 技术依赖：`yt-dlp`、FFmpeg/ffprobe、AI API 配置。
  - 本机环境依赖：`bin/` 或 `PATH` 中可访问必要二进制。
  - API/密钥依赖：`TEC_CHI_API_KEY`、`OPENAI_BASE_URL`、`ANALYSIS_MODEL`。
  - 相关模块是否已初始化：`backend/services/media/`、`modules/fetcher`、`modules/encoder`、`frontend/src/apps/WorkbenchApp.tsx` 已存在。
- **预计影响模块：**
  - 后端：`backend/services/media/`、`backend/services/fetcher.py`、`backend/services/encoder.py`、`backend/api/routes/media.py`、`backend/api/routes/workbench.py`
  - 前端：下载器、工作台、任务中心、日志查看
  - CLI：`python -m cli.main fetcher ...`、`python -m cli.main encoder ...`
  - 测试：`tests/test_media_*`、`tests/test_workbench.py`、API 路由测试
  - 文档：`WORKFLOW.md`、`docs/API_OVERVIEW.md`
- **验证思路：** 自动化覆盖 service/API；人工验证一条小视频下载、分析、切片、工作台复核流程。
- **状态：** [待评估]

### Feature-002：外部工具状态检查统一
- **提交时间：** 2026-05-07 16:56
- **类型：** 工程化 / 外部工具
- **描述：** 统一 FFmpeg、yt-dlp、um-cli、filebrowser、Adobe、auditor、Playwright/CDP 等工具的发现、版本、缺失提示和状态接口。
- **用户价值：** 用户能快速知道当前机器缺什么，减少环境问题排查成本。
- **前置依赖检查：**
  - 技术依赖：现有 `backend/services/runtime/`、`adapters/`、`modules/*` 状态能力。
  - 本机环境依赖：各工具安装情况不一致，必须允许缺失。
  - API/密钥依赖：通常无；Adobe/AI 场景按功能另行检查。
  - 相关模块是否已初始化：runtime/adapters 已存在但能力分散。
- **预计影响模块：**
  - 后端：`backend/services/runtime/`、`adapters/`、`backend/api/routes/system.py`
  - 前端：设置页、系统状态、任务中心提示
  - CLI：各模块 `status` 命令
  - 测试：外部工具 mock、状态接口测试
  - 文档：`docs/EXTERNAL_TOOLS.md`
- **验证思路：** mock 存在/缺失/版本异常三类状态；人工在缺失工具环境下检查提示。
- **状态：** [待评估]

### Feature-003：任务中心和日志可观察性增强
- **提交时间：** 2026-05-07 16:56
- **类型：** 工程化 / 前端体验
- **描述：** 补齐长任务状态、取消、错误详情、日志关联和前端展示一致性。
- **用户价值：** 下载、转码、解密、审核、Adobe 执行等耗时任务更容易跟踪和排错。
- **前置依赖检查：**
  - 技术依赖：`backend/services/task_center.py`、WebSocket job registry、`frontend/src/LogViewer.tsx`。
  - 本机环境依赖：无强依赖。
  - API/密钥依赖：无。
  - 相关模块是否已初始化：任务中心和日志查看已存在。
- **预计影响模块：**
  - 后端：`backend/api/runtime.py`、`backend/services/task_center.py`、相关 job service
  - 前端：任务中心、右侧面板、日志查看、下载器状态栏
  - CLI：可选，输出 job id 或日志路径
  - 测试：`tests/test_task_center.py`、`tests/test_api_task_center.py`
  - 文档：`docs/TASK_QUEUE.md`
- **验证思路：** 构造成功、失败、取消、并发任务；检查前端状态和日志一致。
- **状态：** [待评估]

### Feature-004：工作区路径安全与文件操作回归
- **提交时间：** 2026-05-07 16:56
- **类型：** 核心主线 / 安全
- **描述：** 系统性覆盖工作区选择、路径选择、文件预览、导出、删除、扫描限制和允许根目录。
- **用户价值：** 降低误操作和越权访问本机文件的风险。
- **前置依赖检查：**
  - 技术依赖：`backend/services/workspace.py`、`backend/services/path_picker.py`、`core/validation.py`。
  - 本机环境依赖：Windows 路径、盘符、符号链接等需重点验证。
  - API/密钥依赖：绑定非本机时需 `API_SECRET_KEY`。
  - 相关模块是否已初始化：工作区、路径选择、文件管理已存在。
- **预计影响模块：**
  - 后端：workspace、path picker、files、assets、media export
  - 前端：文件管理、路径选择、设置页
  - CLI：涉及输入/输出路径的命令
  - 测试：路径安全、文件操作、API 路由测试
  - 文档：`WORKFLOW.md`、`docs/DIRECTORY_STRUCTURE.md`
- **验证思路：** 覆盖允许路径、禁止路径、相对路径、盘符边界、预览大小、扫描数量限制。
- **状态：** [待评估]

### Feature-005：前端 API 类型与请求层收敛
- **提交时间：** 2026-05-07 16:56
- **类型：** 前端体验 / 工程化
- **描述：** 将分散在组件内的请求、响应类型和错误处理逐步集中到 `frontend/src/api.ts` 或领域 helper。
- **用户价值：** 降低前端维护成本，减少 API 变更时的漏改。
- **前置依赖检查：**
  - 技术依赖：React、TypeScript、现有 `frontend/src/api.ts`。
  - 本机环境依赖：Node.js 20+。
  - API/密钥依赖：遵循后端认证配置。
  - 相关模块是否已初始化：前端应用和测试框架已存在。
- **预计影响模块：**
  - 后端：必要时同步 OpenAPI/模型命名
  - 前端：`api.ts`、各 app、领域子组件
  - CLI：无
  - 测试：Vitest、typecheck、构建
  - 文档：`docs/FRONTEND_OVERVIEW.md`
- **验证思路：** `npm run typecheck`、`npm test`、`npm run build`，并手工打开主要窗口。
- **状态：** [待评估]

### Feature-006：测试覆盖率与性能基准补齐
- **提交时间：** 2026-05-07 16:56
- **类型：** 工程化
- **描述：** 将当前覆盖率门槛从 30% 逐步提升，并把 `tests/test_performance.py` 中的 TODO 占位替换为真实基准或明确跳过条件。
- **用户价值：** 提高回归可信度，避免关键媒体流程在重构中退化。
- **前置依赖检查：**
  - 技术依赖：pytest、pytest-cov、性能测试输入样本或 mock。
  - 本机环境依赖：性能测试需避免强依赖大型真实媒体文件。
  - API/密钥依赖：AI 分析基准应 mock，避免消耗真实额度。
  - 相关模块是否已初始化：pytest 配置和测试目录已存在。
- **预计影响模块：**
  - 后端：核心 service/module 测试
  - 前端：可选补齐 Vitest 覆盖
  - CLI：模块命令 smoke test
  - 测试：`tests/test_performance.py`、coverage 配置
  - 文档：`README.md`、`03_Context_Snapshot.md`
- **验证思路：** 分阶段提高覆盖率门槛；性能测试默认使用小样本或 mock，避免 CI 不稳定。
- **状态：** [待评估]
