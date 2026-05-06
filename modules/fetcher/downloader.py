"""
视频下载器

通过 subprocess 调用 bin/yt-dlp 独立二进制执行下载，
支持 YouTube、抖音、TikTok、B站及 yt-dlp 支持的所有平台。
"""
import glob
import json
import os
import platform
import subprocess
from pathlib import Path

from adapters import FFmpegAdapter, YtdlpAdapter
from modules.fetcher.subtitle import SubtitleProcessor

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


class VideoDownloader:
    def __init__(self, output_dir: str, naming_template: str, progress_callback=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.naming_template = naming_template
        self.progress_callback = progress_callback

        self._ytdlp = YtdlpAdapter()
        self._ffmpeg = FFmpegAdapter()
        self._ffmpeg_location = self._ffmpeg.get_ffmpeg_location()

    def get_video_info(self, url: str) -> dict:
        """获取视频元信息（不下载）"""
        cmd = [
            "--dump-json",
            "--no-playlist",
            "--quiet",
            url,
        ]
        try:
            result = self._ytdlp.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                context={"operation": "info", "url": url},
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr[:300])
            info = json.loads(result.stdout)
            return self._normalize_info(info)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析视频信息失败: {e}")

    def download_video(self, url: str, index: int = 1, info: dict = None, codec_preference: str = "h264") -> dict:
        """下载视频（最佳质量 mp4）"""
        if info is None:
            info = self.get_video_info(url)

        filename = self._apply_naming_template(info, index)
        output_tmpl = str(self.output_dir / f"{filename}.%(ext)s")
        format_selector = self._video_format_selector(codec_preference)

        cmd = [
            "--format", format_selector,
            "--merge-output-format", "mp4",
            "--output", output_tmpl,
        ]
        if self._ffmpeg_location:
            cmd += ["--ffmpeg-location", self._ffmpeg_location]
        cmd.append(url)

        log_file = os.path.join(self.output_dir, f".yt-dlp-{info.get('video_id', index)}.log")
        try:
            with open(log_file, "w", encoding="utf-8") as log:
                result = subprocess.run(
                    self._ytdlp.build_command(cmd, {"operation": "download", "url": url, "codec_preference": codec_preference}),
                    stdout=log, stderr=log, text=True, timeout=3600,
                    creationflags=_SUBPROCESS_FLAGS,
                )
            if result.returncode == 0:
                info["video_status"] = "success"
                info["video_error"] = ""
            else:
                # 读取日志最后几行作为错误信息
                # 使用 errors="replace" 避免 GBK/GB2312 等非 UTF-8 编码导致 UnicodeDecodeError
                try:
                    with open(log_file, encoding="utf-8", errors="replace") as log:
                        error_lines = [l.strip() for l in log.readlines()[-5:] if l.strip()]
                        error_detail = " | ".join(error_lines) if error_lines else "yt-dlp 返回非零退出码"
                except Exception:
                    error_detail = "yt-dlp 返回非零退出码"
                info["video_status"] = "failed"
                info["video_error"] = error_detail
        except subprocess.TimeoutExpired:
            info["video_status"] = "failed"
            info["video_error"] = "下载超时"
        except Exception as e:
            info["video_status"] = "failed"
            info["video_error"] = str(e)

        video_path = self._find_downloaded_file(self.output_dir, filename, [".mp4", ".mkv", ".webm", ".m4a", ".flv", ".mov", ".ts"])
        info["local_path"] = str(video_path) if video_path else ""
        return info

    def download_subtitles_only(
        self,
        url: str,
        index: int = 1,
        info: dict = None,
        subtitle_mode: str = "original_only",
        subtitle_formats: list[str] | None = None,
    ) -> dict:
        """
        仅下载字幕（跳过视频）。
        """
        if info is None:
            info = self.get_video_info(url)

        if subtitle_mode == "none":
            return {"original": {}, "zh": {}, "errors": []}

        filename = self._apply_naming_template(info, index)
        output_tmpl = str(self.output_dir / f"{filename}.%(ext)s")
        lang = (info.get("language") or "en").split("-")[0]
        formats = [fmt.lower() for fmt in (subtitle_formats or ["srt", "vtt"]) if fmt]
        normalized_formats = [fmt for fmt in formats if fmt in {"srt", "vtt", "ass", "ssa"}] or ["srt", "vtt"]
        errors: list[str] = []

        self._download_subtitle_family(
            url,
            output_tmpl,
            lang,
            normalized_formats,
            errors,
            include_manual=True,
            include_auto=True,
        )

        self._download_subtitle_family(
            url,
            output_tmpl,
            "zh-Hans",
            normalized_formats,
            errors,
            include_manual=False,
            include_auto=True,
        )

        self._ensure_srt_subtitle_outputs(filename, normalized_formats, errors)
        outputs = self._collect_subtitle_outputs(filename)
        outputs = self._prune_duplicate_subtitle_outputs(outputs)
        outputs["errors"] = errors
        return outputs

    def _video_format_selector(self, codec_preference: str) -> str:
        preference = (codec_preference or "h264").lower()
        if preference == "best":
            return "bestvideo+bestaudio/best"
        if preference == "h264":
            return (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[vcodec^=avc1]+bestaudio/"
                "best[ext=mp4][vcodec^=avc1]/"
                "best[vcodec^=avc1]"
            )
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    def _download_subtitle_family(
        self,
        url: str,
        output_tmpl: str,
        language: str,
        formats: list[str],
        errors: list[str],
        *,
        include_manual: bool,
        include_auto: bool,
    ) -> None:
        base_cmd = [
            "--skip-download",
            "--sub-langs",
            language,
            "--output",
            output_tmpl,
        ]
        if include_manual:
            base_cmd.append("--write-subs")
        if include_auto:
            base_cmd.append("--write-auto-subs")

        download_formats: list[tuple[str, str]] = []
        seen_download_formats: set[str] = set()
        for fmt in formats:
            download_fmt = "vtt" if fmt == "srt" else fmt
            if download_fmt not in seen_download_formats:
                download_formats.append((fmt, download_fmt))
                seen_download_formats.add(download_fmt)

        for requested_fmt, fmt in download_formats:
            cmd = list(base_cmd)
            if fmt == "vtt":
                cmd += ["--sub-format", "vtt"]
            else:
                cmd += ["--sub-format", "vtt", "--convert-subs", fmt]
            cmd.append(url)

            try:
                result = subprocess.run(
                    self._ytdlp.build_command(cmd, {"operation": "subtitle", "url": url, "language": language, "format": fmt}),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=_SUBPROCESS_FLAGS,
                )
                if result.returncode != 0:
                    detail = self._extract_error_detail(result.stderr)
                    if detail:
                        errors.append(f"{language}/{requested_fmt}: {detail}")
            except Exception as exc:
                errors.append(f"{language}/{requested_fmt}: {exc}")

    def _ensure_srt_subtitle_outputs(self, base_name: str, formats: list[str], errors: list[str]) -> None:
        if "srt" not in formats:
            return

        processor = SubtitleProcessor()
        for vtt_path in self.output_dir.glob(f"{glob.escape(base_name)}*.vtt"):
            srt_path = vtt_path.with_suffix(".srt")
            try:
                processor.convert_vtt_to_srt(str(vtt_path), str(srt_path))
            except Exception as exc:
                errors.append(f"{vtt_path.name}/srt: {exc}")

    def _collect_subtitle_outputs(self, base_name: str) -> dict:
        outputs = {"original": {}, "zh": {}}
        sub_files = []
        for ext in ("vtt", "srt", "ass", "ssa"):
            sub_files.extend(self.output_dir.glob(f"{glob.escape(base_name)}*.{ext}"))
        for sub in sub_files:
            lang_code = sub.stem[len(base_name):].lstrip(".")
            lang_lower = lang_code.lower()
            is_zh = lang_lower == "zh" or lang_lower.startswith("zh-")
            bucket = "zh" if is_zh else "original"
            outputs[bucket].setdefault(sub.suffix.lower().lstrip("."), str(sub))
        return outputs

    def _prune_duplicate_subtitle_outputs(self, outputs: dict) -> dict:
        for bucket in ("original", "zh"):
            bucket_outputs = outputs.get(bucket, {})
            srt_path = bucket_outputs.get("srt")
            vtt_path = bucket_outputs.get("vtt")
            if not srt_path or not vtt_path:
                continue
            vtt_file = Path(vtt_path)
            try:
                if vtt_file.exists():
                    vtt_file.unlink()
            except OSError:
                # Keep the VTT entry if cleanup fails unexpectedly.
                continue
            bucket_outputs.pop("vtt", None)
        return outputs

    def _extract_error_detail(self, stderr: str) -> str:
        lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
        for line in reversed(lines):
            if "ERROR" in line or "error" in line.lower():
                return line
        return lines[-1] if lines else ""

    def _normalize_info(self, info: dict) -> dict:
        best_fmt = {}
        formats = info.get("formats") or []
        for fmt in formats:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none" and fmt.get("ext"):
                best_fmt = fmt
        if not best_fmt and formats:
            best_fmt = formats[-1]

        return {
            "video_id": info.get("id") or "",
            "url": info.get("webpage_url") or info.get("url") or "",
            "webpage_url": info.get("webpage_url") or "",
            "direct_media_url": best_fmt.get("url") or info.get("url") or "",
            "title": info.get("title") or "",
            "uploader": info.get("uploader") or info.get("channel") or "",
            "extractor": info.get("extractor") or "",
            "extractor_key": info.get("extractor_key") or "",
            "protocol": best_fmt.get("protocol") or info.get("protocol") or "",
            "format_id": best_fmt.get("format_id") or info.get("format_id") or "",
            "ext": best_fmt.get("ext") or info.get("ext") or "",
            "http_headers": best_fmt.get("http_headers") or info.get("http_headers") or {},
            "duration": info.get("duration") or 0,
            "upload_date": info.get("upload_date") or "",
            "view_count": info.get("view_count") or 0,
            "like_count": info.get("like_count") or 0,
            "language": info.get("language") or "en",
            "resolution": best_fmt.get("resolution") or best_fmt.get("format_note") or "",
            "fps": best_fmt.get("fps") or 0,
            "file_size_mb": round((best_fmt.get("filesize") or 0) / (1024 * 1024), 2),
            "categories": "; ".join(info.get("categories") or []),
            "tags": "; ".join(info.get("tags") or []),
            "has_manual_subs": bool(info.get("subtitles")),
            "has_auto_subs": bool(info.get("automatic_captions")),
            "local_path": "",
            "subtitle_path": "",
            "highlights_count": 0,
        }

    def _apply_naming_template(self, info: dict, index: int) -> str:
        mapping = {
            "{index}": f"{index:03d}",
            "{title}": self._sanitize_filename(info.get("title") or "unknown"),
            "{uploader}": self._sanitize_filename(info.get("uploader") or ""),
            "{upload_date}": info.get("upload_date") or "unknown",
            "{video_id}": info.get("video_id") or "",
            "{duration}": str(info.get("duration") or 0),
            "{language}": info.get("language") or "unknown",
        }
        name = self.naming_template
        for key, value in mapping.items():
            name = name.replace(key, value)
        return name

    def _sanitize_filename(self, name: str) -> str:
        for ch in r'<>:"/\|?*':
            name = name.replace(ch, "_")
        return name[:80].strip()

    def _find_downloaded_file(self, directory: Path, base_name: str, extensions: list) -> Path | None:
        for ext in extensions:
            path = directory / f"{base_name}{ext}"
            if path.exists():
                return path
        return None
