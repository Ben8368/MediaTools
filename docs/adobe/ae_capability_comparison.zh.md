# After Effects 能力对比：CEP/Atom 与 COM

> 中文专有文档，暂无英文版本。

MediaTools 当前的 After Effects 自动化主要走 COM + ExtendScript 路线。Atom/CEP 资料用于能力对照和实现参考。

## 对比

| 维度 | CEP / Atom | COM + ExtendScript |
|---|---|---|
| 运行位置 | AE 内部面板 | 外部 Python 进程 |
| 调用方式 | `CSInterface.evalScript()` | `AfterFX.Application.DoScript()` |
| UI | 插件自带 HTML/JS UI | MediaTools Web UI |
| 部署 | 安装 AE 插件 | 本机 COM/AE 自动化环境 |
| 适合场景 | 设计师在 AE 内交互使用 | 后端批处理和任务中心执行 |

核心事实：两者最终都可以调用 ExtendScript。只要能力来自 AE 的 JSX API，通常都可以评估是否迁移到 COM 路线。

## 当前 MediaTools AE 能力方向

相关代码：

- `modules/adobe/after_effects/scan.py`
- `modules/adobe/after_effects/service.py`
- `modules/adobe/after_effects/project_ops.py`
- `modules/adobe/after_effects/execution.py`
- `services/api_adobe_routes.py`
- `frontend/src/apps/AEApp.tsx`

API 涉及：

- 状态检查
- 工程扫描
- 票据列表和详情
- 票据编辑和执行
- 执行状态和取消
- 字体列表
- 检查点创建、回滚、列表
- 渲染队列添加、启动、状态

## 能力迁移优先级

优先迁移/维护：

- 工程扫描
- 文本层识别和修改
- 字体枚举
- 执行前检查点
- 执行日志和回滚

谨慎处理：

- 复杂 UI 交互
- 插件专属状态
- 依赖 AE 面板生命周期的能力

## 维护建议

- 新 AE 后端能力优先放入 `modules/adobe/after_effects/`。
- Web 路由只做请求和响应组织。
- 任何会修改工程的操作都应考虑检查点和失败恢复。
- 本机软件相关错误需要返回可读诊断信息。
