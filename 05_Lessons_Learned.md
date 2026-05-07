# 项目经验与避坑指南 (Lessons Learned)

> **核心作用：** 这是项目的“法律”和“历史”。Cursor 在写代码前**必须**阅读此文档。
> **当前结论：** 截至 2026-05-07，本文件未发现既有用户报错记录；本次初始化只登记从当前代码和文档审查中归纳出的工程风险。

## 1. 项目铁律 (Project Laws)
> **说明：** 由报错、审查或架构边界转化而来的永久性规范。一旦写入，等同于 Rule 文档。

### Law-001：稳定主线优先
- **来源：** `README.md`、`WORKFLOW.zh.md`、`docs/TOOL_FACTIONS.zh.md`
- **规则：** 新增功能不得破坏 `yt-dlp + 字幕分析 + FFmpeg 切片 + 工作台复核 + 工作区素材管理` 这条稳定主线。
- **预防方式：** 修改媒体流程时，优先覆盖下载、字幕、分析、切片、工作台和素材查看的回归验证。

### Law-002：路由层必须保持轻量
- **来源：** `ARCHITECTURE.zh.md`、`docs/MODULE_DEPENDENCIES.zh.md`
- **规则：** `backend/api/routes/` 只处理请求解析、校验和响应组织；复杂业务必须下沉到 `backend/services/`。
- **预防方式：** 新增 API 时先设计 service 函数，再让 Web、CLI、Agent 复用。

### Law-003：外部工具差异必须隔离
- **来源：** `docs/EXTERNAL_TOOLS.zh.md`、`docs/TOOL_FACTIONS.zh.md`
- **规则：** FFmpeg、yt-dlp、um-cli、Adobe、CapCut、auditor、filebrowser、浏览器控制等外部工具不得把路径、端口、命令和平台差异散落在前端或路由中。
- **预防方式：** 工具发现、版本检查、启动/停止、命令执行放入 adapter、runtime service 或 module wrapper。

### Law-004：工作区路径安全优先
- **来源：** `WORKFLOW.zh.md`、`docs/MODULE_DEPENDENCIES.zh.md`
- **规则：** 文件浏览、预览、导出、删除、扫描、外部命令输入输出必须经过工作区和允许根目录校验。
- **预防方式：** 修改路径相关逻辑时必须覆盖允许路径、禁止路径、相对路径、Windows 盘符和大小限制。

### Law-005：敏感配置不得入库
- **来源：** `README.md`、`app.py`、`backend/config`
- **规则：** API Key、模型服务地址、生产端口和非本机绑定密钥必须来自 `.env` 或环境变量。
- **预防方式：** 示例只写占位符；绑定非本机地址时必须校验 `API_SECRET_KEY`。

### Law-006：`vendor/` 不是自有业务层
- **来源：** `README.md`、`docs/DIRECTORY_STRUCTURE.zh.md`、`docs/VENDOR_ORGANIZATION.zh.md`
- **规则：** `vendor/` 内 README、CHANGELOG、源码和测试属于上游项目，不作为 MediaTools 自有事实来源，默认不改上游源码。
- **预防方式：** 需要改第三方行为时，优先使用 `patches/`、adapter、runtime service 或 wrapper。

### Law-007：未验证不得标记通过
- **来源：** `02_Cursor_Rules.md`、`03_Context_Snapshot.md`
- **规则：** 代码或文档生成后只能标记为“待验证”；只有用户明确回复【验证通过】后，才能把上下文快照或任务状态改为“通过/已完成”。
- **预防方式：** 每次最终回复给出验证命令并停止，等待用户反馈。

### Law-008：Git 是项目真实时间线
- **来源：** 项目治理约定、`.cursor/rules/project-governance.mdc`
- **规则：** Git 历史记录代码和文档的真实演进；`03_Context_Snapshot.md` 只记录当前状态，`04_New_Features.md` 记录功能规划，`05_Lessons_Learned.md` 记录失败复盘和预防规则。
- **预防方式：** 可验证阶段完成后再提交；多 Agent 或多窗口并行开发时优先使用独立 branch 或 worktree，避免多个 Agent 混改同一个 checkout。

## 2. 风险登记 (Risk Register)

