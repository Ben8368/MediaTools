"""
modules.decryptor - 音乐/视频解密模块

通过 subprocess 调用 vendor/unlock-music/ 编译产物（bin/um-cli.exe）
支持 QQ音乐、网易云、酷狗、酷我、虾米、喜马拉雅等平台的加密格式。
"""

from .wrapper import DecryptorWrapper

__all__ = ["DecryptorWrapper"]
