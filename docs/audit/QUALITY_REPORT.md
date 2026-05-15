# MediaTools 项目质量审查报告

> 审查日期：2026-05-15
> 审查范围：全项目代码（排除 `vendor/` 第三方源码）
> 审查工具：手动代码审查 + 自动化扫描

---

## 1. 审查概览

### 1.1 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐⭐ | 分层清晰，但有 2 处反向依赖 |
| 代码质量 | ⭐⭐⭐ | 存在 bare except、静默吞异常、any 滥用 |
| 工程化 | ⭐⭐ | 缺少 CI/CD、前端无 ESLint/Prettier |
| 测试覆盖 | ⭐⭐⭐ | 核心功能有测试，覆盖率阈值仅 30% |
| 文档完整度 | ⭐⭐⭐⭐ | 架构文档完整，docstring 覆盖率中等 |
| **综合** | **⭐⭐⭐ (3/5)** | 中等偏上，主要短板在工程化和类型安全 |

### 1.2 代码规模

| 指标 | 数量 |
|------|------|
| Python 文件总数 | 1592（含 vendor/） |
| TypeScript/TSX 文件总数 | 68 |
| 前端测试文件 | 9 个 |
| 后端测试文件 | ~60 个 |

---

## 2. 超大文件清单（>500 行）

### 2.1 TypeScript/TSX 文件

| 行数 | 文件路径 | 风险 |
|------|----------|------|
| **1824** | `frontend/src/apps/PhotoshopApp.tsx` | 🔴 严重超长，需拆分 |
| **794** | `frontend/src/apps/AEApp.tsx` | 🟡 偏长，建议拆分 |
| **651** | `frontend/src/apps/DownloaderApp.tsx` | 🟢 可接受（已有子目录） |
| **542** | `frontend/src/apps/MediaToolsApps.test.tsx` | 🟢 测试文件，可接受 |
| **524** | `frontend/src/apps/MediaToolsApps.tsx` | 🟡 临界值，建议关注 |

### 2.2 Python 文件（项目自身代码）

项目自身代码（排除 `vendor/`）**无超过 500 行的 Python 文件**。

---

## 3. 架构分析

### 3.1 后端分层架构

```
┌─────────────────────────────────────────────┐
│              API 层 (routes/)                │
│  server.py, setup.py, routes/*.py           │
└──────────────────┬──────────────────────────┘
                   │ 正向依赖
                   ▼
┌─────────────────────────────────────────────┐
│            Services 层 (services/)           │
│  workspace.py, media/, notification.py ...  │
└──────────────────┬──────────────────────────┘
                   │ 正向依赖
                   ▼
┌─────────────────────────────────────────────┐
│             Config 层 (config/)              │
│  settings.py (.env 加载 + 常量定义)          │
└─────────────────────────────────────────────┘
```

### 3.2 前端组件架构

- **桌面窗口模式**：16 个应用通过 `appRegistry.tsx` 统一注册
- **状态管理**：Zustand（4 个 store），类型化接口
- **API 层**：集中式 `api.ts`，自动注入 API Key 和 401 重试
- **样式隔离**：CSS 命名空间前缀（`dl-`、`fm-`、`ps-` 等）

### 3.3 模块依赖关系

```
backend/config/settings.py     ← 被 10+ 模块依赖（全局配置中心）
backend/services/workspace.py  ← 被 10+ 模块依赖（路径管理核心）
backend/api/routes/*.py        ← 路由之间零相互导入（良好）
backend/agent/tools.py         ← 纯函数设计，可独立测试（良好）
```

---

## 4. 耦合问题（逐文件）

### 4.1 反向依赖问题

#### 🔴 问题 1：service → agent 反向依赖

