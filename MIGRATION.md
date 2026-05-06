# Backend 架构重构迁移指南

本文档说明如何从旧的 `services/` 架构迁移到新的 `backend/` 架构。

## 重构概述

**完成时间**：2026-05-07  
**影响范围**：104 个文件，7,881 行新增代码

### 新的目录结构

```
MediaTools/
├── backend/                  # 后端代码（新）
│   ├── config/              # 配置管理
│   ├── agent/               # AI Agent 层
│   ├── api/                 # API 层
│   │   ├── server.py
│   │   ├── routes/          # 15个路由文件
│   │   └── ...
│   └── services/            # 业务服务层
│       ├── media/           # 媒体服务
│       ├── runtime/         # 运行时管理
│       └── ...
├── cli/                     # CLI 入口
└── ...
```

## 导入路径变更

### 配置

```python
# 旧方式（已废弃，但仍可用）
from config import BASE_DIR, API_KEY

# 新方式（推荐）
from backend.config import BASE_DIR, API_KEY
```

### Agent

```python
# 旧方式
from services.agent import MediaAgentService
from services.agent_tools import execute_tool

# 新方式
from backend.agent.service import MediaAgentService
from backend.agent.tools import execute_tool
```

### API

```python
# 旧方式
from services.api_server import app
from services.api_models import AgentChatBody

# 新方式
from backend.api.server import app
from backend.api.models import AgentChatBody
```

### 服务

```python
# 旧方式
from services.media import fetch_video_info
from services.workspace import get_current_workspace

# 新方式
from backend.services.media.core import fetch_video_info
from backend.services.workspace import get_current_workspace
```

## 兼容性说明

### 向后兼容

为了保持向后兼容，以下文件被保留作为兼容层：

1. **config.py**
   - 重新导出 `backend.config` 的所有内容
   - 显示 DeprecationWarning

2. **main.py**
   - 重新导出 `cli.main` 的 main 函数
   - 显示 DeprecationWarning

3. **services/** 目录
   - 保留原有文件（未删除）
   - 可以继续使用旧的导入路径

### 迁移建议

**立即迁移**（推荐）：
- 新代码使用新的导入路径
- 逐步更新现有代码

**延迟迁移**：
- 继续使用旧的导入路径
- 在未来 1-2 个版本后再迁移

## 启动方式变更

### Web 服务

```bash
# 方式不变
python app.py

# 或指定端口
python app.py --port 8080
```

### CLI 工具

```bash
# 新方式（推荐）
python -m cli.main fetcher download <url>

# 旧方式（兼容）
python main.py fetcher download <url>
```

## 测试更新

所有测试文件的导入已更新：

```python
# 旧方式
from services.agent import MediaAgentService

# 新方式
from backend.agent.service import MediaAgentService
```

如果你有自定义测试，请参考 `tests/` 目录中的更新。

## 常见问题

### Q: 我的代码会立即失效吗？

**A**: 不会。所有旧的导入路径仍然可用，只是会显示 DeprecationWarning。

### Q: 我需要立即更新所有代码吗？

**A**: 不需要。你可以：
- 新代码使用新路径
- 旧代码保持不变
- 逐步迁移

### Q: services/ 目录会被删除吗？

**A**: 目前不会。services/ 目录中的文件仍然存在，作为向后兼容层。未来版本可能会移除。

### Q: 如何知道哪些导入需要更新？

**A**: 运行代码时，Python 会显示 DeprecationWarning，告诉你哪些导入已废弃。

### Q: 重构后性能有影响吗？

**A**: 没有。新的架构只是重新组织了代码，不影响运行时性能。

## 迁移检查清单

如果你决定立即迁移，请检查以下内容：

- [ ] 更新所有 `from config import` 为 `from backend.config import`
- [ ] 更新所有 `from services.agent` 为 `from backend.agent.service`
- [ ] 更新所有 `from services.api_server` 为 `from backend.api.server`
- [ ] 更新所有 `from services.media` 为 `from backend.services.media.core`
- [ ] 更新所有其他 `from services.*` 为 `from backend.services.*`
- [ ] 运行测试确保一切正常
- [ ] 更新文档和注释

## 获取帮助

如果在迁移过程中遇到问题：

1. 查看 `ARCHITECTURE.md` 了解新的架构设计
2. 参考 `tests/` 目录中的测试文件示例
3. 查看 `scripts/complete_refactor.py` 了解迁移逻辑

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 完整的架构文档
- [README.md](./README.md) - 项目说明
- [scripts/complete_refactor.py](./scripts/complete_refactor.py) - 重构脚本
