import html
import re
from pathlib import Path


class SubtitleProcessor:
    """字幕处理器，封装 VTT 解析、去重、格式转换等操作。"""

    def convert_vtt_to_srt(self, vtt_path: str, output_path: str = None) -> str:
        return convert_vtt_to_srt(vtt_path, output_path)

    def parse_srt(self, srt_path: str) -> list:
        """解析 SRT 文件，返回 [{index, start, end, text}, ...] 列表。"""
        segments = []
        content = Path(srt_path).read_text(encoding="utf-8-sig")
        blocks = re.split(r"\n\s*\n", content.strip())
        for block in blocks:
            lines = block.strip().splitlines()
            if len(lines) < 3:
                continue
            try:
                index = int(lines[0].strip())
            except ValueError:
                continue
            time_match = re.match(
                r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                lines[1].strip(),
            )
            if not time_match:
                continue
            text = " ".join(l.strip() for l in lines[2:] if l.strip())
            segments.append({
                "index": index,
                "start": time_match.group(1),
                "end": time_match.group(2),
                "text": text,
            })
        return segments

    def format_for_llm(self, segments: list) -> str:
        """将字幕段列表格式化为适合 LLM 分析的纯文本。"""
        lines = []
        for seg in segments:
            lines.append(f"[{seg['start']} --> {seg['end']}] {seg['text']}")
        return "\n".join(lines)

    def convert_vtt_to_text(self, vtt_path: str) -> str:
        """将 VTT 文件直接转为适合 LLM 分析的文本（不写出 SRT 文件）。"""
        text = Path(vtt_path).read_text(encoding="utf-8-sig")
        segments = _parse_vtt(text)
        segments = _deduplicate_vtt_segments(segments)
        lines = []
        for seg in segments:
            lines.append(f"[{seg['start']} --> {seg['end']}] {seg['text']}")
        return "\n".join(lines)


def _clean_vtt_text(text: str) -> str:
    """修复 Bug 7: 完整清理 VTT 标签，包括语音标签 <v...> 和样式标签"""
    text = html.unescape(text)
    # 移除 VTT 样式类 <c.xxx> / </c>
    text = re.sub(r'<c\.[^>]*>', '', text)
    text = re.sub(r'</c>', '', text)
    # 移除语音标签的前缀名 <v Name> -> 只移除标签，保留内容
    text = re.sub(r'<v[^>]*>', '', text)
    # 移除所有剩余 HTML/VTT 标签 <...>
    text = re.sub(r'<[^>]+>', '', text)
    # 清理常见的字幕前缀噪声，如 >> / >>>
    text = re.sub(r'^(?:>+\s*)+', '', text)
    # 合并多余空格
    return " ".join(text.split()).strip()


def _timestamp_to_millis(value: str) -> int:
    normalized = value.replace(",", ".")
    parts = normalized.split(":")
    if len(parts) != 3:
        return 0
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds, millis = parts[2].split(".")
    return ((hours * 60 + minutes) * 60 + int(seconds)) * 1000 + int(millis)


def _normalize_vtt_timestamp(value: str) -> str:
    raw = value.replace('.', ',')
    parts = raw.split(':')
    if len(parts) == 2:
        return f"00:{parts[0]}:{parts[1]}"
    return raw


def _word_overlap_size(left: str, right: str) -> int:
    left_words = left.split()
    right_words = right.split()
    max_overlap = min(len(left_words), len(right_words))
    for size in range(max_overlap, 0, -1):
        if left_words[-size:] == right_words[:size]:
            return size
    return 0


def _join_text_with_overlap(left: str, right: str) -> str:
    overlap = _word_overlap_size(left, right)
    if overlap <= 0:
        return f"{left} {right}".strip()
    right_words = right.split()
    return " ".join(left.split() + right_words[overlap:]).strip()


def _parse_vtt(text: str) -> list:
    """修复 Bug 6: 精确匹配时间戳格式"""
    segments = []
    # 匹配 00:00:07.830 或 00:07.830 等常见 VTT 时间戳格式
    pattern = re.compile(r'((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})')

    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line_stripped = lines[i].strip()
        # 跳过 WEBVTT 头部、STYLE 块、NOTE 注释、元数据行
        if line_stripped.startswith(('WEBVTT', 'NOTE', 'STYLE', 'Kind:', 'Language:')) or line_stripped == '':
            i += 1
            continue

        match = pattern.search(lines[i])
        if match:
            start = _normalize_vtt_timestamp(match.group(1))
            end = _normalize_vtt_timestamp(match.group(2))

            text_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip():
                # 如果遇到下一个时间戳，停止收集
                if pattern.search(lines[j]):
                    break
                text_lines.append(lines[j].strip())
                j += 1

            raw_text = " ".join(text_lines)
            clean_text = _clean_vtt_text(raw_text)

            if clean_text:
                segments.append({
                    "start": start,
                    "end": end,
                    "text": clean_text
                })
            i = j
        else:
            i += 1
    return segments


def _deduplicate_vtt_segments(segments: list, threshold: float = 0.85) -> list:
    """保守去重：仅移除真正重复的 cue，避免把正常逐句字幕合并成长段。"""
    if not segments:
        return []

    cleaned = [segments[0].copy()]
    for seg in segments[1:]:
        prev = cleaned[-1]
        prev_text = prev["text"].strip()
        curr_text = seg["text"].strip()
        prev_end = _timestamp_to_millis(prev["end"])
        curr_start = _timestamp_to_millis(seg["start"])
        curr_end = _timestamp_to_millis(seg["end"])
        curr_duration = max(0, curr_end - curr_start)
        time_gap = max(0, curr_start - prev_end)

        if prev_text == curr_text:
            if curr_end > prev_end:
                prev["end"] = seg["end"]
            continue

        if time_gap <= 120:
            if curr_duration <= 120 and (curr_text in prev_text or prev_text.endswith(curr_text)):
                if curr_end > prev_end:
                    prev["end"] = seg["end"]
                continue

            if prev_text in curr_text:
                prev["text"] = curr_text
                prev["end"] = seg["end"]
                continue

            overlap = _word_overlap_size(prev_text, curr_text)
            if overlap >= 3:
                prev["text"] = _join_text_with_overlap(prev_text, curr_text)
                prev["end"] = seg["end"]
                continue

        cleaned.append(seg.copy())

    for idx, seg in enumerate(cleaned, 1):
        seg["index"] = idx
    return cleaned


def convert_vtt_to_srt(vtt_path: str, output_path: str = None) -> str:
    text = Path(vtt_path).read_text(encoding="utf-8-sig")
    segments = _parse_vtt(text)

    # 应用去重优化
    segments = _deduplicate_vtt_segments(segments)

    srt_lines = []
    for index, seg in enumerate(segments, 1):
        srt_lines.append(f"{index}\n{seg['start']} --> {seg['end']}\n{seg['text']}\n")

    srt_text = "\n".join(srt_lines)

    if not output_path:
        output_path = Path(vtt_path).with_suffix('.srt')
    else:
        output_path = Path(output_path)

    output_path.write_text(srt_text, encoding="utf-8")
    return str(output_path)