- **文件**：`backend/services/photoshop_copy_translate.py`
- **行号**：第 9 行
- **代码**：`from backend.agent.service import MediaAgentService`
- **问题**：Service 层导入 Agent 层的 `MediaAgentService`，打破了 `api → services → config` 的分层原则
- **影响**：`api/routes/photoshop` → `services/photoshop_copy_translate` → `agent/service` → `services/*` 形成复杂交叉依赖链
- **风险**：中等。当前不会导致运行时循环导入（Python import 缓存机制），但新增功能时容易触发循环依赖
- **修复建议**：
  1. 将翻译功能提取为独立的 LLM 调用服务（如 `services/llm_translate.py`），不依赖 Agent 类
  2. 或将其移入 agent 层作为 agent 工具

#### 🟡 问题 2：service → api 反向依赖

- **文件**：`backend/services/system_monitor.py`
- **行号**：第 16 行
- **代码**：`from backend.api.modules import build_module_catalog`
- **问题**：Service 层导入 API 层的 `build_module_catalog` 函数
- **影响**：`api/routes/system` → `services/system_monitor` → `api/modules` 形成间接引用链
- **风险**：低。`build_module_catalog` 是纯数据构造函数，无反向依赖，不会导致运行时循环
- **修复建议**：将 `modules.py` 移至 `services/` 层或独立为 `core/` 共享模块

### 4.2 超大组件问题

#### 🔴 问题 3：PhotoshopApp.tsx 过大（1824 行）

- **文件**：`frontend/src/apps/PhotoshopApp.tsx`
- **行数**：1824 行
- **问题**：单文件组件承载了扫描、编辑、执行、翻译、AI 聊天等全部功能
- **与 AEApp.tsx 的关系**：两者共享高度相似的 ticket/workorder 模板代码（119 处 vs 58 处 ticket 相关代码），属于典型的"复制粘贴式"开发
- **风险**：中等。可维护性差，修改一个功能可能影响其他功能
- **修复建议**：
  1. 提取共享的 `useAutomationTicket` hook
  2. 按功能拆分为子组件：`PhotoshopScanPanel`、`PhotoshopTicketEditor`、`PhotoshopExecutionPanel`、`PhotoshopTranslatePanel`
  3. 参考 `apps/downloader/` 的子目录组织模式

#### 🟡 问题 4：AEApp.tsx 偏长（794 行）

- **文件**：`frontend/src/apps/AEApp.tsx`
- **行数**：794 行
- **问题**：与 PhotoshopApp 共享大量重复的 ticket 管理逻辑
- **修复建议**：与 PhotoshopApp 一起重构，提取共享 hook

### 4.3 server.py 臃肿

#### 🟡 问题 5：server.py 内联过多端点

- **文件**：`backend/api/server.py`
- **行数**：404 行
- **内联端点**：
  - 第 169 行：`POST /api/agent/chat`
  - 第 199 行：`POST /api/agent/test-connection`
  - 第 220 行：`WebSocket /ws/jobs`
  - 第 236 行：`POST /api/jobs/cancel/{job_id}`
  - 第 245 行：`POST /api/system/shutdown`
  - 第 301 行：`WebSocket /ws/agent`
- **修复建议**：将 agent 相关端点移入 `routes/agent.py`，WebSocket 端点移入 `routes/websocket.py`

#### 🟡 问题 6：server.py 重复函数定义

- **文件**：`backend/api/server.py`
- **行号**：第 375 行和第 391 行
- **问题**：两个同名函数 `api_post_path_fallback`，后者会覆盖前者，属于代码 bug
- **修复建议**：删除第 375-388 行的重复定义

---

## 5. 代码质量问题（逐文件+行号）

### 5.1 bare except（3 处）

| # | 文件路径 | 行号 | 代码片段 | 修复建议 |
|---|----------|------|----------|----------|
| 1 | `backend/services/task_center.py` | 368 | `except:` → `task[field] = {}` | 改为 `except (json.JSONDecodeError, ValueError):` |
| 2 | `scripts/apply_patches.py` | 109 | `except:` → `pass` | 改为 `except (ValueError, IndexError):` |
| 3 | `scripts/migrate_all_imports.py` | 62 | `except:` → `print(...)` | 改为 `except (UnicodeDecodeError, OSError):` |

