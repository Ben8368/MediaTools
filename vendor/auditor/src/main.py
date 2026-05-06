"""
main.py — 入口，启动常驻进程
所有配置从 .env（连接信息）+ 配置工作簿（运营配置）读取，代码零硬编码
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)

import settings
from output.factory import create_backend
from audit.engine import AuditEngine
from audit.ai_client import AIClient
from audit.pipeline import AuditPipeline
from audit.validator import ConfigValidator
from feishu.designer_lookup import DesignerLookup
from monitor.folder_monitor import FolderMonitor


def setup_logging(sys_config: dict):
    level = getattr(logging, sys_config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/auditor.log", encoding="utf-8"),
        ],
    )


def main():
    Path("data").mkdir(exist_ok=True)

    # 1. 连接配置后端（local / feishu / google_sheets）
    backend = create_backend()

    # 2. 从配置表加载所有运营配置
    sys_config = backend.load_system_config()
    setup_logging(sys_config)
    logger = logging.getLogger(__name__)
    logger.info("Backend: %s | Config loaded", settings.BACKEND)

    # 3. 配置验证
    validator = ConfigValidator(sys_config)
    errors = validator.validate()
    if errors:
        for err in errors:
            logger.error("[配置错误] %s", err)
        sys.exit(1)

    # 4. 初始化各模块（依赖注入，不 import 任何全局配置）
    ai_client = AIClient(sys_config)

    engine = AuditEngine(
        ai_client=ai_client,
        rules_loader=backend.load_rules,
        roles_loader=backend.load_roles,
        sys_config=sys_config,
    )

    designer_lookup = DesignerLookup(data_loader=backend.load_designers)
    designer_lookup.refresh()

    supervisor_id = sys_config.get("SUPERVISOR_FEISHU_ID", "")

    pipeline = AuditPipeline(engine, designer_lookup, backend, supervisor_id)

    def on_new_files(file_paths):
        logger.info("New files: %s", file_paths)
        try:
            results = asyncio.run(pipeline.process(file_paths, include_audit_time=True))
        except Exception as e:
            logger.error("审计异常: %s", e, exc_info=True)
        finally:
            monitor.finish_audit()

    # 5. 启动文件夹监控
    monitor = FolderMonitor(sys_config=sys_config, on_new_files=on_new_files)

    # 优雅关闭: Ctrl+C / SIGTERM 时保存快照
    def shutdown(signum, frame):
        logger.info("收到退出信号，保存快照后退出...")
        try:
            monitor.finish_audit()
        except Exception as e:
            logger.warning("保存快照失败: %s", e)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()
