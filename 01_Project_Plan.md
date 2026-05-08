# 项目开发蓝图 (Project Master Plan)

> **状态标识：** [已初始化]
> **最后初始化：** 2026-05-07 16:56

## 1. 项目定义 (Project Definition)
- **项目名称：** MediaTools
- **核心目标：** 构建一个面向内容创作与本地媒体处理的 Web 工作台，整合视频下载、字幕清洗与 AI 分析、FFmpeg 转码/切片、素材管理、文件管理、Adobe 自动化、CapCut 实验联动、素材审核与执行型 AI 助手。
- **主入口：**
  - Web 服务：`python app.py`
  - CLI：`python -m cli.main <module> ...`
  - 前端开发：`cd frontend && npm run dev`
- **项目模式 (Project Mode)：**
  - [x] **工程模式 (Engineering Mode)：** 适用：Web/App/大型插件。
    - 约束：强制 SRP；新增业务文件目标不超过 300 行；禁止循环依赖；API、service、module、adapter 分层清晰。
  - [ ] **脚本模式 (Script Mode)：** 适用：自动化脚本/简单工具。
    - 约束：仅允许在 `scripts/`、一次性迁移或小型维护工具中使用。
- **注释与文档语言：**
  - 项目治理文档、业务注释、用户可见说明优先使用中文。
  - 代码标识符遵循对应语言社区标准；第三方术语、协议名、环境变量和 API 字段保持英文。
- **当前阶段容忍度 (Stage Tolerance):**
  - [x] **MVP/原型阶段**：容忍黄灯，只修红灯。
  - [ ] **生产/交付阶段**：零容忍。红灯黄灯必须全修。

## 2. 技术栈矩阵 (Tech Stack Matrix)
| 维度 | 选择技术 | 用途/备注 |
| :--- | :--- | :--- |
| **后端语言** | Python 3.11+ | 媒体处理、API、CLI、AI Agent、外部工具编排 |
| **后端框架** | FastAPI、Uvicorn、Pydantic | Web API、WebSocket、请求/响应模型、静态前端服务 |
| **前端/UI** | React 18、TypeScript、Vite | 桌面式 Web 工作台和多窗口应用 |
| **前端状态** | Zustand、React Hooks | 全局状态、窗口状态、局部交互状态 |
| **AI/模型接口** | OpenAI-compatible API、`openai` SDK | 字幕分析、AI 助手、工具调用编排 |
| **媒体工具** | `yt-dlp`、FFmpeg/ffprobe、Unlock Music CLI | 下载、字幕、转码、切片、音频提取、解密 |
| **外部集成** | Adobe COM/CEP/ExtendScript、capcut-mate、filebrowser、auditor、Playwright/CDP | 专业软件自动化、实验剪辑联动、文件管理、审核、浏览器控制 |
| **配置管理** | `.env`、`python-dotenv`、`backend/config/settings.py` | API Key、端口、允许工作区、运行时路径 |
| **后端验证** | pytest、pytest-cov、ruff、black、mypy、pre-commit | 测试、覆盖率、格式化、静态检查 |
| **前端验证** | Vitest、TypeScript、Vite build | 单元测试、类型检查、构建验证 |
| **运行环境** | Windows 优先，跨平台尽量兼容 | 仓库包含 `.bat` 启动脚本；外部软件能力依赖本机环境 |

## 3. 动态架构规范 (Dynamic Architecture)
> **强制要求：** 新代码必须符合当前分层，优先复用已有服务、模块和适配器。

```text
MediaTools/
├── app.py                    # Web 服务入口，启动 backend/api/server.py
├── config.py                 # 兼容配置入口，代理到 backend/config
├── cli/                      # CLI 主入口
├── backend/                  # 后端 API、services、agent、config
│   ├── api/routes/           # 路由层，只做请求解析、校验和响应组织
│   ├── services/             # 跨模块业务编排、任务中心、工作区、运行时服务
│   ├── agent/                # AI 助手服务、工具定义和直连路由
│   └── config/               # 环境变量和全局配置
├── frontend/                 # React + TypeScript + Vite 前端
├── modules/                  # 可 CLI 调用的底层能力模块
├── adapters/                 # 外部工具、本机软件、第三方运行时差异隔离层
├── core/                     # 通用基础能力：认证、校验、日志、FFmpeg 等
├── patches/                  # 外部工具补丁规则
├── scripts/                  # 开发、构建、维护脚本
├── tests/                    # Python 测试
├── docs/                     # 项目自有文档
├── vendor/                   # 第三方源码或嵌入工具，不视为自有业务层
├── bin/                      # 本地二进制工具，通常不提交
├── runtime/                  # 运行时状态，通常不提交
└── projects/                 # 用户工作区和产物，通常不提交
```