**风险**：🟡 中等。bare except 会捕获 `KeyboardInterrupt`、`SystemExit` 等不应被捕获的异常。

### 5.2 except Exception: pass（8 处）

| # | 文件路径 | 行号 | 场景 | 修复建议 |
|---|----------|------|------|----------|
| 1 | `backend/api/routes/browser.py` | 148 | CDP WebSocket 转发错误 | 添加 `logger.debug` |
| 2 | `backend/api/routes/browser.py` | 157 | WebSocket 关闭错误 | 添加 `logger.debug` |
| 3 | `backend/api/routes/photoshop.py` | 316 | 工单执行失败通知 | 添加 `logger.warning` |
| 4 | `backend/api/server.py` | 339 | WebSocket 发送错误 | 添加 `logger.debug` |
| 5 | `backend/services/log_buffer.py` | 65 | 日志缓冲写入失败 | 添加 `logger.debug` |
| 6 | `backend/services/log_buffer.py` | 67 | 日志缓冲外层写入失败 | 添加 `logger.debug` |
| 7 | `backend/services/notification.py` | 104 | 通知持久化失败 | 添加 `logger.warning` |
| 8 | `backend/services/notification.py` | 124 | 通知加载失败 | 添加 `logger.warning` |

**风险**：🟡 中等。静默吞掉异常会导致问题难以排查，至少应记录日志。

### 5.3 any 类型滥用

#### 5.3.1 catch (err: any) — 46 处

| 文件路径 | 数量 |
|----------|------|
| `frontend/src/apps/PhotoshopApp.tsx` | 10 |
| `frontend/src/apps/AEApp.tsx` | 5 |
| `frontend/src/apps/DownloaderApp.tsx` | 6 |
| `frontend/src/apps/file-manager/FileManagerPane.tsx` | 7 |
| `frontend/src/apps/SettingsApp.tsx` | 4 |
| `frontend/src/apps/MediaToolsApps.tsx` | 3 |
| `frontend/src/RightPanel.tsx` | 2 |
| `frontend/src/apps/BrowserApp.tsx` | 2 |
| 其他文件（各 1 处） | 7 |

**修复建议**：定义统一的错误类型，将 `catch (err: any)` 改为 `catch (err: unknown)` 并使用类型守卫。

#### 5.3.2 AnyRecord = Record<string, any> 定义位置（6 处）

| 文件路径 | 行号 |
|----------|------|
| `frontend/src/apps/AEApp.tsx` | 39 |
| `frontend/src/apps/PhotoshopApp.tsx` | 43 |
| `frontend/src/apps/MediaToolsApps.tsx` | 28 |
| `frontend/src/apps/WorkbenchApp.tsx` | 18 |
| `frontend/src/apps/AuditorApp.tsx` | 18 |
| `frontend/src/apps/mediatools/AutomationTaskDialog.tsx` | 6 |

**修复建议**：将 `AnyRecord` 提取到 `frontend/src/types.ts` 统一定义，或逐步为 API 响应定义具体类型。

#### 5.3.3 Promise<any> — 1 处（根源问题）

- **文件**：`frontend/src/api.ts`
- **行号**：第 12 行
- **代码**：`async function request(path: string, init: RequestInit = {}, retry = true): Promise<any>`
- **影响**：所有 50+ 个 API 函数的返回类型都是 `Promise<any>`，类型不安全从此处蔓延到全部组件
- **修复建议**：为 `request` 函数添加泛型参数 `request<T>(...)`，逐步为各 API 端点定义响应类型

### 5.4 重复代码模式

| 重复模式 | 位置 | 数量 |
|----------|------|------|
| `AnyRecord` 类型定义 | 6 个文件 | 6 处 |
| `catch (err: any)` 模式 | 14 个文件 | 46 处 |
| 轮询模式（`setInterval` + `useEffect`） | 6 个文件 | 6 处 |
| ticket/workorder 模板代码 | PhotoshopApp + AEApp | 大量 |

---

## 6. 工程化缺失项

### 6.1 CI/CD 配置

**状态**：🔴 完全缺失

