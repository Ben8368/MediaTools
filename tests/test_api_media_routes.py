import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services.api_media_routes import create_router
from backend.services.task_center import TaskCenter


class FakeJobRegistry:
    def __init__(self):
        self.finished = {}
        self.updates = []
        self.cancelled = set()

    def register(self, job_id, job_type, name):
        return job_id

    def update(self, job_id, stage, percent, status="running"):
        self.updates.append((job_id, stage, percent, status))

    def finish(self, job_id, success=True):
        self.finished[job_id] = success

    def is_cancelled(self, job_id):
        return job_id in self.cancelled


def run_immediately(target):
    target()


class TestApiMediaRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.downloads = self.root / "downloads"
        self.downloads.mkdir()
        self.task_center = TaskCenter(str(self.root / "tasks.db"))
        self.job_registry = FakeJobRegistry()
        self.stream_snapshots = []
        self.fetch_kwargs = None
        self.transcode_result = {"summary_rows": [["status", "success"]], "output_path": str(self.root / "out.mp4")}
        self.decrypt_result = {"summary_rows": [["status", "success"]], "result_text": "ok"}
        app = FastAPI()
        app.include_router(
            create_router(
                self.job_registry,
                lambda: {"project_root": str(self.root), "downloads_dir": str(self.downloads)},
                self.resolve_allowed_path,
                self.run_fetch_batch_stream,
                self.run_transcode_job,
                self.run_decrypt_job,
                self.result_success,
            )
        )
        self.client = TestClient(app)
        self.patch_get = patch("services.task_center.get_task_center", return_value=self.task_center)
        self.patch_get.start()
        self.patch_thread = patch("services.api_media_routes._start_background", run_immediately)
        self.patch_thread.start()

    def tearDown(self):
        self.patch_thread.stop()
        self.patch_get.stop()
        self.temp_dir.cleanup()

    def resolve_allowed_path(self, path, workspace):
        target = Path(path)
        if not target.is_absolute():
            target = Path(workspace["project_root"]) / target
        return target

    def run_fetch_batch_stream(self, **kwargs):
        self.fetch_kwargs = kwargs
        if isinstance(self.stream_snapshots, BaseException):
            raise self.stream_snapshots
        return iter(self.stream_snapshots)

    def run_transcode_job(self, *args, **kwargs):
        if isinstance(self.transcode_result, BaseException):
            raise self.transcode_result
        progress_callback = kwargs.get("progress_callback")
        if progress_callback:
            progress_callback(42.0)
        return self.transcode_result

    def run_decrypt_job(self, *args, **kwargs):
        if isinstance(self.decrypt_result, BaseException):
            raise self.decrypt_result
        return self.decrypt_result

    def result_success(self, result):
        return bool(result.get("output_path") or result.get("result_text"))

    def test_fetcher_download_completes_task(self):
        output = self.downloads / "clip.mp4"
        self.stream_snapshots = [
            {
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": str(output), "title": "Clip"}}],
            }
        ]

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["status"], "pending")
        tasks = []
        for _ in range(20):
            tasks = self.task_center.list_tasks()
            if tasks and tasks[0]["status"] == "completed":
                break
            time.sleep(0.02)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["status"], "completed")
        self.assertEqual(tasks[0]["progress"], 100.0)
        self.assertEqual(self.fetch_kwargs["subtitle_formats"], ["srt"])
        self.assertEqual(self.fetch_kwargs["video_codec_preference"], "best")
        self.assertTrue(self.fetch_kwargs["download_video"])

    def test_fetcher_download_uses_selected_quality_for_best_or_h264(self):
        output = self.downloads / "clip.mp4"
        self.stream_snapshots = [
            {
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": str(output)}}],
            }
        ]

        response = self.client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "quality": "best", "subtitles": True, "analyze": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fetch_kwargs["video_codec_preference"], "best")
        self.assertEqual(self.fetch_kwargs["subtitle_mode"], "original_only")
        self.assertTrue(self.fetch_kwargs["analyze"])

    def test_fetcher_download_normalizes_h264_quality_value(self):
        output = self.downloads / "clip.mp4"
        self.stream_snapshots = [
            {
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": str(output)}}],
            }
        ]

        response = self.client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "quality": " H264 "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fetch_kwargs["video_codec_preference"], "h264")
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["params"]["quality"], "h264")

    def test_fetcher_download_rejects_non_directory_target(self):
        file_target = self.root / "not-dir.txt"
        file_target.write_text("x", encoding="utf-8")

        response = self.client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "output_dir": str(file_target)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not-dir.txt", response.json()["error"])

    def test_fetcher_download_short_video_mode_disables_subtitles(self):
        output = self.downloads / "clip.mp4"
        self.stream_snapshots = [
            {
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": str(output), "title": "Clip"}}],
            }
        ]

        response = self.client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "platform": "short_video", "subtitles": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fetch_kwargs["subtitle_mode"], "none")
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["params"]["platform"], "short_video")
        self.assertFalse(task["params"]["subtitles"])

    def test_fetcher_download_marks_failed_when_stream_raises(self):
        self.stream_snapshots = RuntimeError("download exploded")

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "download exploded")
        self.assertIn(task["id"], self.job_registry.finished)
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_fetcher_download_marks_failed_without_result(self):
        self.stream_snapshots = []

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "download failed: no result")

    def test_fetcher_download_marks_cancelled_from_snapshot(self):
        self.stream_snapshots = [{"progress_percent": 30, "progress_text": "cancelled", "current_stage": "cancelled"}]

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "cancelled")
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_fetcher_download_marks_failed_when_info_has_no_artifacts(self):
        self.stream_snapshots = [{"items": [{"info": {"title": "no files"}}], "progress_percent": 88}]

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["progress"], 88)
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_fetcher_download_marks_failed_without_info(self):
        self.stream_snapshots = [{"items": [{"not_info": {}}]}]

        response = self.client.post("/api/fetcher/download", json={"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "download failed")

    def test_encoder_transcode_completes_task_and_updates_progress(self):
        response = self.client.post("/api/encoder/transcode", json={"input_path": str(self.root / "in.mp4")})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["output_path"], self.transcode_result["output_path"])
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["progress"], 100.0)
        self.assertTrue(any(update[1] == "transcoding" for update in self.job_registry.updates))

    def test_encoder_transcode_marks_failed_result(self):
        self.transcode_result = {"ok": False, "error": "bad codec"}

        response = self.client.post("/api/encoder/transcode", json={"input_path": str(self.root / "in.mp4")})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["progress"], 42.0)
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_encoder_transcode_exception_marks_failed_and_propagates(self):
        self.transcode_result = RuntimeError("ffmpeg failed")

        with self.assertRaises(RuntimeError):
            self.client.post("/api/encoder/transcode", json={"input_path": str(self.root / "in.mp4")})

        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "ffmpeg failed")
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_encoder_transcode_marks_cancelled_when_job_cancelled(self):
        original_register = self.job_registry.register

        def register_and_cancel(job_id, job_type, name):
            result = original_register(job_id, job_type, name)
            self.job_registry.cancelled.add(job_id)
            return result

        self.job_registry.register = register_and_cancel

        response = self.client.post("/api/encoder/transcode", json={"input_path": str(self.root / "in.mp4")})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "cancelled")
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_decryptor_decrypt_completes_task(self):
        response = self.client.post("/api/decryptor/decrypt", json={"input_path": str(self.root / "song.ncm")})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result_text"], "ok")
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["progress"], 100.0)

    def test_decryptor_decrypt_marks_failed_result(self):
        self.decrypt_result = {"ok": False, "error": "decrypt failed"}

        response = self.client.post("/api/decryptor/decrypt", json={"input_path": str(self.root / "song.ncm")})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["progress"], 0.0)
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_decryptor_decrypt_exception_marks_failed_and_propagates(self):
        self.decrypt_result = RuntimeError("um failed")

        with self.assertRaises(RuntimeError):
            self.client.post("/api/decryptor/decrypt", json={"input_path": str(self.root / "song.ncm")})

        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["error"], "um failed")
        self.assertFalse(self.job_registry.finished[task["id"]])

    def test_decryptor_decrypt_marks_cancelled_when_job_cancelled(self):
        original_register = self.job_registry.register

        def register_and_cancel(job_id, job_type, name):
            result = original_register(job_id, job_type, name)
            self.job_registry.cancelled.add(job_id)
            return result

        self.job_registry.register = register_and_cancel

        response = self.client.post("/api/decryptor/decrypt", json={"input_path": str(self.root / "song.ncm")})

        self.assertEqual(response.status_code, 200)
        task = self.task_center.list_tasks()[0]
        self.assertEqual(task["status"], "cancelled")
        self.assertFalse(self.job_registry.finished[task["id"]])


if __name__ == "__main__":
    unittest.main()