### 依赖方向
- `frontend/` 只通过 HTTP/WebSocket 调用 API，不依赖 Python 文件结构。
- `backend/api/routes/` 不承载复杂业务，不直接拼接复杂 shell 命令。
- 跨模块流程放入 `backend/services/`，例如下载-分析-切片工作流、任务中心、运行时管理。
- 单步可复用能力放入 `modules/`，并尽量保持 CLI 可测。
- 外部工具发现、版本检查、命令执行、平台差异放入 `adapters/`、`core/` 或 `backend/services/runtime/`。
- `vendor/` 只承载第三方上游代码和文档，不应反向依赖项目服务。

### 稳定主线
```text
yt-dlp 下载
-> 字幕清洗/AI 分析
-> FFmpeg 切片或转码
-> 工作台复核
-> 工作区素材管理
```

### 扩展能力定位
- Adobe / Photoshop / After Effects：专业软件自动化扩展，强依赖本机软件、权限、插件和版本。
- CapCut / capcut-mate：实验剪辑联动，不作为唯一导出路径。
- auditor：素材审核扩展，环境相关。
- filebrowser：文件浏览和管理扩展，需隔离第三方运行时。

## 4. 验证与交付标准
> **说明：** 代码修改完成后必须先审查，再给出可复制验证命令。未获得用户“验证通过”前，不得把 `03_Context_Snapshot.md` 标记为通过。

### 后端基础验证
```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy backend --ignore-missing-imports
```

### 前端基础验证
```powershell
cd frontend
npm run typecheck
npm test
npm run build
```

### 运行验证
```powershell
python app.py
python -m cli.main --help
python -m cli.main fetcher ytdlp status
```

### 完成定义
- 修改范围符合 `docs/DEPENDENCIES.zh.md` 的依赖方向。
- 不新增硬编码密钥，敏感配置必须进入 `.env` 或环境变量。
- 新增 API 有必要的请求校验、错误处理和测试。
- 长任务接入任务中心或提供可观察日志。
- 外部工具能力必须有状态检查、缺失工具提示和可降级说明。
- 文档改动不得把未验证工作标记为已通过。

## 5. 开发阶段拆解 (Roadmap)
> **任务状态图例：**
> - [ ] 待开始
> - [x] 已完成 @ [YYYY-MM-DD HH:MM]
> - [⏸] **挂起/延后 (Postponed)**：因技术瓶颈或依赖缺失，暂时跳过。
> - [R] **返工 (Rework)**：验证失败，正在修复。

### Phase 0：项目治理初始化
- [x] 重写 README、工作流、架构和核心专题文档 @ 2026-05-06
- [R] 初始化 01-05 项目治理文档 @ 2026-05-07 18:15
  - 验证发现：根目录不存在 `main.py`，CLI 实际入口为 `python -m cli.main`；已修正本治理文档中的入口描述。
  - 仍待处理：后端测试、lint、format、mypy 与前端依赖安装后的验证。

### Phase 1：稳定生产主线
- [ ] 巩固 `yt-dlp + 字幕分析 + FFmpeg 切片 + 工作台复核` 的端到端体验
- [ ] 统一 Web、CLI、AI 助手复用的媒体服务接口
- [ ] 补齐下载、字幕、分析、切片的失败分支和任务中心日志

### Phase 2：工作区与素材管理
- [ ] 强化工作区路径安全、允许根目录、预览大小和扫描数量限制
- [ ] 优化素材扫描、文件管理、预览和导出结果索引
- [ ] 将工作区产物结构和 UI 操作保持一致

### Phase 3：外部工具与运行时
- [ ] 统一 FFmpeg、yt-dlp、um-cli、filebrowser、Adobe、auditor 的状态检查和安装提示
- [ ] 将本机软件差异继续收敛到 adapter/runtime 层
- [ ] 为环境相关能力提供最小可验证命令和 mock 测试

### Phase 4：前端工程化
- [ ] 继续拆分大型应用窗口，复用窗口、任务、日志、路径选择和状态组件
- [ ] 收敛 API 类型和请求 helper，减少组件深层直接拼 API
- [ ] 保持 `typecheck`、Vitest、生产构建可通过

### Phase 5：质量与交付
- [ ] 将当前覆盖率门槛从 30% 逐步提升
- [ ] 增加性能基准测试的真实实现，替换占位 TODO
- [ ] 完善 pre-commit、CI 或本地一键验证脚本
