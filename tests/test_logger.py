import logging
import tempfile
import unittest
from pathlib import Path

from core.logger import get_logger, setup_logger
from backend.services.log_buffer import LogBuffer


class TestLogger(unittest.TestCase):
    def test_setup_logger_replaces_existing_handlers(self):
        logger = logging.getLogger("mediatools.test.replace")
        logger.addHandler(logging.NullHandler())

        configured = setup_logger("mediatools.test.replace", console=False)

        self.assertIs(configured, logger)
        self.assertEqual(configured.handlers, [])
        self.assertFalse(configured.propagate)

    def test_setup_logger_writes_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "app.log"
            logger = setup_logger("mediatools.test.file", log_file=log_path, console=False)

            logger.info("hello")
            handlers = list(logger.handlers)
            for handler in handlers:
                handler.flush()

            self.assertTrue(log_path.exists())
            self.assertIn("hello", log_path.read_text(encoding="utf-8"))
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)

    def test_get_logger_reuses_configured_logger(self):
        logger = setup_logger("mediatools.test.reuse", console=False)

        self.assertIs(get_logger("mediatools.test.reuse"), logger)

    def test_get_logger_creates_default_logger(self):
        name = "mediatools.test.default"
        logging.getLogger(name).handlers.clear()

        logger = get_logger(name)

        self.assertTrue(logger.handlers)

    def test_log_buffer_level_threshold_and_noisy_access_filter(self):
        buffer = LogBuffer()
        logger = logging.getLogger("test.log_buffer")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        logger.addHandler(buffer)

        access_logger = logging.getLogger("api.access")
        access_logger.handlers.clear()
        access_logger.propagate = False
        access_logger.setLevel(logging.DEBUG)
        access_logger.addHandler(buffer)

        logger.debug("debug detail")
        logger.info("business info")
        logger.warning("warning detail")
        access_logger.info("GET /api/tasks -> 200")
        access_logger.info("GET /api/system/metrics -> 200")

        info_records = buffer.get_records(level="INFO")["items"]
        self.assertEqual([item["message"] for item in info_records], ["warning detail", "business info"])

        debug_records = buffer.get_records(level="DEBUG")["items"]
        self.assertEqual([item["message"] for item in debug_records], ["GET /api/tasks -> 200", "warning detail", "business info", "debug detail"])

        access_records = buffer.get_records(level="INFO", module="api.access")["items"]
        self.assertEqual(access_records[0]["message"], "GET /api/tasks -> 200")


if __name__ == "__main__":
    unittest.main()
