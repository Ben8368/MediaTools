import unittest
from pathlib import Path

from core.validation import (
    ValidationError,
    sanitize_filename,
    validate_file_path,
    validate_integer,
    validate_timestamp,
    validate_url,
)


class TestValidation(unittest.TestCase):
    def test_validate_url_success(self):
        url = validate_url("https://youtube.com/watch?v=test")
        self.assertEqual(url, "https://youtube.com/watch?v=test")

    def test_validate_url_invalid_scheme(self):
        with self.assertRaises(ValidationError):
            validate_url("ftp://example.com")

    def test_validate_url_empty(self):
        with self.assertRaises(ValidationError):
            validate_url("")

    def test_validate_file_path_resolves_relative_to_base_dir(self):
        base_dir = Path.cwd()
        result = validate_file_path("README.md", must_exist=True, base_dir=base_dir)
        self.assertEqual(result, base_dir / "README.md")

    def test_validate_file_path_rejects_escape_from_base_dir(self):
        with self.assertRaises(ValidationError):
            validate_file_path("../outside.mp4", base_dir=Path.cwd())

    def test_validate_file_path_checks_allowed_extensions(self):
        with self.assertRaises(ValidationError):
            validate_file_path("README.md", allowed_extensions=[".mp4"], base_dir=Path.cwd())

    def test_validate_timestamp_hms(self):
        ts = validate_timestamp("01:23:45")
        self.assertEqual(ts, "01:23:45")

    def test_validate_timestamp_ms(self):
        ts = validate_timestamp("12:34")
        self.assertEqual(ts, "12:34")

    def test_validate_timestamp_seconds(self):
        ts = validate_timestamp("123.5")
        self.assertEqual(ts, "123.5")

    def test_validate_timestamp_invalid(self):
        with self.assertRaises(ValidationError):
            validate_timestamp("invalid")

    def test_validate_integer_success(self):
        value = validate_integer("42", min_value=0, max_value=100)
        self.assertEqual(value, 42)

    def test_validate_integer_out_of_range(self):
        with self.assertRaises(ValidationError):
            validate_integer("150", min_value=0, max_value=100)

    def test_sanitize_filename(self):
        safe = sanitize_filename("test<>file?.txt")
        self.assertEqual(safe, "test__file_.txt")

    def test_sanitize_filename_long(self):
        long_name = "a" * 300 + ".txt"
        safe = sanitize_filename(long_name, max_length=255)
        self.assertLessEqual(len(safe), 255)
        self.assertTrue(safe.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
