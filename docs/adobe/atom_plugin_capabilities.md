# Atom 插件能力清单

本文是 Atom/CEP 能力的参考清单，不代表 MediaTools 已完整集成 Atom。

## 可参考能力

| 能力 | MediaTools 迁移价值 |
|---|---|
| 字体枚举 | 高 |
| 文本层扫描 | 高 |
| 文本内容修改 | 高 |
| 工程检查点 | 高 |
| 渲染队列管理 | 中高 |
| 图层属性批量修改 | 中 |
| 表达式辅助 | 中 |
| AE 内交互式 UI | 低，通常不迁移 |
| 插件内素材生成 | 低，需单独评估 |

## 与当前实现的关系

当前 MediaTools 更关注这些后端可执行能力：

- 扫描 AE 工程生成 ticket
- 编辑 ticket
- 执行 ticket
- 查看执行状态
- 创建和回滚检查点
- 管理渲染队列

对应代码：

- `modules/adobe/after_effects/`
- `services/api_adobe_routes.py`
- `frontend/src/apps/AEApp.tsx`

## 迁移方式

1. 确认能力是否基于 ExtendScript。
2. 在 `modules/adobe/after_effects/` 中封装脚本和数据结构。
3. 在 service/API 层提供产品语义。
4. 在前端 AE 应用中暴露操作。
5. 加入本机环境失败时的清晰错误提示。

## 注意事项

- 不要直接复制插件 UI 逻辑。
- 不要把 Atom 作为 MediaTools 必装依赖。
- 任何写工程操作都应考虑检查点。
- Adobe 能力必须允许环境不可用时优雅降级。
