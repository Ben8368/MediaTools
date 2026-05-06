import socket
import sys
from unittest.mock import Mock, patch

import services.system_monitor as monitor
from services.system_monitor import RuntimeMetricSampler, _bytes_per_sec, _status


def test_bytes_per_sec_formats_units():
    assert _bytes_per_sec(0)["text"] == "0 B/s"
    assert _bytes_per_sec(1536)["text"] == "1.5 KB/s"
    assert _bytes_per_sec(2 * 1024 * 1024)["text"] == "2.0 MB/s"
    assert _bytes_per_sec(-10)["text"] == "0 B/s"
    assert _bytes_per_sec(5 * 1024 * 1024 * 1024)["text"] == "5.0 GB/s"


def test_status_formats_online_and_offline():
    assert _status(True, "ready") == {"online": True, "status": "online", "detail": "ready"}
    assert _status(False) == {"online": False, "status": "offline", "detail": ""}


def test_has_routable_adapter_address_rejects_non_external_addresses():
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET6, address="::1")]) is False
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET, address="not-an-ip")]) is False
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET, address="127.0.0.1")]) is False
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET, address="169.254.1.10")]) is False
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET, address="0.0.0.0")]) is False
    assert monitor._has_routable_adapter_address([Mock(family=socket.AF_INET, address="10.0.0.20")]) is True


def test_is_external_interface_rejects_internal_and_down_interfaces():
    routable = [Mock(family=socket.AF_INET, address="10.0.0.20")]

    assert monitor._is_external_interface("vEthernet (WSL)", routable, Mock(isup=True)) is False
    assert monitor._is_external_interface("Ethernet", routable, Mock(isup=False)) is False
    assert monitor._is_external_interface("Ethernet", routable, None) is True


def test_network_rates_use_delta():
    sampler = RuntimeMetricSampler()

    with patch.object(monitor, "_external_network_totals", side_effect=[(1000, 2000, ["Wi-Fi"]), (2500, 5000, ["Wi-Fi"])]):
        assert sampler._network_rates(10.0) == (0.0, 0.0)
        upload, download = sampler._network_rates(12.0)

    assert upload == 750.0
    assert download == 1500.0


def test_external_network_totals_filters_internal_interfaces():
    pernic = {
        "Wi-Fi": Mock(bytes_sent=3000, bytes_recv=7000),
        "vEthernet (WSL)": Mock(bytes_sent=9000, bytes_recv=9000),
        "Loopback Pseudo-Interface 1": Mock(bytes_sent=5000, bytes_recv=5000),
    }
    addresses = {
        "Wi-Fi": [Mock(family=socket.AF_INET, address="192.168.1.20")],
        "vEthernet (WSL)": [Mock(family=socket.AF_INET, address="172.20.1.1")],
        "Loopback Pseudo-Interface 1": [Mock(family=socket.AF_INET, address="127.0.0.1")],
    }
    stats = {
        "Wi-Fi": Mock(isup=True),
        "vEthernet (WSL)": Mock(isup=True),
        "Loopback Pseudo-Interface 1": Mock(isup=True),
    }

    with patch.object(monitor.psutil, "net_io_counters", return_value=pernic), patch.object(
        monitor.psutil,
        "net_if_addrs",
        return_value=addresses,
    ), patch.object(monitor.psutil, "net_if_stats", return_value=stats):
        sent, recv, interfaces = monitor._external_network_totals()

    assert sent == 3000
    assert recv == 7000
    assert interfaces == ["Wi-Fi"]


def test_external_network_totals_falls_back_to_all_counters():
    pernic = {
        "Loopback Pseudo-Interface 1": Mock(bytes_sent=5000, bytes_recv=5000),
    }
    total = Mock(bytes_sent=12000, bytes_recv=34000)

    with patch.object(monitor.psutil, "net_io_counters", side_effect=[pernic, total]), patch.object(
        monitor.psutil,
        "net_if_addrs",
        return_value={"Loopback Pseudo-Interface 1": [Mock(family=socket.AF_INET, address="127.0.0.1")]},
    ), patch.object(monitor.psutil, "net_if_stats", return_value={"Loopback Pseudo-Interface 1": Mock(isup=True)}):
        sent, recv, interfaces = monitor._external_network_totals()

    assert sent == 12000
    assert recv == 34000
    assert interfaces == ["all"]


def test_snapshot_contains_resources_services_and_tasks():
    sampler = RuntimeMetricSampler()
    sampler._network_rates = Mock(return_value=(100.0, 200.0))
    sampler._gpu_video_encode_percent = Mock(return_value={"available": True, "percent": 12.5, "detail": "ok"})
    sampler._service_statuses = Mock(return_value=[{"id": "encoder", "name": "转码编码", "online": True, "status": "online"}])
    sampler._task_progress = Mock(return_value=[{"id": "task-1", "name": "demo", "progress": 25.0, "status": "running"}])

    with patch.object(monitor.psutil, "cpu_percent", return_value=33.3), patch.object(
        monitor.psutil,
        "virtual_memory",
        return_value=Mock(percent=44.4, used=10, total=20),
    ):
        result = sampler.snapshot()

    assert result["ok"] is True
    assert result["system"]["cpu_percent"] == 33.3
    assert result["system"]["memory_percent"] == 44.4
    assert result["system"]["gpu_video_encode_percent"] == 12.5
    assert result["network"]["upload_bytes_per_sec"] == 100.0
    assert result["services"][0]["id"] == "encoder"
    assert result["tasks"][0]["id"] == "task-1"


