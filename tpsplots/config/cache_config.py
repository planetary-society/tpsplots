"""
Cache configuration for tpsplots data retrieval.

This module sets up cachier to cache external data fetches in a consistent location.
"""

from pathlib import Path

from cachier import set_default_params

# Set up cache directory
CACHE_DIR = Path.home() / ".cache" / "tps-charts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure cachier defaults
set_default_params(
    cache_dir=str(CACHE_DIR),
    backend="pickle",  # Use pickle backend for simplicity
)

# Export cache directory for other modules
__all__ = ["CACHE_DIR"]
