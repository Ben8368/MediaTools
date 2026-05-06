"""Tests for MediaAgentService model orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import services.agent as agent
from services.agent import MediaAgentService


class _FakeToolCall:
    def __init__(self, name: str, arguments: str = "{}") -> None:
        self.id = f"call-{name}"
        self.function = SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class _FakeChatClient:
    def __init__(self, messages: list[SimpleNamespace] | None = None, error: Exception | None = None) -> None:
        self.messages = list(messages or [])
        self.error = error
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        snapshot = dict(kwargs)
        if "messages" in snapshot:
            snapshot["messages"] = list(snapshot["messages"])
        self.calls.append(snapshot)
        if self.error:
            raise self.error
        message = self.messages.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _message(content: str = "", tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def test_client_is_lazy_and_requires_api_key(monkeypatch):
    created: list[dict] = []

    class FakeOpenAI:
        def __init__(self, api_key: str, base_url: str) -> None:
            created.append({"api_key": api_key, "base_url": base_url})

    monkeypatch.setattr(agent, "OpenAI", FakeOpenAI)

    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")

    first = service.client
    second = service.client

    assert first is second
    assert created == [{"api_key": "secret", "base_url": "https://api.example.com"}]

    monkeypatch.setattr(agent, "get_api_config", lambda: {"api_key": "", "api_base_url": "https://api.example.com", "analysis_model": "model-a"})
    with pytest.raises(ValueError, match="API key"):
        MediaAgentService(api_key="", base_url="https://api.example.com", model="model-a").client


def test_test_connection_success_and_failure():
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")
    service._client = _FakeChatClient([_message("ok")])  # type: ignore[assignment]

    result = service.test_connection()

    assert result == {"ok": True, "message": "ok"}
    assert service._client.calls[0]["model"] == "model-a"  # type: ignore[union-attr]
    assert service._client.calls[0]["max_tokens"] == 8  # type: ignore[union-attr]

    failing = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")
    failing._client = _FakeChatClient(error=RuntimeError("network down"))  # type: ignore[assignment]

    assert failing.test_connection() == {"ok": False, "message": "network down"}


def test_test_connection_uses_completion_tokens_for_gpt5_models():
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="gpt-5.4")
    service._client = _FakeChatClient([_message("ok")])  # type: ignore[assignment]

    result = service.test_connection()

    assert result == {"ok": True, "message": "ok"}
    assert service._client.calls[0]["max_completion_tokens"] == 8  # type: ignore[union-attr]
    assert "max_tokens" not in service._client.calls[0]  # type: ignore[operator,union-attr]


def test_run_tool_unknown_and_mapping_defaults(monkeypatch):
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")

    assert service._run_tool("missing_tool", {})["ok"] is False

    calls: list[dict] = []
    monkeypatch.setattr(
        agent,
        "_tool_execute_transcode",
        lambda input_path, codec, output_path="", crf=23, preset="medium": calls.append(
            {
                "input_path": input_path,
                "codec": codec,
                "output_path": output_path,
                "crf": crf,
                "preset": preset,
            }
        )
        or {"ok": True},
    )

    assert service._run_tool("execute_transcode", {"input_path": "in.mp4", "codec": "h265"}) == {"ok": True}
    assert calls == [{"input_path": "in.mp4", "codec": "h265", "output_path": "", "crf": 23, "preset": "medium"}]


def test_execute_uses_direct_route_before_model_client():
    service = MediaAgentService(api_key="", base_url="https://api.example.com", model="model-a")
    service._try_direct_route = Mock(return_value={"ok": True, "answer": "direct", "tool_traces": []})  # type: ignore[method-assign]

    result = service.execute("scan local assets")

    assert result["answer"] == "direct"
    service._try_direct_route.assert_called_once_with("scan local assets", "")


def test_execute_returns_final_model_answer_without_tool_calls():
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")
    service._try_direct_route = Mock(return_value=None)  # type: ignore[method-assign]
    service._client = _FakeChatClient([_message("final answer")])  # type: ignore[assignment]

    result = service.execute("plan this", extra_context="context line")

    assert result["ok"] is True
    assert result["answer"] == "final answer"
    assert result["actions"] == []
    assert result["artifacts"] == []
    assert "get_video_info" not in result["tool_trace_text"]
    request_messages = service._client.calls[0]["messages"]  # type: ignore[union-attr]
    assert "context line" in request_messages[1]["content"]


def test_execute_runs_tool_calls_then_returns_final_answer(monkeypatch):
    tool_call = _FakeToolCall("get_video_info", '{"url": "https://example.com/v"}')
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")
    service._try_direct_route = Mock(return_value=None)  # type: ignore[method-assign]
    service._client = _FakeChatClient([_message(tool_calls=[tool_call]), _message("done")])  # type: ignore[assignment]
    run_tool = Mock(return_value={"ok": True, "title": "Video A"})
    service._run_tool = run_tool  # type: ignore[method-assign]

    result = service.execute("inspect video")

    assert result["ok"] is True
    assert result["answer"] == "done"
    run_tool.assert_called_once_with("get_video_info", {"url": "https://example.com/v"})
    assert "get_video_info" in result["tool_trace_text"]
    assert result["actions"][0]["kind"] == "inspect_video"

    second_call_messages = service._client.calls[1]["messages"]  # type: ignore[union-attr]
    assert second_call_messages[-1]["role"] == "tool"
    assert second_call_messages[-1]["tool_call_id"] == "call-get_video_info"


def test_execute_reports_step_limit_after_repeated_tool_calls():
    service = MediaAgentService(api_key="secret", base_url="https://api.example.com", model="model-a")
    service._try_direct_route = Mock(return_value=None)  # type: ignore[method-assign]
    service._client = _FakeChatClient([_message(tool_calls=[_FakeToolCall("get_video_info")]) for _ in range(6)])  # type: ignore[assignment]
    service._run_tool = Mock(return_value={"ok": True})  # type: ignore[method-assign]

    result = service.execute("keep working")

    assert result["ok"] is False
    assert "step limit" in result["answer"]
    assert service._run_tool.call_count == 6  # type: ignore[union-attr]