def test_gpu_video_encode_percent_hides_transient_counter_errors():
    sampler = RuntimeMetricSampler()
    fake_win32pdh = Mock()
    fake_win32pdh.PERF_DETAIL_WIZARD = 0
    fake_win32pdh.PDH_FMT_DOUBLE = 0
    fake_win32pdh.EnumObjectItems.return_value = (["Utilization Percentage"], ["pid_1_engtype_VideoEncode"])
    fake_win32pdh.OpenQuery.return_value = "query"
    fake_win32pdh.MakeCounterPath.return_value = "counter-path"
    fake_win32pdh.AddCounter.return_value = "counter"
    fake_win32pdh.GetFormattedCounterValue.side_effect = RuntimeError("GetFormattedCounterValue failed")

    with patch.object(monitor.platform, "system", return_value="Windows"), patch.dict(sys.modules, {"win32pdh": fake_win32pdh}):
        result = sampler._gpu_video_encode_percent()

    assert result == {
        "available": True,
        "percent": 0.0,
        "detail": "Video Encode counters temporarily unavailable",
    }


def test_gpu_video_encode_percent_reports_unsupported_platform():
    sampler = RuntimeMetricSampler()

    with patch.object(monitor.platform, "system", return_value="Linux"):
        result = sampler._gpu_video_encode_percent()

    assert result == {
        "available": False,
        "percent": 0.0,
        "detail": "GPU Video Encode counters are only available on Windows",
    }


def test_gpu_video_encode_percent_reports_missing_counter():
    sampler = RuntimeMetricSampler()
    fake_win32pdh = Mock(PERF_DETAIL_WIZARD=0)
    fake_win32pdh.EnumObjectItems.return_value = (["Other Counter"], [])

    with patch.object(monitor.platform, "system", return_value="Windows"), patch.dict(sys.modules, {"win32pdh": fake_win32pdh}):
        result = sampler._gpu_video_encode_percent()

    assert result == {"available": False, "percent": 0.0, "detail": "GPU utilization counter not found"}


def test_gpu_video_encode_percent_reports_no_active_encode_engine():
    sampler = RuntimeMetricSampler()
    fake_win32pdh = Mock(PERF_DETAIL_WIZARD=0)
    fake_win32pdh.EnumObjectItems.return_value = (["Utilization Percentage"], ["pid_1_engtype_3D"])

    with patch.object(monitor.platform, "system", return_value="Windows"), patch.dict(sys.modules, {"win32pdh": fake_win32pdh}):
        result = sampler._gpu_video_encode_percent()

    assert result == {"available": True, "percent": 0.0, "detail": "No Video Encode engine instance is active"}


def test_gpu_video_encode_percent_samples_encode_engines_and_closes_query():
    sampler = RuntimeMetricSampler()
    fake_win32pdh = Mock()
    fake_win32pdh.PERF_DETAIL_WIZARD = 0
    fake_win32pdh.PDH_FMT_DOUBLE = 0
    fake_win32pdh.EnumObjectItems.return_value = (
        ["Utilization Percentage"],
        ["pid_1_engtype_VideoEncode", "pid_2_engtype_VideoEncode"],
    )
    fake_win32pdh.OpenQuery.return_value = "query"
    fake_win32pdh.MakeCounterPath.side_effect = ["path-1", "path-2"]
    fake_win32pdh.AddCounter.side_effect = ["handle-1", "handle-2"]
    fake_win32pdh.GetFormattedCounterValue.side_effect = [(0, 65.0), (0, 50.0)]

    with patch.object(monitor.platform, "system", return_value="Windows"), patch.dict(
        sys.modules,
        {"win32pdh": fake_win32pdh},
    ), patch.object(monitor.time, "sleep"):
        result = sampler._gpu_video_encode_percent()

    assert result == {"available": True, "percent": 100.0, "detail": "2/2 Video Encode engine(s)"}
    fake_win32pdh.CloseQuery.assert_called_once_with("query")


def test_gpu_video_encode_percent_caches_import_error_detail():
    sampler = RuntimeMetricSampler()

    with patch.object(monitor.platform, "system", return_value="Windows"), patch.dict(sys.modules, {"win32pdh": None}):
        result = sampler._gpu_video_encode_percent()

    assert result == {"available": False, "percent": 0.0, "detail": "GPU Video Encode unavailable"}
    assert sampler._gpu_error


