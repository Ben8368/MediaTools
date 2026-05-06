"""测试 Media Service 模块"""
import unittest
from unittest.mock import Mock, patch

from backend.services.media import fetch_video_info


class TestMediaService(unittest.TestCase):
    @patch("services.media.VideoDownloader")
    def test_fetch_video_info_success(self, mock_downloader_class):
        """测试获取视频信息成功"""
        mock_downloader = Mock()
        mock_downloader.get_video_info.return_value = {
            "video_id": "test123",
            "title": "Test Video",
            "duration": 120,
        }
        mock_downloader_class.return_value = mock_downloader

        result = fetch_video_info(
            "https://youtube.com/watch?v=test123",
            "/tmp/output",
            "{title}",
        )

        self.assertEqual(result["video_id"], "test123")
        self.assertEqual(result["title"], "Test Video")
        self.assertEqual(result["duration"], 120)

    @patch("services.media.VideoDownloader")
    def test_fetch_video_info_invalid_url(self, mock_downloader_class):
        """测试无效 URL 的错误处理"""
        mock_downloader = Mock()
        mock_downloader.get_video_info.side_effect = RuntimeError("Invalid URL")
        mock_downloader_class.return_value = mock_downloader

        with self.assertRaises(RuntimeError):
            fetch_video_info("invalid-url", "/tmp/output", "{title}")


if __name__ == "__main__":
    unittest.main()
