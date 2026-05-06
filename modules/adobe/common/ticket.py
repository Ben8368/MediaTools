"""通用工单基类"""

from abc import ABC, abstractmethod
from typing import Any


class AdobeTicket(ABC):
    """Adobe 工单抽象基类"""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AdobeTicket':
        """从字典反序列化"""
        pass

    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        """验证工单有效性，返回 (是否有效, 错误信息)"""
        pass
