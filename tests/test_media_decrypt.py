"""Tests for encrypted music decrypt service helpers."""

from pathlib import Path
from unittest.mock import Mock, patch

import backend.services.media.decrypt as media_decrypt


def workspace(tmp_path):
    root = tmp_path / "workspace"
    decrypted = root / "decrypted"
    assets = root / "assets"
    decrypted.mkdir(parents=True)
    assets.mkdir(parents=True)
    return {
        "project_root": str(root),
        "decrypted_dir": str(decrypted),
        "assets_dir": str(assets),
    }


def test_effective_decrypt_output_dir_uses_parent_when_empty_single(tmp_path):
    audio = tmp_path / "music" / "song.ncm"
    result = media_decrypt._effective_decrypt_output_dir("单文件", str(audio), None)
    assert result == audio.parent.resolve()


def test_effective_decrypt_output_dir_uses_input_folder_when_empty_batch(tmp_path):
    album = tmp_path / "album"
    result = media_decrypt._effective_decrypt_output_dir("文件夹批量", str(album), None)
    assert result == album.resolve()


def test_effective_decrypt_output_dir_uses_explicit_output(tmp_path):
    explicit = tmp_path / "custom"
    result = media_decrypt._effective_decrypt_output_dir("单文件", "song.ncm", str(explicit))
    assert result == explicit


def test_snapshot_files_and_copy_to_assets(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    existing = source / "exists.flac"
    existing.write_text("music", encoding="utf-8")
    missing = source / "missing.flac"
    assets = tmp_path / "assets"

    assert str(existing.resolve()) in media_decrypt._snapshot_files(source)
    copied = media_decrypt._copy_to_assets([existing, missing], assets)

    assert copied == 1
    assert (assets / "exists.flac").read_text(encoding="utf-8") == "music"


def test_run_decrypt_job_rejects_empty_input():
    result = media_decrypt.run_decrypt_job("单文件", "  ", None, remove_source=False)

    assert result["summary_rows"] == [["状态", "未开始"]]
    assert "请输入文件或文件夹路径" in result["result_text"]


def test_run_decrypt_job_reports_missing_umcli(tmp_path):
    wrapper = Mock()
    wrapper.is_available.return_value = False
    wrapper.binary = tmp_path / "um-cli.exe"

    with patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper):
        result = media_decrypt.run_decrypt_job("单文件", "song.ncm", None, remove_source=False)

    assert result["summary_rows"] == [["状态", "um-cli 未安装"]]
    assert str(wrapper.binary) in result["result_text"]


def test_run_decrypt_job_single_file_success_without_assets(tmp_path):
    ws = workspace(tmp_path)
    wrapper = Mock()
    wrapper.is_available.return_value = True
    wrapper.decrypt.return_value = {"success": True, "output": "ok"}
    output_dir = tmp_path / "out"

    with (
        patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper),
        patch.object(media_decrypt, "get_current_workspace", return_value=ws),
    ):
        result = media_decrypt.run_decrypt_job("file", " song.ncm ", str(output_dir), remove_source=True)

    wrapper.decrypt.assert_called_once_with("song.ncm", str(output_dir), True, cancel_check=None)
    assert ["状态", "成功"] in result["summary_rows"]
    assert ["模式", "单文件"] in result["summary_rows"]
    assert ["输出目录", str(output_dir)] in result["summary_rows"]
    assert not any(row[0] == "删除源文件" for row in result["summary_rows"])


def test_run_decrypt_job_batch_success_copies_created_files_to_assets(tmp_path):
    ws = workspace(tmp_path)
    output_dir = tmp_path / "album-out"
    output_dir.mkdir()
    wrapper = Mock()
    wrapper.is_available.return_value = True

    def decrypt_batch(*args, **kwargs):
        (output_dir / "song.flac").write_text("music", encoding="utf-8")
        return {"success": True, "output": "done"}

    wrapper.decrypt_batch.side_effect = decrypt_batch

    with (
        patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper),
        patch.object(media_decrypt, "get_current_workspace", return_value=ws),
    ):
        result = media_decrypt.run_decrypt_job(
            "folder",
            str(tmp_path / "album"),
            str(output_dir),
            remove_source=False,
            add_to_assets=True,
            cancel_check=lambda: False,
        )

    wrapper.decrypt_batch.assert_called_once()
    assert (Path(ws["assets_dir"]) / "song.flac").exists()
    assert ["状态", "成功"] in result["summary_rows"]
    assert ["输出目录", str(output_dir)] in result["summary_rows"]


