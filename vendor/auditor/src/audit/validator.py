"""
validator.py — 启动时配置完整性检查，给出友好的错误提示
"""
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ConfigValidator:
    """启动前配置检查"""

    def __init__(self, sys_config: Dict[str, str]):
        self.cfg = sys_config

    def validate(self) -> List[str]:
        """返回错误列表，为空表示配置正常"""
        errors = []
        self._check_required(errors)
        self._check_watch_folders(errors)
        self._check_numeric(errors)
        return errors

    def _check_required(self, errors: List[str]):
        val = os.getenv("TEC_CHI_API_KEY", "") or self.cfg.get("TEC_CHI_API_KEY", "").strip()
        if not val:
            errors.append("配置缺失: TEC_CHI_API_KEY — 请在环境变量 .env 中设置")

    def _check_watch_folders(self, errors: List[str]):
        folders = self.cfg.get("WATCH_FOLDERS", "").strip()
        if not folders:
            errors.append("配置缺失: WATCH_FOLDERS — 要监控的文件夹路径")
            return
        for folder in folders.split(","):
            f = folder.strip()
            if f and not os.path.isdir(f):
                errors.append(f"文件夹不存在: {f}")

    def _check_numeric(self, errors: List[str]):
        numeric_fields = [
            "MAX_CONCURRENCY", "API_TIMEOUT_SECONDS", "API_RETRY_COUNT",
            "SCAN_INTERVAL_SECONDS", "STABLE_WAIT_SECONDS",
        ]
        for key in numeric_fields:
            val = self.cfg.get(key, "").strip()
            if val:
                try:
                    int(val)
                except ValueError:
                    errors.append(f"配置格式错误: {key} 应为整数，当前值: {val}")
