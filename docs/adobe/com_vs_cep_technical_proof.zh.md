# COM vs CEP 技术说明

> 中文专有文档，暂无英文版本。

本文说明为什么 MediaTools 可以用 COM + ExtendScript 实现一部分 CEP/Atom 能力。

## 核心结论

CEP 和 COM 的入口不同，但很多 AE 自动化最终都会进入同一个 ExtendScript 能力面：

```text
CEP panel
-> CSInterface.evalScript()
-> ExtendScript
-> After Effects project/layer/render APIs

Python COM
-> AfterFX.Application.DoScript()
-> ExtendScript
-> After Effects project/layer/render APIs
```

因此，只要某个能力主要依赖 ExtendScript API，而不是 CEP 面板自身状态，就可以评估用 COM 路线实现。

## COM 路线优点

- 适合后端批处理。
- 能接入 MediaTools 任务中心。
- 可以由 Web UI 或 AI 助手触发。
- 不需要把用户操作限制在 AE 面板内。

## COM 路线限制

- 依赖 Windows COM 环境。
- 需要本机安装 After Effects。
- 弹窗、权限和工程状态会影响稳定性。
- 与 AE UI 强绑定的交互不适合直接迁移。

## CEP/Atom 路线优点

- 在 AE 内部运行，天然贴近设计师工作流。
- 适合交互式 UI。
- 可以利用插件自己的前端状态和用户上下文。

## CEP/Atom 路线限制

- 部署和更新依赖插件安装。
- 不适合作为 MediaTools 后端服务的基础依赖。
- 与 Web 工作台的任务中心、日志和鉴权体系衔接成本更高。

## 迁移判断

可以迁移到 COM：

- 扫描工程结构
- 读取和修改文本层
- 枚举字体
- 保存工程
- 创建检查点
- 添加渲染队列

不适合直接迁移：

- 依赖 CEP 面板 UI 状态的交互
- 长时间需要人工点击的流程
- 插件内部云服务或账号能力

## 当前实现位置

- `modules/adobe/after_effects/`
- `adapters/after_effects_runtime.py`
- `services/api_adobe_routes.py`
- `frontend/src/apps/AEApp.tsx`
