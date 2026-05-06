import logging
import tempfile
import unittest
from pathlib import Path

from core.logger import get_logger, setup_logger


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


if __name__ == "__main__":
    unittest.main()