### Risk-001：外部软件和本机环境不一致
- **影响范围：** Adobe、CapCut/capcut-mate、auditor、filebrowser、Playwright/CDP、FFmpeg、yt-dlp、um-cli。
- **风险表现：** 开发者机器可用，但用户机器缺二进制、端口冲突、权限不足或软件版本不兼容。
- **预防措施：** 所有环境相关能力必须提供状态检查、缺失依赖提示、最小命令验证和可降级路径。

### Risk-002：AI 分析依赖字幕质量和 API 可用性
- **影响范围：** 字幕分析、AI 助手、自动切片建议。
- **风险表现：** 字幕缺失、时间轴不准、模型不可用、API Key 错误或结果质量不稳定。
- **预防措施：** 提供字幕清洗/转换失败提示；AI 调用失败时保留手动工作台复核路径；测试中 mock AI API。

### Risk-003：路径和文件操作可能越界
- **影响范围：** 工作区、文件管理、素材扫描、预览、导出、删除、外部命令输入输出。
- **风险表现：** 访问非允许目录、误删文件、读取过大文件、路径穿越或 Windows 盘符边界错误。
- **预防措施：** 统一走路径校验和允许根目录；限制预览大小和扫描数量；增加路径安全测试。

### Risk-004：Web、CLI、Agent 逻辑重复导致行为分叉
- **影响范围：** 下载、转码、解密、工作台、AI 助手工具调用。
- **风险表现：** 同一功能在 Web 可用、CLI 不可用，或错误处理、输出路径不一致。
- **预防措施：** 编排逻辑集中到 `backend/services/`；CLI 和 Agent 调用同一 service 或 module 能力。

### Risk-005：前端 API 类型分散
- **影响范围：** `frontend/src/apps/*`、`frontend/src/api.ts`。
- **风险表现：** API 字段变化后组件漏改，运行时才暴露错误。
- **预防措施：** API 类型、请求 helper 和错误处理集中管理；修改 API 后运行 `npm run typecheck`、`npm test`、`npm run build`。

### Risk-006：覆盖率门槛偏低且性能测试存在占位
- **影响范围：** 回归测试可信度、媒体流程性能。
- **风险表现：** `pyproject.toml` 当前覆盖率门槛为 30%，`tests/test_performance.py` 存在 TODO 占位。
- **预防措施：** 优先补关键 service/API 失败分支测试；性能测试使用小样本或 mock，避免依赖大型真实媒体。

### Risk-007：历史专题文档可能滞后于当前实现
- **影响范围：** 架构判断、功能定位、外部工具能力。
- **风险表现：** 误把早期设计文档或 `vendor/` 上游文档当作当前实现事实。
- **预防措施：** 优先参考根 README、`WORKFLOW.md`、`ARCHITECTURE.md`、`docs/README.md`、01-05 治理文档和当前代码。

### Risk-008：CLI 入口文档可能漂移
- **影响范围：** README、治理文档、CLI 示例、开发者入门验证命令。
- **风险表现：** 文档写 `python main.py`，但当前仓库根目录不存在 `main.py`，实际可用入口为 `python -m cli.main`。
- **预防措施：** 写入或修改 CLI 示例前必须用 `Glob` 或实际命令验证入口文件存在；最小 CLI 验证统一使用 `python -m cli.main --help`。

## 3. 错题记录 (Error Log)
> **说明：** 记录具体的报错代码、复现条件、修复方案和未来预防方式。

### Lesson-001：文档引用不存在的根 CLI 入口
- **发生时间：** 2026-05-07 18:15
- **触发场景：** 执行治理文档验证命令 `python main.py --help`。
- **报错信息：** `can't open file 'D:\\Ben\\Cursor\\MediaTools\\main.py': [Errno 2] No such file or directory`
- **根因：** 文档沿用了历史兼容入口 `main.py`，但当前仓库根目录没有该文件，实际 CLI 入口为 `cli/main.py`。
- **修复方案：** 将 01-05 治理文档中的最小 CLI 命令改为 `python -m cli.main ...`。
- **未来预防：** 文档中新增入口命令前必须先验证文件存在和命令可执行。
- **关联文件/测试：** `01_Project_Plan.md`、`02_Cursor_Rules.md`、`03_Context_Snapshot.md`、`04_New_Features.md`、`05_Lessons_Learned.md`

