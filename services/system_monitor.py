"""Runtime metrics for the desktop status panel."""

from __future__ import annotations

import ipaddress
import platform
import socket
import time
from dataclasses import dataclass, field
from typing import Any

import psutil

from adapters import FFmpegAdapter, PhotoshopAutomationAdapter, UmcliAdapter, YtdlpAdapter
from services.auditor import get_auditor_status
from services.task_center import TaskStatus, TaskType, get_task_center
from services.wechat_moments import get_wechat_moments_status
from services.workspace import get_current_workspace


def _bytes_per_sec(value: float) -> dict[str, Any]:
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    current = float(max(value, 0.0))
    for unit in units:
        if current < 1024 or unit == units[-1]:
            return {"value": round(current, 1), "text": f"{current:.1f} {unit}" if unit != "B/s" else f"{current:.0f} {unit}"}
        current /= 1024
    return {"value": current, "text": f"{current:.1f} GB/s"}


def _status(online: bool, detail: str = "") -> dict[str, Any]:
    return {"online": bool(online), "status": "online" if online else "offline", "detail": detail}


INTERNAL_INTERFACE_HINTS = (
    "loopback",
    "localhost",
    "virtual",
    "vethernet",
    "hyper-v",
    "vmware",
    "virtualbox",
    "docker",
    "wsl",
    "tap",
    "tunnel",
    "teredo",
    "isatap",
    "npcap",
    "bluetooth",
    "zerotier",
    "tailscale",
    "hamachi",
)


def _has_routable_adapter_address(addresses: list[Any]) -> bool:
    for addr in addresses:
        if addr.family != socket.AF_INET:
            continue
        try:
            ip = ipaddress.ip_address(addr.address)
        except ValueError:
            continue
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
            continue
        return True
    return False


def _is_external_interface(name: str, addresses: list[Any], stats: Any) -> bool:
    lowered = name.lower()
    if any(hint in lowered for hint in INTERNAL_INTERFACE_HINTS):
        return False
    if stats is not None and not getattr(stats, "isup", False):
        return False
    return _has_routable_adapter_address(addresses)


def _external_network_totals() -> tuple[int, int, list[str]]:
    pernic = psutil.net_io_counters(pernic=True)
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    interface_names = [
        name
        for name in pernic
        if _is_external_interface(name, addresses.get(name, []), stats.get(name))
    ]
    if not interface_names:
        counters = psutil.net_io_counters()
        return int(counters.bytes_sent), int(counters.bytes_recv), ["all"]

    sent = sum(int(pernic[name].bytes_sent) for name in interface_names)
    recv = sum(int(pernic[name].bytes_recv) for name in interface_names)
    return sent, recv, interface_names


TASK_TYPE_LABELS = {
    "fetch": "媒体下载",
    "download": "媒体下载",
    "transcode": "视频转码",
    "slice": "视频切片",
    "decrypt": "音频解密",
    "photoshop": "PS 工单",
    "audit": "素材审核",
    "wechat": "朋友圈生成",
}

TASK_STATUS_LABELS = {
    "pending": "等待中",
    "running": "执行中",
    "paused": "已暂停",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已停止",
}


def _task_type_label(task_type: str) -> str:
    return TASK_TYPE_LABELS.get(task_type, task_type or "任务")


def _task_status_label(status: str) -> str:
    return TASK_STATUS_LABELS.get(status, status or "未知")


def _task_source(task: dict[str, Any]) -> str:
    params = task.get("params") if isinstance(task.get("params"), dict) else {}
    for key in ("url", "input_path", "output_path", "file_path"):
        value = params.get(key)
        if value:
            return str(value)
    name = str(task.get("name") or "")
    task_type = str(task.get("type") or "")
    return "" if name == _task_type_label(task_type) else name


