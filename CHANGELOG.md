# MediaTools 更新日志

## 2026-04-24 - 重大更新

### 安全性改进
- ✅ 修改默认服务绑定地址为 127.0.0.1（原 0.0.0.0）
- ✅ 添加 API_SECRET_KEY 配置支持（可选认证）
- ✅ 增强输入验证和错误处理

### 日志系统增强
- ✅ 重构 core/logger.py，支持文件日志和控制台日志
- ✅ 统一错误处理，替换 print 为结构化日志
- ✅ 添加日志级别配置

### 新增功能模块
- ✅ **素材生成模块** (modules/generator)
  - 支持视频截图提取
  - 批量截图生成
  - CLI: `python main.py generator screenshot`

### 已有模块确认
- ✅ **PSD批量处理** (modules/photoshop) - 已存在
- ✅ **素材审核** (modules/auditor) - 已存在
- ✅ **微信朋友圈** (modules/wechat_moments) - 已存在

### 字幕下载增强
- ✅ 确认支持中文翻译字幕下载（zh-Hans）
- ✅ 支持原语言 + 中文双语字幕

### 测试覆盖
- ✅ 添加 tests/ 目录
- ✅ 添加 services/media 测试
- ✅ 添加 modules/encoder/transcoder 测试

### 待办事项
- ⏳ 更新 vendor/capcut-mate 到最新版本
- ⏳ 添加 API 认证中间件实现
- ⏳ 扩展测试覆盖率
- ⏳ 添加 CI/CD 配置

## 后端能力清单

### ✅ 已实现
1. 视频下载（YouTube + 多平台）
2. 字幕下载（原语言 + 中文翻译）
3. 字幕分析切片（LLM驱动）
4. 音乐解密（unlock-music）
5. PSD批量处理（Photoshop自动化）
6. 素材生成（视频截图）
7. 素材审核（Auditor集成）

### 🔄 实验性
- capcut-mate 集成（需更新到最新版本）

## 技术债务
- 添加更多单元测试
- 实现任务队列（Celery/RQ）
- 添加进度持久化
- 统一前端框架（移除Gradio）