### Lesson-002：测试导入路径滞后于后端重构
- **发生时间：** 2026-05-07 18:15
- **触发场景：** 执行 `python -m pytest`。
- **报错信息：** 收集阶段 16 个导入错误，测试仍引用 `backend.services.api_*`、`backend.services.media_*`、`services.*` 等旧路径。
- **根因：** 后端已迁移到 `backend/api/routes/`、`backend/services/media/`、`backend/services/runtime/` 等新结构，但部分测试和兼容层没有同步。
- **修复方案：** 将测试 patch/import 目标改到真实模块路径，或补齐明确需要保留的兼容 re-export。
- **未来预防：** 模块迁移必须同步运行测试收集，并在 `docs/MODULE_DEPENDENCIES.md` 和测试 helper 中维护唯一事实来源。
- **关联文件/测试：** `tests/test_api_*`、`tests/test_media_*`、`tests/test_filebrowser_runtime.py`、`tests/test_photoshop_state.py`

### Lesson-003：前端测试期望与当前 UI 行为不一致
- **发生时间：** 2026-05-07 18:18
- **触发场景：** 执行 `npm test`。
- **报错信息：** `LeftNavbar.test.tsx` 期待 `restart-backend` 按钮，但当前电源菜单只渲染 `shutdown-backend`。
- **根因：** 前端测试与当前 `LeftNavbar` 行为或产品设计未对齐。
- **修复方案：** 确认产品是否应保留“重启后端”；若应保留，则恢复 UI；若已移除，则更新测试。
- **未来预防：** 修改 UI 行为时同步更新可访问标签和对应测试，避免仅通过 typecheck/build 掩盖行为回归。
- **关联文件/测试：** `frontend/src/LeftNavbar.test.tsx`、`frontend/src/LeftNavbar.tsx`

### Lesson-004：启动脚本同时受导入漂移与端口残留影响
- **发生时间：** 2026-05-07 19:19
- **触发场景：** 执行 `start_mediatools.bat` 或 `start_mediatools_dev.bat` 启动项目。
- **报错信息：** 后端日志出现 `ModuleNotFoundError: No module named 'backend.services.runtime'`；开发模式还可能因 `5173` 已被其他 Vite 进程占用而退出。
- **根因：** 路由已引用 `backend.services.runtime.filebrowser`，但 runtime service 目录缺失；同时 `.gitignore` 的 `runtime/` 会误忽略源码目录 `backend/services/runtime/`。开发脚本还只清理当前仓库路径下的 Vite，无法处理旧路径残留进程。
- **修复方案：** 补齐 `backend/services/runtime/filebrowser.py`，将 `.gitignore` 的运行时目录规则收窄为 `/runtime/`，并让 dev 脚本清理占用 `5173` 的 Vite 进程、按真实监听 PID 判断 reload 后端是否启动。
- **未来预防：** 新增名为 `runtime` 的源码包时必须检查 Git ignore 命中情况；启动脚本不能只看父进程是否存活，还应检查实际监听端口和进程命令。
- **关联文件/测试：** `backend/services/runtime/filebrowser.py`、`.gitignore`、`start_mediatools_dev.bat`

### 错题记录模板
- **Lesson ID：** Lesson-XXX
- **发生时间：**
- **触发场景：**
- **报错信息：**
- **根因：**
- **修复方案：**
- **未来预防：**
- **关联文件/测试：**

## 4. 写代码前检查清单
- 是否触及稳定主线？如果触及，必须说明回归范围。
- 是否依赖外部工具或本机软件？如果依赖，必须提供状态检查和缺失提示。
- 是否读写工作区或本机文件？如果读写，必须经过路径安全校验。
- 是否新增 API？如果新增，路由应保持轻量，复杂逻辑下沉 service。
- 是否新增长任务？如果新增，必须有状态、日志、取消或失败可见性。
- 是否需要真实 API Key 或模型？如果需要，测试必须 mock，文档只能写占位符。
- 是否修改 `03_Context_Snapshot.md` 的验证状态？如果未获用户【验证通过】，只能写“待验证”。