@dataclass
class RuntimeMetricSampler:
    started_at: float = field(default_factory=time.time)
    _last_net: tuple[float, int, int] | None = None
    _service_cache: tuple[float, list[dict[str, Any]]] | None = None
    _gpu_supported: bool | None = None
    _gpu_error: str = ""

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        sent_rate, recv_rate = self._network_rates(now)
        gpu_encode = self._gpu_video_encode_percent()

        return {
            "ok": True,
            "sampled_at": now,
            "runtime": {
                "started_at": self.started_at,
                "uptime_seconds": max(0, int(now - self.started_at)),
            },
            "system": {
                "cpu_percent": round(float(cpu_percent), 1),
                "memory_percent": round(float(memory.percent), 1),
                "memory_used_bytes": int(memory.used),
                "memory_total_bytes": int(memory.total),
                "gpu_video_encode_percent": round(gpu_encode["percent"], 1),
                "gpu_video_encode_available": gpu_encode["available"],
                "gpu_video_encode_detail": gpu_encode.get("detail", ""),
            },
            "network": {
                "upload_bytes_per_sec": sent_rate,
                "download_bytes_per_sec": recv_rate,
                "upload": _bytes_per_sec(sent_rate),
                "download": _bytes_per_sec(recv_rate),
            },
            "services": self._service_statuses(),
            "tasks": self._task_progress(),
            "task_summary": self._task_summary(),
        }

    def _network_rates(self, now: float) -> tuple[float, float]:
        sent, recv, _interfaces = _external_network_totals()
        current = (now, sent, recv)
        if self._last_net is None:
            self._last_net = current
            return 0.0, 0.0

        last_time, last_sent, last_recv = self._last_net
        self._last_net = current
        elapsed = max(now - last_time, 0.001)
        return max(0.0, (current[1] - last_sent) / elapsed), max(0.0, (current[2] - last_recv) / elapsed)

    def _gpu_video_encode_percent(self) -> dict[str, Any]:
        if platform.system().lower() != "windows":
            return {"available": False, "percent": 0.0, "detail": "GPU Video Encode counters are only available on Windows"}
        try:
            import win32pdh  # type: ignore

            counters, instances = win32pdh.EnumObjectItems(None, None, "GPU Engine", win32pdh.PERF_DETAIL_WIZARD)
            if "Utilization Percentage" not in counters:
                return {"available": False, "percent": 0.0, "detail": "GPU utilization counter not found"}

            encode_instances = [item for item in instances if "engtype_VideoEncode" in item]
            if not encode_instances:
                return {"available": True, "percent": 0.0, "detail": "No Video Encode engine instance is active"}

            query = win32pdh.OpenQuery()
            handles = []
            try:
                for instance in encode_instances:
                    path = win32pdh.MakeCounterPath((None, "GPU Engine", instance, None, 0, "Utilization Percentage"))
                    handles.append(win32pdh.AddCounter(query, path))
                win32pdh.CollectQueryData(query)
                time.sleep(0.05)
                win32pdh.CollectQueryData(query)
                total = 0.0
                sampled = 0
                for handle in handles:
                    try:
                        _kind, value = win32pdh.GetFormattedCounterValue(handle, win32pdh.PDH_FMT_DOUBLE)
                    except Exception:
                        continue
                    total += float(value)
                    sampled += 1
                if sampled == 0:
                    return {"available": True, "percent": 0.0, "detail": "Video Encode counters temporarily unavailable"}
                return {
                    "available": True,
                    "percent": min(total, 100.0),
                    "detail": f"{sampled}/{len(encode_instances)} Video Encode engine(s)",
                }
            finally:
                win32pdh.CloseQuery(query)
        except Exception as exc:
            self._gpu_error = str(exc)
            return {"available": False, "percent": 0.0, "detail": "GPU Video Encode unavailable"}

    def _service_statuses(self) -> list[dict[str, Any]]:
        now = time.time()
        if self._service_cache and now - self._service_cache[0] < 10:
            return self._service_cache[1]

        workspace = get_current_workspace()
        ffmpeg_info = FFmpegAdapter().get_info()
        ytdlp_status = YtdlpAdapter().get_status()
        photoshop_status = PhotoshopAutomationAdapter().get_status()
        services = [
            {"id": "fetcher", "name": "媒体获取", **_status(ytdlp_status.get("installed", False), ytdlp_status.get("version", ""))},
            {"id": "encoder", "name": "转码编码", **_status(ffmpeg_info.get("installed", False), ffmpeg_info.get("version", ""))},
            {"id": "decryptor", "name": "音频解密", **_status(UmcliAdapter().is_available(), "um-cli")},
            {"id": "photoshop", "name": "PS 工单", **_status(photoshop_status.get("available", False), photoshop_status.get("message", ""))},
            {"id": "auditor", "name": "素材审核", **_status(get_auditor_status(workspace).get("available", False), "")},
            {"id": "wechat", "name": "朋友圈生成", **_status(get_wechat_moments_status(workspace).get("available", False), "")},
        ]
        self._service_cache = (now, services)
        return services

    def _task_progress(self) -> list[dict[str, Any]]:
        task_center = get_task_center()
        tasks = task_center.get_active_tasks()
        return [
            {
                "id": task.get("id", ""),
                "name": _task_type_label(str(task.get("type") or "")),
                "source": _task_source(task),
                "type": task.get("type", ""),
                "status": task.get("status", ""),
                "status_label": _task_status_label(str(task.get("status") or "")),
                "stage": task.get("stage", ""),
                "progress": max(0.0, min(float(task.get("progress") or 0.0), 100.0)),
                "updated_at": task.get("updated_at"),
                "can_pause": False,
                "can_resume": False,
                "can_cancel": task.get("status") in {"pending", "running", "paused"},
            }
            for task in tasks
        ]

    def _task_summary(self) -> dict[str, Any]:
        task_center = get_task_center()
        active_tasks = task_center.get_active_tasks()
        active_downloads = [task for task in active_tasks if str(task.get("type") or "") == TaskType.DOWNLOAD.value]
        download_records = task_center.list_tasks(task_type=TaskType.DOWNLOAD, limit=1000)
        terminal_statuses = {
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        }
        return {
            "active_downloads": len(active_downloads),
            "total_download_records": len(download_records),
            "terminal_download_records": sum(1 for task in download_records if task.get("status") in terminal_statuses),
        }


_sampler = RuntimeMetricSampler()


def get_runtime_metrics() -> dict[str, Any]:
    return _sampler.snapshot()
