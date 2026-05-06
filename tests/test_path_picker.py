from pathlib import Path

import pytest

from services.path_picker import get_path_picker_roots, list_path_picker_directory


def _workspace(root: Path) -> dict[str, str]:
    return {
        "project_root": str(root),
        "downloads_dir": str(root / "downloads"),
        "assets_dir": str(root / "assets"),
        "exports_dir": str(root / "exports"),
        "cache_dir": str(root / "cache"),
    }


def test_path_picker_roots_include_workspace_dirs(tmp_path):
    workspace = _workspace(tmp_path / "project")

    roots = get_path_picker_roots(workspace)
    root_ids = {root["id"] for root in roots}

    assert {"workspace", "downloads", "assets", "exports"}.issubset(root_ids)
    assert str((tmp_path / "project").resolve()) in {root["path"] for root in roots}


def test_path_picker_lists_directories_and_files(tmp_path):
    project = tmp_path / "project"
    (project / "inputs").mkdir(parents=True)
    (project / "inputs" / "clip.mp4").write_text("video", encoding="utf-8")

    result = list_path_picker_directory(root_id="workspace", path="inputs", workspace=_workspace(project))

    assert result["relative_path"] == "inputs"
    assert result["files"][0]["name"] == "clip.mp4"
    assert result["files"][0]["path"] == str((project / "inputs" / "clip.mp4").resolve())


def test_path_picker_missing_file_lists_existing_parent(tmp_path):
    project = tmp_path / "project"
    (project / "exports").mkdir(parents=True)

    result = list_path_picker_directory(root_id="workspace", path="exports/new-output.mp4", workspace=_workspace(project))

    assert result["relative_path"] == "exports"
    assert result["path"] == str((project / "exports").resolve())


def test_path_picker_rejects_traversal(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ValueError):
        list_path_picker_directory(root_id="workspace", path="../outside", workspace=_workspace(project))
