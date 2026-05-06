## 10. Atom - After Effects 自动化 🟡

### 基本信息
- **官方网站**: https://tryatom.ai
- **官方文档**: https://tryatom.ai/docs/introduction
- **类型**: CEP 扩展（独立运行）
- **用途**: After Effects 自动化插件

### 功能特性

#### 1. 批量清理与整理
- 重命名图层
- 重排图层顺序
- 批量编辑图层属性

#### 2. 快速创意探索
- 快速尝试运动效果
- 调整节奏和配色
- 迭代动效方案

#### 3. 表达式自动化
- 快速添加 wiggle 表达式
- 属性联动
- 解释现有表达式

#### 4. 控制器搭建
- 用滑块统一控制
- 属性同步
- 快速搭建 rig

#### 5. 生成图片素材
- 在聊天中生成纹理
- 生成精灵图
- 生成氛围图并自动导入工程

### 后端能力
```
# Atom 是独立的 CEP 扩展，不直接集成到后端
# 但可以通过以下方式间接集成:

1. 脚本接口
   - 通过 ExtendScript 脚本调用
   - 批量处理 AE 工程

2. 文件监控
   - 监控 AE 输出目录
   - 自动导入到素材库

3. 工作流集成
   - 与其他模块配合
   - 自动化动效生成流程
```

### Agent集成 ❌
```python
# 当前没有 Atom 相关的 Agent 工具
# 潜在集成方式:
# - _tool_generate_ae_animation(description, template)
# - _tool_batch_process_ae_projects(projects, operations)
```

### 前端API ❌
```
# 当前没有 Atom 相关的 API 路由
# 潜在 API:
# GET  /api/atom/status          # 检查 AE 和 Atom 状态
# POST /api/atom/execute          # 执行 AE 脚本
# GET  /api/atom/projects         # 列出 AE 工程
```

### 评估
- **完整度**: 100% (作为独立工具) ✅
- **集成度**: 0% (未集成到 MediaTools) ❌
- **Agent可用**: 否 ❌
- **前端可用**: 否 ❌
- **状态**: 独立工具，可选集成

### 集成建议

#### 短期（可选）
1. **文件监控集成**
   - 监控 AE 输出目录
   - 自动导入到素材库

#### 中期（可选）
2. **脚本接口集成**
   - 创建 `modules/ae_automation/`
   - 通过 ExtendScript 调用 Atom
   - 提供批量处理能力

#### 长期（可选）
3. **完整集成**
   - Agent 工具集成
   - 前端界面
   - 工作流自动化

### 使用方式

#### 独立使用
1. 安装 Atom 到 AE 扩展目录
2. 在 AE 中打开 Atom 面板
3. 用自然语言描述需求

#### 与 MediaTools 配合
1. 使用 MediaTools 下载素材
2. 在 AE 中用 Atom 处理
3. 输出回 MediaTools 素材库

---

**维护者**: MediaTools Team  
**最后更新**: 2026-04-24  
**集成优先级**: 低（可选）
