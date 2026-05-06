"""Tests for PreviewGenerator"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from modules.assets.preview import PreviewGenerator


class TestPreviewGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = PreviewGenerator()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_can_preview_image(self):
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            result = self.generator.can_preview(f"/some/file{ext}")
            self.assertTrue(result["can_preview"])
            self.assertEqual(result["preview_type"], "image")

    def test_can_preview_video(self):
        for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"]:
            result = self.generator.can_preview(f"/some/file{ext}")
            self.assertTrue(result["can_preview"])
            self.assertEqual(result["preview_type"], "video")

    def test_can_preview_audio(self):
        for ext in [".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg"]:
            result = self.generator.can_preview(f"/some/file{ext}")
            self.assertTrue(result["can_preview"])
            self.assertEqual(result["preview_type"], "audio")

    def test_can_preview_unsupported(self):
        for ext in [".pdf", ".docx", ".py", ".zip"]:
            result = self.generator.can_preview(f"/some/file{ext}")
            self.assertFalse(result["can_preview"])
            self.assertIsNone(result["preview_type"])

    def test_generate_image_preview(self):
        test_image = Path(self.temp_dir) / "test.jpg"
        test_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        result = self.generator.generate_image_preview(str(test_image))
        self.assertEqual(result["type"], "image")
        self.assertIn("data:", result["data"])
        self.assertIn("image/jpeg", result["mime_type"])
        self.assertGreater(result["size"], 0)

    def test_generate_image_preview_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.generator.generate_image_preview("/nonexistent/image.jpg")

    def test_generate_image_preview_png(self):
        test_image = Path(self.temp_dir) / "test.png"
        test_image.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)

        result = self.generator.generate_image_preview(str(test_image))
        self.assertEqual(result["mime_type"], "image/png")

    @patch("modules.assets.preview.subprocess.run")
    def test_generate_video_thumbnail(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stderr="")

        test_video = Path(self.temp_dir) / "test.mp4"
        test_video.write_bytes(b"\x00" * 100)

        output_thumb = Path(self.temp_dir) / "thumb.jpg"
        output_thumb.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)

        mock_ffmpeg = Mock()
        mock_ffmpeg.get_info.return_value = {"installed": True}
        mock_ffmpeg.get_ffmpeg_path.return_value = "/usr/bin/ffmpeg"
        self.generator.ffmpeg = mock_ffmpeg

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"\xff\xd8\xff\x00" * 10)):
            result = self.generator.generate_video_thumbnail(str(test_video), "00:00:01", str(output_thumb))
            self.assertEqual(result["type"], "video_thumbnail")

    @patch("modules.assets.preview.subprocess.run")
    def test_generate_video_thumbnail_ffmpeg_not_available(self, mock_run):
        test_video = Path(self.temp_dir) / "test.mp4"
        test_video.write_bytes(b"\x00" * 100)

        mock_ffmpeg = Mock()
        mock_ffmpeg.get_info.return_value = {"installed": False}
        self.generator.ffmpeg = mock_ffmpeg

        with self.assertRaises(RuntimeError):
            self.generator.generate_video_thumbnail(str(test_video))

    def test_generate_video_thumbnail_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.generator.generate_video_thumbnail("/nonexistent/video.mp4")

    @patch("modules.assets.preview.subprocess.run")
    def test_generate_audio_waveform(self, mock_run):
        import json
        audio_metadata = {
            "format": {"duration": "120.5", "bit_rate": "320000"},
            "streams": [
                {"codec_type": "audio", "codec_name": "mp3", "sample_rate": "44100", "channels": 2}
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(audio_metadata), stderr="")

        test_audio = Path(self.temp_dir) / "test.mp3"
        test_audio.write_bytes(b"\x00" * 100)

        mock_ffmpeg = Mock()
        mock_ffmpeg.get_info.return_value = {"installed": True}
        mock_ffmpeg.get_ffprobe_path.return_value = "/usr/bin/ffprobe"
        self.generator.ffmpeg = mock_ffmpeg

        result = self.generator.generate_audio_waveform(str(test_audio))
        self.assertEqual(result["type"], "audio")
        self.assertAlmostEqual(result["duration"], 120.5)
        self.assertEqual(result["codec"], "mp3")
        self.assertEqual(result["channels"], 2)

    @patch("modules.assets.preview.subprocess.run")
    def test_generate_audio_waveform_ffmpeg_not_available(self, mock_run):
        test_audio = Path(self.temp_dir) / "test.mp3"
        test_audio.write_bytes(b"\x00" * 100)

        mock_ffmpeg = Mock()
        mock_ffmpeg.get_info.return_value = {"installed": False}
        self.generator.ffmpeg = mock_ffmpeg

        with self.assertRaises(RuntimeError):
            self.generator.generate_audio_waveform(str(test_audio))

    def test_generate_audio_waveform_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.generator.generate_audio_waveform("/nonexistent/audio.mp3")

    def test_get_mime_type(self):
        self.assertEqual(self.generator._get_mime_type(".jpg"), "image/jpeg")
        self.assertEqual(self.generator._get_mime_type(".png"), "image/png")
        self.assertEqual(self.generator._get_mime_type(".gif"), "image/gif")
        self.assertEqual(self.generator._get_mime_type(".webp"), "image/webp")
        self.assertEqual(self.generator._get_mime_type(".svg"), "image/svg+xml")
        self.assertEqual(self.generator._get_mime_type(".xyz"), "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
