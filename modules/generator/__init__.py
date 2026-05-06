"""素材生成模块

支持多种素材创建功能：
- 视频截图提取
- 朋友圈图片生成
"""

from .screenshot import ScreenshotGenerator
from .wechat_moments import WechatMomentsGenerator

__all__ = ["ScreenshotGenerator", "WechatMomentsGenerator"]
