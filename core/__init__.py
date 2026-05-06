"""
core 公共基础层

提供所有模块共享的基础设施：
- ffmpeg: FFmpeg/FFprobe 路径管理和调用封装
- logger: 统一日志输出
- utils: 通用工具函数
"""

from .ffmpeg import FFmpegManager
from .logger import setup_logger

__all__ = [
    "FFmpegManager",
    "setup_logger",
]