| 检查项 | 结果 |
|--------|------|
| `.github/workflows/` | 不存在 |
| `.gitlab-ci.yml` | 不存在 |
| `Jenkinsfile` | 不存在 |
| `.circleci/` | 不存在 |

**影响**：代码质量检查（lint、type check、test）仅在本地通过 pre-commit 运行，无法保证团队协作和远程仓库的质量一致性。

**修复建议**：创建 `.github/workflows/ci.yml`，包含：
- Python: ruff lint + black check + mypy + pytest
- Frontend: typecheck + test + build

### 6.2 前端 Lint/Format

**状态**：🔴 完全缺失

| 检查项 | 结果 |
|--------|------|
| `.eslintrc*` / `eslint.config.*` | 不存在 |
| `.prettierrc*` | 不存在 |
| `package.json` 中的 lint 脚本 | 不存在 |

**影响**：前端代码风格完全依赖开发者自觉，无自动化检查。

**修复建议**：
1. 安装 ESLint（flat config）+ Prettier
2. 在 `package.json` 中添加 `lint` 和 `format` 脚本
3. 启用 tsconfig 中的 `noUnusedLocals` 和 `noUnusedParameters`

### 6.3 测试覆盖率

**状态**：🟡 阈值过低

| 指标 | 当前值 | 建议值 |
|------|--------|--------|
| pytest 覆盖率阈值 | 30% | 60%+ |
| 前端测试文件 | 9 个 | 需补充 8+ 个缺失组件的测试 |

**缺失测试的组件**：
- `App.tsx`（根组件）
- `AppLauncher.tsx`
- `DesktopIcons.tsx`
- `Window.tsx`
- `AIAssistantApp.tsx`
- `BrowserApp.tsx`
- `SettingsApp.tsx`
- `DownloaderSidebar.tsx`、`DownloaderToolbar.tsx` 等子组件

---

## 7. 风险评估矩阵

| # | 问题 | 文件路径 | 风险等级 | 影响范围 | 修复成本 | 优先级 |
|---|------|----------|----------|----------|----------|--------|
| 1 | service→agent 反向依赖 | `backend/services/photoshop_copy_translate.py:9` | 🔴 高 | 架构 | 中（2-3h） | P1 |
| 2 | PhotoshopApp 超大组件 | `frontend/src/apps/PhotoshopApp.tsx` | 🔴 高 | 可维护性 | 高（4-6h） | P1 |
| 3 | CI/CD 完全缺失 | `.github/workflows/` | 🔴 高 | 工程化 | 中（2-4h） | P1 |
| 4 | server.py 重复函数定义 | `backend/api/server.py:375,391` | 🔴 高 | 可靠性 | 低（10min） | P1 |
| 5 | api.ts Promise<any> | `frontend/src/api.ts:12` | 🟡 中 | 类型安全 | 高（4-8h） | P2 |
| 6 | 46 处 catch(err:any) | 多个前端文件 | 🟡 中 | 类型安全 | 中（2-4h） | P2 |
| 7 | 3 处 bare except | task_center.py:368 等 | 🟡 中 | 可靠性 | 低（30min） | P2 |
| 8 | 8 处 except:pass | 多个后端文件 | 🟡 中 | 可维护性 | 低（1h） | P2 |
| 9 | 前端无 ESLint/Prettier | `frontend/` | 🟡 中 | 工程化 | 低（1-2h） | P2 |
| 10 | service→api 反向依赖 | `backend/services/system_monitor.py:16` | 🟢 低 | 架构 | 低（30min） | P3 |
| 11 | 测试覆盖率 30% | `pyproject.toml` | 🟢 低 | 可靠性 | 持续 | P3 |
| 12 | 6 处 AnyRecord 重复定义 | 6 个前端文件 | 🟢 低 | 可维护性 | 低（30min） | P3 |

---

## 8. 改进建议（按优先级）

### 8.1 P1 — 高优先级（建议 1-2 周内完成）

