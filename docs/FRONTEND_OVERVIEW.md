# 前端结构

MediaTools 前端是 React + TypeScript + Vite 应用，采用桌面式工作台界面。

## 入口

```text
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/AppLayout.tsx
```

生产构建：

```powershell
cd frontend
npm run build
```

开发服务：

```powershell
cd frontend
npm run dev
```

## 主要应用

| 应用 | 文件 |
|---|---|
| 下载器 | `frontend/src/apps/DownloaderApp.tsx` |
| 工作台 | `frontend/src/apps/WorkbenchApp.tsx` |
| 文件管理 | `frontend/src/apps/FileManagerApp.tsx` |
| 浏览器控制 | `frontend/src/apps/BrowserApp.tsx` |
| AI 助手 | `frontend/src/apps/AIAssistantApp.tsx` |
| Photoshop | `frontend/src/apps/PhotoshopApp.tsx` |
| After Effects | `frontend/src/apps/AEApp.tsx` |
| 素材审核 | `frontend/src/apps/AuditorApp.tsx` |
| MediaTools 工具集 | `frontend/src/apps/MediaToolsApps.tsx` |
| 设置 | `frontend/src/apps/SettingsApp.tsx` |

应用注册与窗口管理：
- `frontend/src/appRegistry.tsx`：应用注册表。
- `frontend/src/AppLauncher.tsx`：应用启动器。
- `frontend/src/Window.tsx`、`WindowContainer.tsx`：窗口容器。
- `frontend/src/LeftNavbar.tsx`、`RightPanel.tsx`：主界面区域。
- `frontend/src/windowStore.ts`：窗口状态。

领域拆分：
- `frontend/src/apps/downloader/`：下载器子组件、表格、表单、状态栏。
- `frontend/src/apps/file-manager/`：文件管理导航、控件、类型定义。
- `frontend/src/apps/mediatools/`：MediaTools 通用控件（如 FontPicker、AutomationTaskDialog）和自动化任务 UI。
- `frontend/src/icon-library/`：应用图标资源。

## 公共结构

- `frontend/src/api.ts`：API 调用入口。
- `frontend/src/store.ts`：全局状态。
- `frontend/src/windowStore.ts`：窗口状态。

## 测试

```powershell
cd frontend
npm test
npm run typecheck
```

测试文件通常和被测文件同目录，后缀为 `.test.ts` 或 `.test.tsx`。

## 维护建议

- 新应用窗口放在 `frontend/src/apps/`。
- 大型应用继续按领域拆到子目录。
- API 类型和调用不要散落在组件深处，优先集中到 `api.ts` 或领域 helper。
- 窗口、导航、任务状态等通用体验复用现有组件。