def test_service_statuses_uses_cache_for_ten_seconds():
    sampler = RuntimeMetricSampler()
    cached = [{"id": "encoder", "name": "cached"}]
    sampler._service_cache = (100.0, cached)

    with patch.object(monitor.time, "time", return_value=105.0), patch.object(monitor, "get_current_workspace") as workspace:
        assert sampler._service_statuses() is cached

    workspace.assert_not_called()


def test_service_statuses_builds_and_caches_adapter_statuses():
    sampler = RuntimeMetricSampler()
    ffmpeg_adapter = Mock()
    ffmpeg_adapter.get_info.return_value = {"installed": True, "version": "ffmpeg 7"}
    ytdlp_adapter = Mock()
    ytdlp_adapter.get_status.return_value = {"installed": False, "version": ""}
    umcli_adapter = Mock()
    umcli_adapter.is_available.return_value = True
    photoshop_adapter = Mock()
    photoshop_adapter.get_status.return_value = {"available": False, "message": "missing"}

    with patch.object(monitor.time, "time", return_value=200.0), patch.object(
        monitor,
        "get_current_workspace",
        return_value=Mock(name="workspace"),
    ), patch.object(monitor, "FFmpegAdapter", return_value=ffmpeg_adapter), patch.object(
        monitor,
        "YtdlpAdapter",
        return_value=ytdlp_adapter,
    ), patch.object(monitor, "UmcliAdapter", return_value=umcli_adapter), patch.object(
        monitor,
        "PhotoshopAutomationAdapter",
        return_value=photoshop_adapter,
    ), patch.object(monitor, "get_auditor_status", return_value={"available": True}), patch.object(
        monitor,
        "get_wechat_moments_status",
        return_value={"available": False},
    ):
        services = sampler._service_statuses()

    by_id = {service["id"]: service for service in services}
    assert by_id["encoder"]["online"] is True
    assert by_id["fetcher"]["online"] is False
    assert by_id["decryptor"]["online"] is True
    assert by_id["photoshop"]["detail"] == "missing"
    assert by_id["auditor"]["online"] is True
    assert by_id["wechat"]["online"] is False
    assert sampler._service_cache == (200.0, services)


def test_task_progress_uses_active_queue_and_readable_labels():
    sampler = RuntimeMetricSampler()
    task_center = Mock()
    task_center.get_active_tasks.return_value = [
        {
            "id": "task-1",
            "type": "transcode",
            "name": "in.mp4",
            "status": "running",
            "stage": "转码中",
            "progress": 42.6,
            "params": {"input_path": "D:/media/in.mp4"},
        }
    ]

    with patch.object(monitor, "get_task_center", return_value=task_center):
        tasks = sampler._task_progress()

    task_center.list_tasks.assert_not_called()
    assert tasks == [
        {
            "id": "task-1",
            "name": "视频转码",
            "source": "D:/media/in.mp4",
            "type": "transcode",
            "status": "running",
            "status_label": "执行中",
            "stage": "转码中",
            "progress": 42.6,
            "updated_at": None,
            "can_pause": False,
            "can_resume": False,
            "can_cancel": True,
        }
    ]


def test_task_progress_clamps_values_and_uses_name_fallbacks():
    sampler = RuntimeMetricSampler()
    task_center = Mock()
    task_center.get_active_tasks.return_value = [
        {"id": "too-high", "type": "unknown", "name": "custom task", "status": "completed", "progress": 150},
        {"id": "too-low", "type": "download", "name": monitor._task_type_label("download"), "status": "paused", "progress": -5},
    ]

    with patch.object(monitor, "get_task_center", return_value=task_center):
        tasks = sampler._task_progress()

    assert tasks[0]["name"] == "unknown"
    assert tasks[0]["source"] == "custom task"
    assert tasks[0]["status_label"] == monitor._task_status_label("completed")
    assert tasks[0]["progress"] == 100.0
    assert tasks[0]["can_cancel"] is False
    assert tasks[1]["source"] == ""
    assert tasks[1]["progress"] == 0.0
    assert tasks[1]["can_cancel"] is True


def test_task_summary_counts_active_and_terminal_downloads():
    sampler = RuntimeMetricSampler()
    task_center = Mock()
    task_center.get_active_tasks.return_value = [
        {"type": "download", "status": "running"},
        {"type": "transcode", "status": "running"},
    ]
    task_center.list_tasks.return_value = [
        {"type": "download", "status": "completed"},
        {"type": "download", "status": "failed"},
        {"type": "download", "status": "cancelled"},
        {"type": "download", "status": "running"},
    ]

    with patch.object(monitor, "get_task_center", return_value=task_center):
        summary = sampler._task_summary()

    task_center.list_tasks.assert_called_once_with(task_type=monitor.TaskType.DOWNLOAD, limit=1000)
    assert summary == {
        "active_downloads": 1,
        "total_download_records": 4,
        "terminal_download_records": 3,
    }


def test_get_runtime_metrics_delegates_to_singleton_sampler():
    with patch.object(monitor._sampler, "snapshot", return_value={"ok": True}) as snapshot:
        assert monitor.get_runtime_metrics() == {"ok": True}

    snapshot.assert_called_once_with()
