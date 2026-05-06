"""
DEPRECATED: This module has moved to backend.config

Please update your imports:
    from backend.config import *
"""
import warnings
warnings.warn(
    "Importing from 'config' is deprecated. Use 'backend.config' instead.",
    DeprecationWarning,
    stacklevel=2,
)
from backend.config import *  # noqa: F401, F403
