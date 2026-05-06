"""CapCut editing integration.

This package talks to a separately running capcut-mate HTTP service. Direct
imports from vendor/capcut-mate are intentionally not exposed because that path
was never fully implemented.
"""

from .adapter import CapcutAdapter

__all__ = ["CapcutAdapter"]
