"""
DEPRECATED: This module has moved to cli.main

Please run:
    python -m cli.main
"""
import warnings
warnings.warn(
    "Running 'python main.py' is deprecated. Use 'python -m cli.main' instead.",
    DeprecationWarning,
    stacklevel=2,
)
from cli.main import main

if __name__ == "__main__":
    main()
