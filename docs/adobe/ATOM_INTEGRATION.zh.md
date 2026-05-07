# Atom 集成说明

> 中文专有文档，暂无英文版本。

Atom 是 After Effects 的第三方 CEP 插件。MediaTools 当前没有把 Atom 作为后端必需组件；Atom 相关资料只作为 Adobe 自动化路线的参考。

## 当前状态

| 项目 | 状态 |
|---|---|
| Atom 独立插件 | 可作为 AE 内部工具单独使用 |
| MediaTools 后端直连 Atom | 未作为主线实现 |
| MediaTools After Effects COM 自动化 | 已有相关模块和 API |
| 前端 AE 应用 | 已有 `AEApp.tsx` |

## 与 MediaTools 的关系

MediaTools 当前 Adobe 路线主要通过：

- `modules/adobe/after_effects/`
- `services/api_adobe_routes.py`
- `adapters/after_effects_runtime.py`
- `vendor/adobe/after-effects/`

Atom 的价值在于提供 CEP/ExtendScript 方案参考。若某个 Atom 能力需要进入 MediaTools，应优先判断是否可以通过当前 COM/ExtendScript 路线实现。

## 可复用思路

- 字体枚举
- 工程检查点
- 图层扫描
- 文本层修改
- 渲染队列操作
- ExtendScript 脚本封装

## 不建议

- 不要让核心媒体流程依赖 Atom。
- 不要把 Atom 插件内部实现直接写入 `services/`。
- 不要在没有本机 AE/插件验证的情况下把 Atom 能力标成已集成。

## 相关文档

- [AE 能力对比](./ae_capability_comparison.md)
- [COM vs CEP 技术说明](./com_vs_cep_technical_proof.md)
- [Atom 能力清单](./atom_plugin_capabilities.md)