| # | 改进项 | 涉及文件 | 预估工作量 | 具体操作 |
|---|--------|----------|-----------|----------|
| 1 | 修复 server.py 重复函数 | `backend/api/server.py` | 10 min | 删除第 375-388 行的重复 `api_post_path_fallback` |
| 2 | 消除 bare except | `task_center.py`, `apply_patches.py`, `migrate_all_imports.py` | 30 min | 替换为具体异常类型 |
| 3 | 修复 service→agent 反向依赖 | `backend/services/photoshop_copy_translate.py` | 2-3h | 提取独立的 LLM 翻译服务，不依赖 MediaAgentService |
| 4 | 添加 CI/CD 配置 | 新建 `.github/workflows/ci.yml` | 2-4h | 配置 Python lint/test + Frontend typecheck/test/build |

### 8.2 P2 — 中优先级（建议 1 个月内完成）

| # | 改进项 | 涉及文件 | 预估工作量 | 具体操作 |
|---|--------|----------|-----------|----------|
| 5 | 为 except:pass 添加日志 | 8 处，4 个文件 | 1h | 在 pass 前添加 `logger.debug` 或 `logger.warning` |
| 6 | 添加前端 ESLint + Prettier | `frontend/` | 1-2h | 安装配置 ESLint flat config + Prettier，添加 npm scripts |
| 7 | 定义 API 响应类型 | `frontend/src/api.ts` + 新建 `types/` | 4-8h | 为 request 添加泛型，逐步定义各端点响应类型 |
| 8 | 提取共享 ticket hook | `PhotoshopApp.tsx`, `AEApp.tsx` | 4-6h | 创建 `useAutomationTicket` hook，拆分子组件 |

### 8.3 P3 — 低优先级（建议持续改进）

| # | 改进项 | 涉及文件 | 预估工作量 | 具体操作 |
|---|--------|----------|-----------|----------|
| 9 | 修复 service→api 反向依赖 | `backend/services/system_monitor.py` | 30min | 将 `modules.py` 移至 `services/` 或 `core/` |
| 10 | 统一 AnyRecord 定义 | 6 个前端文件 | 30min | 提取到 `frontend/src/types.ts` |
| 11 | 提高测试覆盖率 | `pyproject.toml` + 新增测试 | 持续 | 逐步将阈值从 30% 提升到 60% |
| 12 | 补充缺失组件测试 | 8 个前端组件 | 持续 | 优先补充 AIAssistantApp、BrowserApp、SettingsApp |

---

## 附录 A：路由文件清单

| # | 文件路径 | 路由前缀 | 注册方式 |
|---|----------|----------|----------|
| 1 | `backend/api/routes/system.py` | `/api/system`, `/api/modules` | 工厂函数 |
| 2 | `backend/api/routes/media.py` | `/api/fetcher`, `/api/encoder`, `/api/decryptor` | 工厂函数 |
| 3 | `backend/api/routes/workspace.py` | `/api/workspace` | 工厂函数 |
| 4 | `backend/api/routes/workbench.py` | `/api/workbench` | 工厂函数 |
| 5 | `backend/api/routes/assets.py` | `/api/assets` | 工厂函数 |
| 6 | `backend/api/routes/files.py` | `/api/files` | 工厂函数 |
| 7 | `backend/api/routes/filebrowser.py` | `/api/filebrowser` | 直接导入 |
| 8 | `backend/api/routes/task_center.py` | `/api/tasks` | 直接导入 |
| 9 | `backend/api/routes/log.py` | `/api/logs` | 直接导入 |
| 10 | `backend/api/routes/model_config.py` | `/api/model-config` | 直接导入 |
| 11 | `backend/api/routes/notification.py` | `/api/notifications` | 直接导入 |
| 12 | `backend/api/routes/path_picker.py` | `/api/path-picker`（各路由写完整路径） | 直接导入 |
| 13 | `backend/api/routes/downloader_ai.py` | `/api/downloader/ai`（各路由写完整路径） | 工厂函数 |
| 14 | `backend/api/routes/photoshop.py` | `/api/photoshop` | 工厂函数 |
| 15 | `backend/api/routes/adobe.py` | `/api/adobe` | 工厂函数 |
| 16 | `backend/api/routes/auditor.py` | `/api/auditor` | 工厂函数 |
| 17 | `backend/api/routes/wechat.py` | `/api/wechat_moments` | 工厂函数 |
| 18 | `backend/api/routes/browser.py` | `/api/browser` | 直接导入 |

