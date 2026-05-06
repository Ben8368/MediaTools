"""
modules.encoder - 媒体编码转换模块

基于 FFmpeg 提供视频/音频格式转换、压缩、重编码等功能。
"""

from .transcoder import Transcoder

__all__ = ["Transcoder"]
