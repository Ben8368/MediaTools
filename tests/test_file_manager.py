"""Tests for FileManager"""
import shutil
import tempfile
import unittest
from pathlib import Path

from modules.assets.file_manager import FileManager


class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = FileManager(self.temp_dir)

    def tearDown(self):
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_list_directory_empty(self):
        result = self.manager.list_directory(".")
        self.assertEqual(result["files"], [])
        self.assertEqual(result["directories"], [])

    def test_list_directory_with_files(self):
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("content")
        test_dir = Path(self.temp_dir) / "subdir"
        test_dir.mkdir()

        result = self.manager.list_directory(".")
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(len(result["directories"]), 1)
        self.assertEqual(result["files"][0]["name"], "test.txt")
        self.assertEqual(result["directories"][0]["name"], "subdir")

    def test_list_directory_hidden_files(self):
        hidden_file = Path(self.temp_dir) / ".hidden"
        hidden_file.write_text("secret")

        result = self.manager.list_directory(".", show_hidden=False)
        self.assertEqual(len(result["files"]), 0)

        result = self.manager.list_directory(".", show_hidden=True)
        self.assertEqual(len(result["files"]), 1)

    def test_list_directory_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.list_directory("nonexistent")

    def test_create_directory(self):
        result = self.manager.create_directory("newdir")
        self.assertTrue(result["ok"])
        self.assertTrue((Path(self.temp_dir) / "newdir").exists())

    def test_create_directory_nested(self):
        result = self.manager.create_directory("parent/child")
        self.assertTrue(result["ok"])
        self.assertTrue((Path(self.temp_dir) / "parent" / "child").exists())

    def test_create_directory_already_exists(self):
        (Path(self.temp_dir) / "existing").mkdir()
        with self.assertRaises(FileExistsError):
            self.manager.create_directory("existing")

    def test_delete_file(self):
        test_file = Path(self.temp_dir) / "delete_me.txt"
        test_file.write_text("content")

        result = self.manager.delete("delete_me.txt")
        self.assertTrue(result["ok"])
        self.assertFalse(test_file.exists())

    def test_delete_directory_recursive(self):
        test_dir = Path(self.temp_dir) / "delete_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = self.manager.delete("delete_dir", recursive=True)
        self.assertTrue(result["ok"])
        self.assertFalse(test_dir.exists())

    def test_delete_directory_without_recursive(self):
        test_dir = Path(self.temp_dir) / "delete_dir"
        test_dir.mkdir()

        with self.assertRaises(IsADirectoryError):
            self.manager.delete("delete_dir", recursive=False)

    def test_delete_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.delete("nonexistent.txt")

    def test_rename_file(self):
        old_file = Path(self.temp_dir) / "old.txt"
        old_file.write_text("content")

        result = self.manager.rename("old.txt", "new.txt")
        self.assertTrue(result["ok"])
        self.assertFalse(old_file.exists())
        self.assertTrue((Path(self.temp_dir) / "new.txt").exists())

    def test_rename_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.rename("nonexistent.txt", "new.txt")

    def test_rename_target_exists(self):
        (Path(self.temp_dir) / "old.txt").write_text("old")
        (Path(self.temp_dir) / "new.txt").write_text("new")

        with self.assertRaises(FileExistsError):
            self.manager.rename("old.txt", "new.txt")

    def test_copy_file(self):
        source = Path(self.temp_dir) / "source.txt"
        source.write_text("content")

        result = self.manager.copy("source.txt", "dest.txt")
        self.assertTrue(result["ok"])
        self.assertTrue(source.exists())
        self.assertTrue((Path(self.temp_dir) / "dest.txt").exists())

    def test_copy_directory(self):
        source_dir = Path(self.temp_dir) / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        result = self.manager.copy("source_dir", "dest_dir")
        self.assertTrue(result["ok"])
        self.assertTrue(source_dir.exists())
        self.assertTrue((Path(self.temp_dir) / "dest_dir" / "file.txt").exists())

    def test_copy_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.copy("nonexistent.txt", "dest.txt")

    def test_copy_target_exists(self):
        (Path(self.temp_dir) / "source.txt").write_text("source")
        (Path(self.temp_dir) / "dest.txt").write_text("dest")

        with self.assertRaises(FileExistsError):
            self.manager.copy("source.txt", "dest.txt")

    def test_move_file(self):
        source = Path(self.temp_dir) / "source.txt"
        source.write_text("content")

        result = self.manager.move("source.txt", "dest.txt")
        self.assertTrue(result["ok"])
        self.assertFalse(source.exists())
        self.assertTrue((Path(self.temp_dir) / "dest.txt").exists())

    def test_move_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.move("nonexistent.txt", "dest.txt")

    def test_move_target_exists(self):
        (Path(self.temp_dir) / "source.txt").write_text("source")
        (Path(self.temp_dir) / "dest.txt").write_text("dest")

        with self.assertRaises(FileExistsError):
            self.manager.move("source.txt", "dest.txt")

    def test_get_file_info(self):
        test_file = Path(self.temp_dir) / "info.txt"
        test_file.write_text("content")

        result = self.manager.get_file_info("info.txt")
        self.assertEqual(result["name"], "info.txt")
        self.assertTrue(result["is_file"])
        self.assertFalse(result["is_directory"])
        self.assertEqual(result["extension"], ".txt")
        self.assertGreater(result["size"], 0)

    def test_get_file_info_directory(self):
        test_dir = Path(self.temp_dir) / "info_dir"
        test_dir.mkdir()

        result = self.manager.get_file_info("info_dir")
        self.assertEqual(result["name"], "info_dir")
        self.assertTrue(result["is_directory"])
        self.assertFalse(result["is_file"])

    def test_get_file_info_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.get_file_info("nonexistent.txt")

    def test_rejects_parent_directory_escape(self):
        outside_file = Path(self.temp_dir).parent / "outside.txt"
        outside_file.write_text("outside")
        self.addCleanup(lambda: outside_file.unlink(missing_ok=True))

        with self.assertRaises(ValueError):
            self.manager.get_file_info("../outside.txt")
        self.assertTrue(outside_file.exists())

    def test_delete_rejects_absolute_path_outside_base(self):
        outside_file = Path(self.temp_dir).parent / "outside-delete.txt"
        outside_file.write_text("outside")
        self.addCleanup(lambda: outside_file.unlink(missing_ok=True))

        with self.assertRaises(ValueError):
            self.manager.delete(str(outside_file))
        self.assertTrue(outside_file.exists())

    def test_rename_rejects_path_separator_in_new_name(self):
        old_file = Path(self.temp_dir) / "old.txt"
        old_file.write_text("content")

        with self.assertRaises(ValueError):
            self.manager.rename("old.txt", "../new.txt")
        self.assertTrue(old_file.exists())


if __name__ == "__main__":
    unittest.main()