Agent 端点定义在 `backend/api/server.py`：
- `POST /api/agent/chat`（第 169 行）
- `POST /api/agent/test-connection`（第 199 行）
- `WebSocket /ws/agent`（第 301 行）

---

## 附录 B：前端应用清单

| # | 应用 ID | 标签 | 组件文件 | 启动器可见 |
|---|---------|------|----------|-----------|
| 1 | `dashboard` | 控制台 | `MediaToolsApps.tsx` | 否 |
| 2 | `fetcher` | 下载 | `DownloaderApp.tsx` | 是 |
| 3 | `agent` | AI助手 | `AIAssistantApp.tsx` | 是 |
| 4 | `browser` | 浏览器 | `BrowserApp.tsx` | 是 |
| 5 | `ps` | PS | `PhotoshopApp.tsx` | 是 |
| 6 | `photoshop` | Photoshop | `PhotoshopApp.tsx` | 否（别名） |
| 7 | `ae` | AE | `AEApp.tsx` | 是 |
| 8 | `filebrowser` | 文件管理 | `FileManagerApp.tsx` | 是 |
| 9 | `decryptor` | 音乐解密 | `MediaToolsApps.tsx` | 是 |
| 10 | `assets` | 素材库 | `MediaToolsApps.tsx` | 否 |
| 11 | `workbench` | 工作台 | `MediaToolsApps.tsx` | 否 |
| 12 | `encoder` | 转码 | `MediaToolsApps.tsx` | 否 |
| 13 | `auditor` | 审计 | `AuditorApp.tsx` | 否 |
| 14 | `workspace` | 工作区 | `MediaToolsApps.tsx` | 否 |
| 15 | `settings` | 设置 | `SettingsApp.tsx` | 否 |
| 16 | `logs` | 日志 | `LogViewer.tsx` | 否 |

---

## 附录 C：测试文件清单

### 前端测试（9 个）

| # | 文件路径 | 覆盖组件 |
|---|----------|----------|
| 1 | `frontend/src/apps/MediaToolsApps.test.tsx` | Dashboard, Encoder, Decryptor, Assets, Workspace, Photoshop, AE, Workbench, Auditor |
| 2 | `frontend/src/apps/DownloaderApp.test.tsx` | 下载管理器 |
| 3 | `frontend/src/apps/FileManagerApp.test.tsx` | 文件管理器 |
| 4 | `frontend/src/LeftNavbar.test.tsx` | 左侧导航栏 |
| 5 | `frontend/src/LogViewer.test.tsx` | 日志查看器 |
| 6 | `frontend/src/RightPanel.test.tsx` | 右侧面板 |
| 7 | `frontend/src/WindowContainer.test.tsx` | 窗口管理器 |
| 8 | `frontend/src/apps/mediatools/automation.test.ts` | 自动化工具函数 |
| 9 | `frontend/src/appPresentation.test.ts` | 窗口预设 |

### 后端测试

测试目录：`tests/`，约 60 个测试文件。配置在 `pyproject.toml` 中，覆盖率阈值 30%。

---

## 附录 D：pre-commit hooks 清单

| Repo | 版本 | Hooks |
|------|------|-------|
| `pre-commit/pre-commit-hooks` | v4.6.0 | trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-json, check-toml, check-merge-conflict, detect-private-key |
| `psf/black` | 24.4.2 | black（排除 vendor/ 和 frontend/） |
| `astral-sh/ruff-pre-commit` | v0.4.4 | ruff（排除 vendor/ 和 frontend/） |
| `pre-commit/mirrors-mypy` | v1.10.0 | mypy（排除 vendor/、frontend/、tests/） |
