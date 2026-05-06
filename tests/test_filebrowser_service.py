from pathlib import Path

import pytest

from modules.filebrowser import service as fb


def _set_roots(monkeypatch, *roots: Path) -> None:
    monkeypatch.setattr(
        fb,
        "_WINDOWS_DRIVE_CACHE",
        [{"name": f"Root {idx}", "path": str(root)} for idx, root in enumerate(roots)],
    )


def test_resolve_filebrowser_path_allows_returned_disk_roots(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    child = tmp_path / "media"
    child.mkdir()

    assert fb.resolve_filebrowser_path(child) == child.resolve()


def test_resolve_filebrowser_path_rejects_outside_disk_roots(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    _set_roots(monkeypatch, allowed)

    with pytest.raises(ValueError, match="outside accessible filebrowser roots"):
        fb.resolve_filebrowser_path(outside)


def test_resolve_filebrowser_path_uses_first_root_for_empty_path(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _set_roots(monkeypatch, first, second)

    assert fb.resolve_filebrowser_path("") == first.resolve()
    assert fb.resolve_filebrowser_path(".") == first.resolve()


def test_resolve_filebrowser_path_requires_absolute_paths(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="must be absolute"):
        fb.resolve_filebrowser_path("relative/path")


def test_resolve_filebrowser_path_reports_no_accessible_roots(monkeypatch):
    monkeypatch.setattr(fb, "_WINDOWS_DRIVE_CACHE", [])
    monkeypatch.setattr(fb, "list_filebrowser_disks", lambda: [])

    with pytest.raises(ValueError, match="No accessible"):
        fb.resolve_filebrowser_path("")


def test_list_filebrowser_disks_posix_root(monkeypatch):
    class Usage:
        total = 100
        used = 25
        free = 75

    monkeypatch.setattr(fb.os, "name", "posix")
    monkeypatch.setattr(fb.shutil, "disk_usage", lambda _path: Usage())

    assert fb.list_filebrowser_disks() == [{"name": "Root (/)", "path": "/", "total": 100, "used": 25, "free": 75}]


def test_list_filebrowser_disks_posix_handles_usage_error(monkeypatch):
    monkeypatch.setattr(fb.os, "name", "posix")

    def fail_usage(_path):
        raise OSError("disk unavailable")

    monkeypatch.setattr(fb.shutil, "disk_usage", fail_usage)

    assert fb.list_filebrowser_disks() == []


def test_list_filebrowser_disks_windows_filters_unavailable_drives(monkeypatch):
    class Usage:
        total = 200
        used = 50
        free = 150

    monkeypatch.setattr(fb.os, "name", "nt")
    monkeypatch.setattr(fb.string, "ascii_uppercase", "AB")

    def fake_usage(root):
        if root == "A:\\":
            raise OSError("not ready")
        return Usage()

    def fake_iterdir(path):
        if str(path) == "B:\\":
            return iter([])
        raise PermissionError("blocked")

    monkeypatch.setattr(fb.shutil, "disk_usage", fake_usage)
    monkeypatch.setattr(fb.Path, "iterdir", fake_iterdir)

    assert fb.list_filebrowser_disks() == [
        {"name": "本地磁盘 (B:)", "path": "B:\\", "total": 200, "used": 50, "free": 150}
    ]


def test_fb_list_uses_filebrowser_roots_not_workspace_roots(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    (tmp_path / "clip.mp4").write_text("video", encoding="utf-8")
    (tmp_path / ".hidden").write_text("hidden", encoding="utf-8")
    (tmp_path / "folder").mkdir()

    result = fb.fb_list(str(tmp_path))

    assert result["path"] == str(tmp_path.resolve())
    assert [item["name"] for item in result["directories"]] == ["folder"]
    assert [item["name"] for item in result["files"]] == ["clip.mp4"]

    hidden = fb.fb_list(str(tmp_path), show_hidden=True)
    assert [item["name"] for item in hidden["files"]] == [".hidden", "clip.mp4"]


def test_fb_list_rejects_missing_or_file_paths(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    file_path = tmp_path / "clip.mp4"
    file_path.write_text("video", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        fb.fb_list(str(tmp_path / "missing"))
    with pytest.raises(NotADirectoryError):
        fb.fb_list(str(file_path))


def test_fb_info_and_mkdir(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    file_path = tmp_path / "clip.mp4"
    file_path.write_text("video", encoding="utf-8")
    new_dir = tmp_path / "new"

    info = fb.fb_info(str(file_path))
    created = fb.fb_mkdir(str(new_dir))

    assert info["name"] == "clip.mp4"
    assert info["extension"] == ".mp4"
    assert created["ok"] is True
    assert new_dir.is_dir()
    with pytest.raises(FileExistsError):
        fb.fb_mkdir(str(new_dir))
    with pytest.raises(FileNotFoundError):
        fb.fb_info(str(tmp_path / "missing.txt"))


def test_fb_rename_success_and_rejects_conflicts(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    existing = tmp_path / "existing.txt"
    existing.write_text("y", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid new name"):
        fb.fb_rename(str(source), "")
    with pytest.raises(FileExistsError):
        fb.fb_rename(str(source), "existing.txt")

    result = fb.fb_rename(str(source), "renamed.txt")

    assert result["new_path"] == str(tmp_path / "renamed.txt")
    assert (tmp_path / "renamed.txt").read_text(encoding="utf-8") == "x"

    with pytest.raises(FileNotFoundError):
        fb.fb_rename(str(source), "missing-renamed.txt")


def test_fb_rename_rejects_path_separator_in_new_name(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="path separators"):
        fb.fb_rename(str(source), "nested/name.txt")


def test_fb_move_and_copy_files_and_directories(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    moved = tmp_path / "moved.txt"

    move_result = fb.fb_move(str(source), str(moved))

    assert move_result["destination"] == str(moved)
    assert moved.read_text(encoding="utf-8") == "x"

    copied = tmp_path / "copied.txt"
    copy_result = fb.fb_copy(str(moved), str(copied))
    assert copy_result["destination"] == str(copied)
    assert copied.read_text(encoding="utf-8") == "x"

    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "inside.txt").write_text("inside", encoding="utf-8")
    folder_copy = tmp_path / "folder-copy"

    fb.fb_copy(str(folder), str(folder_copy))

    assert (folder_copy / "inside.txt").read_text(encoding="utf-8") == "inside"
    with pytest.raises(FileExistsError):
        fb.fb_copy(str(folder), str(folder_copy))
    with pytest.raises(FileNotFoundError):
        fb.fb_move(str(tmp_path / "missing.txt"), str(tmp_path / "target.txt"))
    with pytest.raises(FileExistsError):
        fb.fb_move(str(moved), str(copied))
    with pytest.raises(FileNotFoundError):
        fb.fb_copy(str(tmp_path / "missing.txt"), str(tmp_path / "copy.txt"))


def test_fb_delete_moves_file_to_trash_and_restore_recovers_it(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")

    deleted = fb.fb_delete(str(source))

    assert not source.exists()
    assert deleted["trash_id"]
    trash_items = fb.fb_list_trash()["items"]
    assert len(trash_items) == 1
    assert trash_items[0]["original_path"] == str(source)

    restored = fb.fb_restore_trash(deleted["trash_id"])

    assert restored["restored"] == str(source)
    assert source.read_text(encoding="utf-8") == "hello"
    assert fb.fb_list_trash()["items"] == []


def test_fb_delete_directory_requires_recursive_and_then_moves_to_trash(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    source = tmp_path / "folder"
    source.mkdir()
    (source / "inside.txt").write_text("inside", encoding="utf-8")

    with pytest.raises(IsADirectoryError):
        fb.fb_delete(str(source))

    result = fb.fb_delete(str(source), recursive=True)

    assert not source.exists()
    assert result["trash_id"]
    assert fb.fb_list_trash()["items"][0]["type"] == "directory"


def test_fb_delete_rejects_drive_root(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="drive root"):
        fb.fb_delete(str(tmp_path), recursive=True)


def test_fb_delete_missing_path(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)

    with pytest.raises(FileNotFoundError):
        fb.fb_delete(str(tmp_path / "missing.txt"))


def test_fb_restore_trash_rejects_existing_destination_and_missing_payload(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")
    trash_id = fb.fb_delete(str(source))["trash_id"]
    source.write_text("replacement", encoding="utf-8")

    with pytest.raises(FileExistsError):
        fb.fb_restore_trash(trash_id)

    source.unlink()
    payload = Path(fb.fb_list_trash()["items"][0]["stored_path"])
    payload.unlink()

    with pytest.raises(FileNotFoundError, match="payload"):
        fb.fb_restore_trash(trash_id)


def test_fb_restore_trash_to_custom_path(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    source = tmp_path / "source.txt"
    target = tmp_path / "custom.txt"
    source.write_text("hello", encoding="utf-8")
    trash_id = fb.fb_delete(str(source))["trash_id"]

    restored = fb.fb_restore_trash(trash_id, str(target))

    assert restored["restored"] == str(target)
    assert target.read_text(encoding="utf-8") == "hello"


def test_fb_list_trash_ignores_corrupt_entries(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    bad_dir = trash_dir / "bad"
    bad_dir.mkdir(parents=True)
    (bad_dir / fb.TRASH_META).write_text("{bad json", encoding="utf-8")

    assert fb.fb_list_trash()["items"] == []


def test_trash_operations_report_missing_items(tmp_path, monkeypatch):
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", tmp_path / "trash")

    with pytest.raises(FileNotFoundError, match="Trash item"):
        fb.fb_restore_trash("missing")
    with pytest.raises(FileNotFoundError, match="Trash item"):
        fb.fb_purge_trash("missing")
    assert fb.fb_empty_trash()["deleted"] == 0


def test_fb_purge_and_empty_trash(tmp_path, monkeypatch):
    trash_dir = tmp_path / "trash"
    _set_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(fb, "TRASH_DIR", trash_dir)
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    first_id = fb.fb_delete(str(first))["trash_id"]
    fb.fb_delete(str(second))

    assert fb.fb_purge_trash(first_id)["purged"] == first_id
    assert len(fb.fb_list_trash()["items"]) == 1

    assert fb.fb_empty_trash()["deleted"] == 1
    assert fb.fb_list_trash()["items"] == []
