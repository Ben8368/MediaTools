"""Stable adapter exports for external tools and bundled integrations."""

from .adobe_runtime import AdobeAutomationAdapter
from .auditor_runtime import AuditorRuntimeAdapter
from .external_tools import FFmpegAdapter, UmcliAdapter, YtdlpAdapter
from .photoshop_runtime import PhotoshopAutomationAdapter
from .wechat_moments_runtime import WechatMomentsRuntimeAdapter

__all__ = [
    "AdobeAutomationAdapter",
    "AuditorRuntimeAdapter",
    "FFmpegAdapter",
    "PhotoshopAutomationAdapter",
    "UmcliAdapter",
    "WechatMomentsRuntimeAdapter",
    "YtdlpAdapter",
]
