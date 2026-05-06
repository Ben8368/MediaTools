# 任务队列设计方案

## 背景

当前项目的长时间运行任务（视频下载、转码、切片等）都是同步执行的，存在以下问题：

1. **阻塞问题**：长任务会阻塞API响应
2. **并发限制**：无法并发处理多个任务
3. **资源管理**：缺少任务优先级和资源限制
4. **状态持久化**：重启后任务状态丢失

## 方案选择

### 方案1: Celery（推荐）

**优点**：
- 成熟稳定，生态完善
- 支持多种消息队列（Redis、RabbitMQ）
- 内置任务调度、重试、监控
- 支持任务优先级和速率限制

**缺点**：
- 需要额外的消息队列服务
- 配置相对复杂

### 方案2: RQ (Redis Queue)

**优点**：
- 轻量级，易于配置
- 仅依赖Redis
- API简单直观

**缺点**：
- 功能相对简单
- 仅支持Redis

### 方案3: 内置线程池

**优点**：
- 无外部依赖
- 部署简单

**缺点**：
- 功能有限
- 无法跨进程
- 状态不持久化

## 推荐实现：Celery + Redis

### 1. 安装依赖

```bash
pip install celery[redis] redis
```

### 2. 目录结构

```
MediaTools/
├── celery_app.py          # Celery应用配置
├── tasks/                 # 任务定义
│   ├── __init__.py
│   ├── media_tasks.py     # 媒体处理任务
│   ├── analysis_tasks.py  # 分析任务
│   └── export_tasks.py    # 导出任务
└── workers/               # Worker配置
    └── config.py
```

### 3. 配置示例

```python
# celery_app.py
from celery import Celery

app = Celery(
    'mediatools',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
```

### 4. 任务定义

```python
# tasks/media_tasks.py
from celery_app import app
from services.media import run_transcode_job

@app.task(bind=True, name='media.transcode')
def transcode_task(self, input_path, output_path, codec, **options):
    """转码任务"""
    # 更新任务状态
    self.update_state(state='PROGRESS', meta={'stage': '开始转码'})
    
    result = run_transcode_job(input_path, output_path, codec, **options)
    
    return result
```

### 5. API集成

```python
# services/api_server.py
from tasks.media_tasks import transcode_task

@app.post("/api/encoder/transcode-async")
async def transcode_async(request: TranscodeRequest):
    """异步转码"""
    task = transcode_task.delay(
        request.input_path,
        request.output_path,
        request.codec,
    )
    return {"task_id": task.id, "status": "queued"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = transcode_task.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": task.state,
        "result": task.result if task.ready() else None,
        "info": task.info,
    }
```

### 6. 启动Worker

```bash
# 启动Celery Worker
celery -A celery_app worker --loglevel=info --concurrency=2

# 启动Flower监控（可选）
celery -A celery_app flower
```

## 任务优先级

```python
# 高优先级任务
task.apply_async(priority=9)

# 普通优先级
task.apply_async(priority=5)

# 低优先级
task.apply_async(priority=1)
```

## 任务重试

```python
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def download_task(self, url):
    try:
        return download_video(url)
    except Exception as exc:
        # 60秒后重试
        raise self.retry(exc=exc, countdown=60)
```

## 监控和管理

### Flower Web界面

```bash
celery -A celery_app flower --port=5555
# 访问 http://localhost:5555
```

### 命令行工具

```bash
# 查看活跃任务
celery -A celery_app inspect active

# 查看已注册任务
celery -A celery_app inspect registered

# 撤销任务
celery -A celery_app control revoke <task_id>
```

## 部署建议

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  worker:
    build: .
    command: celery -A celery_app worker --loglevel=info
    depends_on:
      - redis
    volumes:
      - ./projects:/app/projects
  
  api:
    build: .
    command: python app.py
    ports:
      - "7860:7860"
    depends_on:
      - redis
```

## 迁移路径

1. **阶段1**：保持现有同步API，添加异步API端点
2. **阶段2**：前端逐步切换到异步API
3. **阶段3**：废弃同步API（保留向后兼容）

## 成本估算

- Redis内存：约100MB（小规模）
- Worker进程：每个约200-500MB
- 建议配置：1个Redis + 2-4个Worker进程
