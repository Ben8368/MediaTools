"""Direct local task routes for the media agent."""

from __future__ import annotations

from backend.agent.helpers import (
    _extract_local_paths,
    _extract_urls,
    _format_fetch_analyze_slice_answer,
    _looks_like_asset_scan_task,
    _looks_like_decrypt_task,
    _looks_like_fetch_analyze_slice_task,
    _make_action,
    _make_artifact,
    _response,
    _summarize_tool_result,
)


def try_direct_route(
    task: str,
    extra_context: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
    get_current_workspace_fn,
    run_fetch_analyze_slice_job_fn,
    tool_scan_assets_fn,
    tool_execute_decrypt_to_assets_fn,
) -> dict | None:
    combined = f"{task}\n{extra_context}".strip()

    if _looks_like_fetch_analyze_slice_task(combined):
        urls = _extract_urls(combined)
        if not urls:
            return _response(
                False,
                "没有检测到可执行的下载链接，请补充 URL。",
                [{"route": "direct_fetch_analyze_slice", "result": "missing_url"}],
                [_make_action("pipeline", "下载并分析切片", "error", "未提供可执行 URL")],
                [],
            )

        tool_traces: list[dict] = []
        actions: list[dict] = []
        artifacts: list[dict] = []
        outputs: list[str] = []
        overall_ok = True

        for index, url in enumerate(urls, 1):
            result = run_fetch_analyze_slice_job_fn(
                url=url,
                index=index,
                video_codec_preference="h264",
                subtitle_mode="original_only",
                subtitle_formats=["srt"],
                clip_count=3,
                accurate_slice=True,
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            tool_traces.append(
                {
                    "tool": "execute_fetch_analyze_slice",
                    "arguments": {"url": url, "index": index, "clip_count": 3, "video_codec_preference": "h264"},
                    "result": result,
                }
            )
            new_actions, new_artifacts = _summarize_tool_result("execute_fetch_analyze_slice", {"url": url}, result)
            actions.extend(new_actions)
            artifacts.extend(new_artifacts)
            outputs.append(_format_fetch_analyze_slice_answer(result))
            overall_ok = overall_ok and bool(result.get("ok"))

        return _response(overall_ok, "\n\n---\n\n".join(outputs), tool_traces, actions, artifacts)

    if _looks_like_asset_scan_task(combined):
        workspace = get_current_workspace_fn()
        result = tool_scan_assets_fn(workspace["project_root"])
        tool_traces = [{"tool": "scan_assets", "arguments": {"directory": workspace["project_root"]}, "result": result}]
        actions, artifacts = _summarize_tool_result("scan_assets", {"directory": workspace["project_root"]}, result)
        answer = f"已扫描素材目录。\n\n目录: {workspace['project_root']}\n素材数量: {result.get('total', 0)}"
        return _response(True, answer, tool_traces, actions, artifacts)

    if _looks_like_decrypt_task(combined):
        paths = _extract_local_paths(combined)
        if not paths:
            return _response(
                False,
                "没有识别到可解密的本地文件路径。",
                [{"route": "direct_decrypt_to_assets", "result": "missing_path"}],
                [_make_action("decrypt", "自动解密到素材区", "error", "未提供待解密文件路径")],
                [],
            )

        path = paths[0]
        result = tool_execute_decrypt_to_assets_fn(path)
        tool_traces = [{"tool": "execute_decrypt_to_assets", "arguments": {"input_path": path}, "result": result}]
        actions = [
            _make_action(
                "decrypt",
                "自动解密到素材区",
                "done" if result.get("ok") else "error",
                result.get("result_text", ""),
            )
        ]
        artifacts = []
        artifact = _make_artifact(result.get("output_dir", ""), "directory", "解密输出目录")
        if artifact:
            artifacts.append(artifact)
        return _response(bool(result.get("ok")), result.get("result_text", ""), tool_traces, actions, artifacts)

    return None
