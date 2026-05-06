from types import SimpleNamespace

from modules.fetcher.analyzer import (
    MAX_SUBTITLE_CHARS,
    TRUNCATION_MARKER,
    SubtitleAnalyzer,
    _normalize_highlights,
    _truncate_subtitle_text,
)


class FakeCompletions:
    def __init__(self, content="", exc=None):
        self.content = content
        self.exc = exc
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, content="", exc=None):
        self.completions = FakeCompletions(content=content, exc=exc)
        self.chat = SimpleNamespace(completions=self.completions)


def test_truncate_subtitle_text_keeps_short_text_unchanged():
    assert _truncate_subtitle_text("hello") == "hello"


def test_truncate_subtitle_text_prefers_recent_line_boundary():
    text = ("a" * (MAX_SUBTITLE_CHARS - 100)) + "\n" + ("b" * 300)

    truncated = _truncate_subtitle_text(text)

    assert truncated.endswith(TRUNCATION_MARKER)
    assert "b" not in truncated


def test_normalize_highlights_accepts_wrapped_list_and_sets_summary():
    highlights = _normalize_highlights({"highlights": [{"reason": "good"}, "skip"]})

    assert highlights == [{"reason": "good", "summary_zh": "good"}]


def test_normalize_highlights_accepts_single_dict():
    highlights = _normalize_highlights({"title": "clip", "summary_zh": "ready"})

    assert highlights == [{"title": "clip", "summary_zh": "ready"}]


def test_analyze_returns_normalized_json_and_passes_model_override():
    client = FakeClient(content='{"highlights": [{"reason": "strong hook"}]}')
    analyzer = SubtitleAnalyzer(api_key="key", base_url="http://api", model="default", client=client)

    result = analyzer.analyze("subtitle text", model="override")

    assert result == [{"reason": "strong hook", "summary_zh": "strong hook"}]
    assert client.completions.calls[0]["model"] == "override"
    assert client.completions.calls[0]["messages"][1]["content"] == "subtitle text"


def test_analyze_returns_empty_list_for_invalid_json():
    analyzer = SubtitleAnalyzer(api_key="key", base_url="http://api", client=FakeClient(content="not json"))

    assert analyzer.analyze("subtitle text") == []


def test_analyze_returns_empty_list_for_client_error():
    analyzer = SubtitleAnalyzer(api_key="key", base_url="http://api", client=FakeClient(exc=RuntimeError("boom")))

    assert analyzer.analyze("subtitle text") == []


def test_analyze_from_srt_uses_processor_text():
    client = FakeClient(content='[{"summary_zh": "ok"}]')
    analyzer = SubtitleAnalyzer(api_key="key", base_url="http://api", client=client)
    processor = SimpleNamespace(
        parse_srt=lambda path: [{"path": path}],
        format_for_llm=lambda segments: f"text from {segments[0]['path']}",
    )

    highlights, text = analyzer.analyze_from_srt("clip.srt", processor)

    assert highlights == [{"summary_zh": "ok"}]
    assert text == "text from clip.srt"
