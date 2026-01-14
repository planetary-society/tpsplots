"""
Deprecated cache configuration.

Caching is disabled in tpsplots; this module is kept for compatibility.
"""

from pathlib import Path

# Export a default cache directory path (unused by the package).
CACHE_DIR = Path.home() / ".cache" / "tps-charts"

__all__ = ["CACHE_DIR"]