def test_run_decrypt_job_skips_copy_when_output_is_assets_dir(tmp_path):
    ws = workspace(tmp_path)
    assets_dir = Path(ws["assets_dir"])
    wrapper = Mock()
    wrapper.is_available.return_value = True
    wrapper.decrypt.return_value = {"success": True, "output": "ok"}

    with (
        patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper),
        patch.object(media_decrypt, "get_current_workspace", return_value=ws),
    ):
        result = media_decrypt.run_decrypt_job(
            "单文件",
            "song.ncm",
            str(assets_dir),
            remove_source=False,
            add_to_assets=True,
        )

    assert ["状态", "成功"] in result["summary_rows"]
    assert ["输出目录", str(assets_dir)] in result["summary_rows"]


def test_run_decrypt_job_failure_and_exception(tmp_path):
    wrapper = Mock()
    wrapper.is_available.return_value = True
    wrapper.decrypt.return_value = {"success": False, "error": "bad format"}

    with patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper):
        failed = media_decrypt.run_decrypt_job("单文件", "song.ncm", str(tmp_path), remove_source=False)

    assert failed["summary_rows"][0] == ["状态", "失败"]
    assert "bad format" in failed["result_text"]

    wrapper.decrypt.side_effect = RuntimeError("boom")
    with patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper):
        errored = media_decrypt.run_decrypt_job("单文件", "song.ncm", str(tmp_path), remove_source=False)

    assert errored["summary_rows"][0] == ["状态", "异常"]
    assert "boom" in errored["result_text"]


def test_status_text_helpers(tmp_path):
    with patch.object(
        media_decrypt,
        "YtdlpAdapter",
        return_value=Mock(get_status=Mock(return_value={"installed": True, "version": "1", "path": "yt-dlp"})),
    ):
        assert "已安装" in media_decrypt.get_ytdlp_status_text()

    with patch.object(
        media_decrypt,
        "FFmpegAdapter",
        return_value=Mock(get_info=Mock(return_value={"installed": False, "bin_dir": str(tmp_path)})),
    ):
        assert str(tmp_path) in media_decrypt.get_ffmpeg_status_text()

    wrapper = Mock()
    wrapper.is_available.return_value = False
    wrapper.get_version.return_value = "unknown"
    wrapper.binary = "um-cli"
    with patch.object(media_decrypt, "UmcliAdapter", return_value=wrapper):
        assert "未安装" in media_decrypt.get_um_status_text()


def test_build_umcli_missing_source_and_subprocess_outcomes(tmp_path):
    # __file__ 深度需与 backend/services/media/decrypt.py 一致，便于 build_umcli() 用 parents[3] 解析仓库根
    fake_service_file = tmp_path / "backend" / "services" / "media" / "decrypt.py"
    fake_service_file.parent.mkdir(parents=True)
    fake_service_file.write_text("", encoding="utf-8")

    with patch.object(media_decrypt, "__file__", str(fake_service_file)):
        assert "go.mod 不存在" in media_decrypt.build_umcli()

    repo_root = tmp_path
    vendor = repo_root / "vendor" / "um-cli" / "source"
    vendor.mkdir(parents=True)
    (vendor / "go.mod").write_text("module test", encoding="utf-8")

    with (
        patch.object(media_decrypt, "__file__", str(fake_service_file)),
        patch("subprocess.run", return_value=Mock(returncode=0)),
        patch("platform.system", return_value="Windows"),
    ):
        assert "编译成功" in media_decrypt.build_umcli()

    with (
        patch.object(media_decrypt, "__file__", str(fake_service_file)),
        patch("subprocess.run", return_value=Mock(returncode=1, stderr="compile failed")),
    ):
        assert "compile failed" in media_decrypt.build_umcli()

    with (
        patch.object(media_decrypt, "__file__", str(fake_service_file)),
        patch("subprocess.run", side_effect=RuntimeError("go missing")),
    ):
        assert "go missing" in media_decrypt.build_umcli()
