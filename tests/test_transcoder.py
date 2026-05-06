"""测试 Transcoder 模块"""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from modules.encoder.transcoder import Transcoder


class TestTranscoder(unittest.TestCase):
    def setUp(self):
        self.transcoder = Transcoder()

    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_to_h265_success(self, mock_ffmpeg):
        """测试 H.265 转码成功"""
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_result = Mock()
        mock_result.returncode = 0
        mock_adapter.run.return_value = mock_result

        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.to_h265("input.mp4", "output.mp4", crf=23)

        self.assertTrue(result["success"])
        self.assertEqual(result["output_path"], "output.mp4")
        self.assertEqual(result["error"], "")

    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_to_h265_ffmpeg_not_available(self, mock_ffmpeg):
        """测试 FFmpeg 不可用时的错误处理"""
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = False
        mock_adapter.bin_dir = "/path/to/bin"

        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.to_h265("input.mp4", "output.mp4")

        self.assertFalse(result["success"])
        self.assertIn("FFmpeg 未安装", result["error"])

    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_extract_audio_success(self, mock_ffmpeg):
        """测试音频提取成功"""
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_result = Mock()
        mock_result.returncode = 0
        mock_adapter.run.return_value = mock_result

        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.extract_audio("input.mp4", "output.mp3")

        self.assertTrue(result["success"])
        self.assertEqual(result["output_path"], "output.mp3")


    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_to_h264(self, mock_ffmpeg):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_result = Mock(returncode=0, stderr="")
        mock_adapter.run.return_value = mock_result
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.to_h264("input.mp4")
        self.assertTrue(result["success"])
        self.assertIn("h264", result["output_path"])

    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_transcode_failure(self, mock_ffmpeg):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_result = Mock(returncode=1, stderr="some error")
        mock_adapter.run.return_value = mock_result
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.transcode("input.mp4", "output.mp4")
        self.assertFalse(result["success"])
        self.assertIn("some error", result["error"])

    def test_transcode_builds_full_option_args(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_adapter.run.return_value = Mock(returncode=0, stderr="")
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.transcode(
            "input.mp4",
            "output.mp4",
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="slow",
            bitrate="4M",
        )

        self.assertTrue(result["success"])
        args = mock_adapter.run.call_args.args[0]
        self.assertEqual(
            args,
            [
                "-y",
                "-i",
                "input.mp4",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-crf",
                "18",
                "-preset",
                "slow",
                "-b:v",
                "4M",
                "output.mp4",
            ],
        )
        self.assertEqual(mock_adapter.run.call_args.kwargs["context"]["operation"], "transcode")

    def test_transcode_audio_only_skips_video_codec(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_adapter.run.return_value = Mock(returncode=0, stderr="")
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.transcode("input.mp4", "output.mp3", no_video=True, vcodec="ignored", acodec="mp3")

        self.assertTrue(result["success"])
        args = mock_adapter.run.call_args.args[0]
        self.assertIn("-vn", args)
        self.assertNotIn("-c:v", args)
        self.assertIn("mp3", args)

    def test_transcode_uses_progress_runner_and_handles_cancelled_returncode(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_adapter.run_with_progress.return_value = Mock(returncode=-1, stderr="")
        progress = Mock()
        cancel = Mock(return_value=True)
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.transcode("input.mp4", "output.mp4", progress_callback=progress, cancel_check=cancel)

        self.assertFalse(result["success"])
        self.assertIn("取消", result["error"])
        mock_adapter.run.assert_not_called()
        mock_adapter.run_with_progress.assert_called_once()
        self.assertIs(mock_adapter.run_with_progress.call_args.kwargs["progress_callback"], progress)
        self.assertIs(mock_adapter.run_with_progress.call_args.kwargs["cancel_check"], cancel)

    def test_transcode_exception_is_returned_as_failure(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        mock_adapter.run.side_effect = RuntimeError("ffmpeg crashed")
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.transcode("input.mp4", "output.mp4")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "ffmpeg crashed")

    def test_slice_video_input_not_found(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = True
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.slice_video("/nonexistent.mp4", "00:00:10", "00:00:20")
        self.assertFalse(result["success"])
        self.assertIn("不存在", result["error"])

    def test_safe_time_tag(self):
        self.assertEqual(self.transcoder._safe_time_tag("00:01:30"), "000130")
        self.assertEqual(self.transcoder._safe_time_tag("01:02:03.4567890"), "010203456789")
        self.assertEqual(self.transcoder._safe_time_tag("invalid"), "clip")

    def test_build_subtitle_filter_escapes_path(self):
        filter_text = self.transcoder._build_subtitle_filter("C:\\Videos\\it's.srt")

        self.assertIn("subtitles='", filter_text)
        self.assertIn(r"C\:", filter_text)
        self.assertIn(r"it\'s.srt", filter_text)

    @patch("modules.encoder.transcoder.FFmpegAdapter")
    def test_slice_video_success(self, mock_ffmpeg):
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            input_file = Path(tmp) / "video.mp4"
            input_file.write_bytes(b"\x00" * 10)
            output_file = str(Path(tmp) / "out.mp4")

            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_result = Mock(returncode=0, stderr="")
            mock_adapter.run.return_value = mock_result
            self.transcoder.ffmpeg = mock_adapter

            result = self.transcoder.slice_video(str(input_file), "00:00:01", "00:00:05", output_file)
            self.assertTrue(result["success"])
            args = mock_adapter.run.call_args.args[0]
            self.assertIn("-c:v", args)
            self.assertIn("libx264", args)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_slice_video_ffmpeg_not_available(self):
        mock_adapter = Mock()
        mock_adapter.is_available.return_value = False
        mock_adapter.bin_dir = "/missing/bin"
        self.transcoder.ffmpeg = mock_adapter

        result = self.transcoder.slice_video("input.mp4", "00:00:01", "00:00:05")

        self.assertFalse(result["success"])
        self.assertIn("/missing/bin", result["error"])

    def test_slice_video_fast_copy_success_and_default_output(self):
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        try:
            input_file = Path(tmp) / "video.mp4"
            input_file.write_bytes(b"video")
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.run.return_value = Mock(returncode=0, stderr="")
            self.transcoder.ffmpeg = mock_adapter

            result = self.transcoder.slice_video(str(input_file), "00:00:01", "00:00:05", accurate=False)

            self.assertTrue(result["success"])
            self.assertIn("video_000001_000005.mp4", result["output_path"])
            args = mock_adapter.run.call_args.args[0]
            self.assertLess(args.index("-ss"), args.index("-i"))
            self.assertIn("-c", args)
            self.assertIn("copy", args)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_slice_video_burn_subtitles_missing_subtitle(self):
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        try:
            input_file = Path(tmp) / "video.mp4"
            input_file.write_bytes(b"video")
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            self.transcoder.ffmpeg = mock_adapter

            result = self.transcoder.slice_video(
                str(input_file),
                "00:00:01",
                "00:00:05",
                subtitle_path=str(Path(tmp) / "missing.srt"),
                burn_subtitles=True,
            )

            self.assertFalse(result["success"])
            self.assertIn("字幕", result["error"])
            mock_adapter.run.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_slice_video_fast_burn_subtitles_reencodes(self):
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        try:
            input_file = Path(tmp) / "video.mp4"
            subtitle_file = Path(tmp) / "sub.srt"
            input_file.write_bytes(b"video")
            subtitle_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi", encoding="utf-8")
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.run.return_value = Mock(returncode=0, stderr="")
            self.transcoder.ffmpeg = mock_adapter

            result = self.transcoder.slice_video(
                str(input_file),
                "00:00:01",
                "00:00:05",
                str(Path(tmp) / "out.mp4"),
                accurate=False,
                subtitle_path=str(subtitle_file),
                burn_subtitles=True,
            )

            self.assertTrue(result["success"])
            args = mock_adapter.run.call_args.args[0]
            self.assertIn("-vf", args)
            self.assertIn("-c:v", args)
            self.assertNotIn("copy", args)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_slice_video_failure_and_exception(self):
        import shutil
        import tempfile

        tmp = tempfile.mkdtemp()
        try:
            input_file = Path(tmp) / "video.mp4"
            input_file.write_bytes(b"video")
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.run.return_value = Mock(returncode=1, stderr="slice failed")
            self.transcoder.ffmpeg = mock_adapter

            result = self.transcoder.slice_video(str(input_file), "00:00:01", "00:00:05", str(Path(tmp) / "out.mp4"))
            self.assertFalse(result["success"])
            self.assertIn("slice failed", result["error"])

            mock_adapter.run.side_effect = RuntimeError("boom")
            result = self.transcoder.slice_video(str(input_file), "00:00:01", "00:00:05", str(Path(tmp) / "out2.mp4"))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "boom")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
