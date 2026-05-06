"""
任务中心 - 统一管理所有任务的生命周期

功能：
- 任务持久化（SQLite）
- 任务历史记录（7天）
"""
import json
import sqlite3
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any

from config import TASK_DB_PATH, TASK_HISTORY_DAYS


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    PAUSED = "paused"         # 旧版本遗留状态，不再提供新的暂停/继续入口
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class TaskType(Enum):
    """任务类型"""
    TRANSCODE = "transcode"   # 转码
    DOWNLOAD = "download"     # 下载
    DECRYPT = "decrypt"       # 解密
    PS_BATCH = "ps_batch"     # PS批量处理
    CUSTOM = "custom"         # 自定义任务


class TaskCenter:
    """任务中心 - 管理所有任务的生命周期"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = TASK_DB_PATH

        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
        self._cleanup_old_tasks()

    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                stage TEXT DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                paused_at REAL,
                params TEXT,
                state TEXT,
                result TEXT,
                error TEXT
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON tasks(type)")

        conn.commit()
        conn.close()

    def _cleanup_old_tasks(self):
        """清理历史任务"""
        cutoff_time = time.time() - (TASK_HISTORY_DAYS * 24 * 3600)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM tasks
            WHERE created_at < ?
            AND status IN ('completed', 'failed', 'cancelled')
        """, (cutoff_time,))

        conn.commit()
        conn.close()

    def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        name: str,
        params: dict = None
    ) -> dict:
        """创建新任务"""
        with self._lock:
            now = time.time()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tasks (
                    id, type, name, status, progress, stage,
                    created_at, updated_at, params
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                task_type.value,
                name,
                TaskStatus.PENDING.value,
                0.0,
                "等待开始",
                now,
                now,
                json.dumps(params or {}, ensure_ascii=False)
            ))

            conn.commit()
            conn.close()

            return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict | None:
        """获取任务信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_dict(row)

    def update_task(
        self,
        task_id: str,
        status: TaskStatus = None,
        progress: float = None,
        stage: str = None,
        state: dict = None,
        result: dict = None,
        error: str = None
    ):
        """更新任务状态"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            updates = ["updated_at = ?"]
            values = [time.time()]

            if status is not None:
                updates.append("status = ?")
                values.append(status.value)

                # 更新时间戳
                if status == TaskStatus.RUNNING and not self._get_field(task_id, "started_at"):
                    updates.append("started_at = ?")
                    values.append(time.time())
                elif status == TaskStatus.PAUSED:
                    updates.append("paused_at = ?")
                    values.append(time.time())
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    updates.append("completed_at = ?")
                    values.append(time.time())

            if progress is not None:
                updates.append("progress = ?")
                values.append(progress)

            if stage is not None:
                updates.append("stage = ?")
                values.append(stage)

            if state is not None:
                updates.append("state = ?")
                values.append(json.dumps(state, ensure_ascii=False))

            if result is not None:
                updates.append("result = ?")
                values.append(json.dumps(result, ensure_ascii=False))

            if error is not None:
                updates.append("error = ?")
                values.append(error)

            values.append(task_id)

            cursor.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                values
            )

            conn.commit()
            conn.close()

    def pause_task(self, task_id: str, state: dict = None) -> bool:
        """暂停任务暂不支持。

        历史实现只改数据库状态，不能真正停止后台下载、转码或解密线程。
        调用方应使用 cancel_task 后重新提交任务。
        """
        raise NotImplementedError("Reliable pause/resume is not supported; cancel and resubmit the task instead.")

    def resume_task(self, task_id: str) -> dict | None:
        """继续任务暂不支持。"""
        raise NotImplementedError("Reliable pause/resume is not supported; cancel and resubmit the task instead.")

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task or task["status"] in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            return False

        self.update_task(task_id, status=TaskStatus.CANCELLED)
        return True

    def delete_task(self, task_id: str, allow_active: bool = False) -> bool:
        """Delete a persisted task record."""
        with self._lock:
            task = self.get_task(task_id)
            if not task:
                return False
            if not allow_active and task["status"] in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value):
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted

    def delete_tasks(
        self,
        task_ids: list[str] | None = None,
        statuses: list[TaskStatus] | None = None,
        task_type: TaskType | None = None,
        allow_active: bool = False,
    ) -> int:
        """Delete task records by ids or by task filters."""
        with self._lock:
            clauses: list[str] = []
            values: list[Any] = []

            if task_ids:
                placeholders = ",".join("?" for _ in task_ids)
                clauses.append(f"id IN ({placeholders})")
                values.extend(task_ids)

            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                clauses.append(f"status IN ({placeholders})")
                values.extend([status.value for status in statuses])

            if task_type:
                clauses.append("type = ?")
                values.append(task_type.value)

            if not allow_active:
                clauses.append("status NOT IN (?, ?)")
                values.extend([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])

            if not clauses:
                return 0

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM tasks WHERE {' AND '.join(clauses)}", values)
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted

    def list_tasks(
        self,
        status: TaskStatus = None,
        task_type: TaskType = None,
        limit: int = 100
    ) -> list[dict]:
        """列出任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if task_type:
            query += " AND type = ?"
            params.append(task_type.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_active_tasks(self) -> list[dict]:
        """获取所有活跃任务（pending, running）。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tasks
            WHERE status IN ('pending', 'running')
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def _get_field(self, task_id: str, field: str) -> Any:
        """获取任务的某个字段"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"SELECT {field} FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    def _row_to_dict(self, row: tuple) -> dict:
        """将数据库行转换为字典"""
        columns = [
            "id", "type", "name", "status", "progress", "stage",
            "created_at", "updated_at", "started_at", "completed_at", "paused_at",
            "params", "state", "result", "error"
        ]

        task = dict(zip(columns, row))

        # 解析JSON字段
        for field in ["params", "state", "result"]:
            if task[field]:
                try:
                    task[field] = json.loads(task[field])
                except:
                    task[field] = {}

        return task


# 全局任务中心实例
_task_center: TaskCenter | None = None


def get_task_center() -> TaskCenter:
    """获取任务中心实例"""
    global _task_center
    if _task_center is None:
        _task_center = TaskCenter()
    return _task_center
