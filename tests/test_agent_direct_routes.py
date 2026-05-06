"""Tests for direct local agent routing."""

from unittest.mock import Mock

from backend.services.agent_direct_routes import try_direct_route


def base_kwargs(**overrides):
    kwargs = {
        "api_key": "key",
        "base_url": "https://api.example.com",
        "model": "model-a",
        "get_current_workspace_fn": Mock(return_value={"project_root": "D:\\MediaTools"}),
        "run_fetch_analyze_slice_job_fn": Mock(),
        "tool_scan_assets_fn": Mock(),
        "tool_execute_decrypt_to_assets_fn": Mock(),
    }
    kwargs.update(overrides)
    return kwargs


def test_try_direct_route_returns_none_for_unmatched_task():
    result = try_direct_route("普通聊天", "", **base_kwargs())

    assert result is None


def test_fetch_analyze_slice_requires_url():
    kwargs = base_kwargs()

    result = try_direct_route("下载并自动切片", "", **kwargs)

    assert result["ok"] is False
    assert "补充 URL" in result["answer"]
    assert result["actions"][0]["status"] == "error"
    assert "direct_fetch_analyze_slice" in result["tool_trace_text"]
    kwargs["run_fetch_analyze_slice_job_fn"].assert_not_called()


def test_fetch_analyze_slice_runs_each_url_and_combines_results(tmp_path):
    output_dir = tmp_path / "clips"
    output_dir.mkdir()
    clip = output_dir / "clip.mp4"
    clip.write_bytes(b"clip")
    fetch_job = Mock(
        side_effect=[
            {
                "ok": True,
                "message": "done",
                "video_info": {"title": "A"},
                "video_path": str(tmp_path / "a.mp4"),
                "subtitle_path": str(tmp_path / "a.srt"),
                "analysis_path": str(tmp_path / "analysis.json"),
                "selected_clips": [{"start_time": "00:00:01", "end_time": "00:00:03", "title": "hook"}],
                "slice_result": {"output_dir": str(output_dir), "output_paths": [str(clip)]},
            },
            {"ok": False, "message": "download failed", "subtitle_errors": ["no subtitle"]},
        ]
    )
    kwargs = base_kwargs(run_fetch_analyze_slice_job_fn=fetch_job)

    result = try_direct_route(
        "请下载并切片 https://example.com/a",
        "还要处理 https://example.com/b",
        **kwargs,
    )

    assert result["ok"] is False
    assert "执行成功" in result["answer"]
    assert "执行失败" in result["answer"]
    assert fetch_job.call_count == 2
    assert fetch_job.call_args_list[0].kwargs["url"] == "https://example.com/a"
    assert fetch_job.call_args_list[0].kwargs["index"] == 1
    assert fetch_job.call_args_list[1].kwargs["url"] == "https://example.com/b"
    assert fetch_job.call_args_list[1].kwargs["model"] == "model-a"
    assert "execute_fetch_analyze_slice" in result["tool_trace_text"]
    assert any(action["kind"] == "pipeline" for action in result["actions"])
    assert any(artifact["kind"] == "directory" and artifact["path"] == str(output_dir) for artifact in result["artifacts"])


def test_asset_scan_uses_current_workspace_root():
    scan = Mock(return_value={"ok": True, "directory": "D:\\MediaTools", "total": 12})
    kwargs = base_kwargs(tool_scan_assets_fn=scan)

    result = try_direct_route("扫描项目素材", "", **kwargs)

    assert result["ok"] is True
    assert "素材数量: 12" in result["answer"]
    scan.assert_called_once_with("D:\\MediaTools")
    assert result["actions"][0]["kind"] == "scan_assets"
    assert "scan_assets" in result["tool_trace_text"]


def test_decrypt_route_requires_local_path():
    kwargs = base_kwargs()

    result = try_direct_route("解密音乐文件", "", **kwargs)

    assert result["ok"] is False
    assert "本地文件路径" in result["answer"]
    assert result["actions"][0]["status"] == "error"
    kwargs["tool_execute_decrypt_to_assets_fn"].assert_not_called()


def test_decrypt_route_executes_first_path_and_returns_artifact(tmp_path):
    output_dir = tmp_path / "assets"
    output_dir.mkdir()
    decrypt = Mock(return_value={"ok": True, "result_text": "解密成功", "output_dir": str(output_dir)})
    kwargs = base_kwargs(tool_execute_decrypt_to_assets_fn=decrypt)

    result = try_direct_route("请解密 D:\\Music\\song.ncm", "另外 D:\\Music\\other.ncm", **kwargs)

    assert result["ok"] is True
    assert result["answer"] == "解密成功"
    decrypt.assert_called_once_with("D:\\Music\\song.ncm")
    assert result["actions"][0]["kind"] == "decrypt"
    assert result["actions"][0]["status"] == "done"
    assert result["artifacts"][0]["kind"] == "directory"
    assert result["artifacts"][0]["path"] == str(output_dir)


def test_decrypt_route_reports_tool_failure_without_artifact():
    decrypt = Mock(return_value={"ok": False, "result_text": "解密失败", "output_dir": ""})
    kwargs = base_kwargs(tool_execute_decrypt_to_assets_fn=decrypt)

    result = try_direct_route("解密 D:\\Music\\bad.kgm", "", **kwargs)

    assert result["ok"] is False
    assert result["answer"] == "解密失败"
    assert result["actions"][0]["status"] == "error"
    assert result["artifacts"] == []
