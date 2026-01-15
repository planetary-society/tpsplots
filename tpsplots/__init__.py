"""tpsplots - Planetary Society chart generation from YAML configurations.

A library to create custom Planetary Society-branded charts from YAML
configuration files, with support for multiple chart types, data sources,
and output formats.

Basic usage:
    >>> import tpsplots
    >>> result = tpsplots.generate("chart_config.yaml")

CLI usage:
    $ tpsplots chart_config.yaml
    $ tpsplots yaml/  # Process all YAML files in directory
"""

import os
import sys
import warnings
from pathlib import Path


# Auto-detect headless environment and switch to Agg backend before importing pyplot
# This prevents "couldn't connect to display" errors in CI/CD and server environments
def _is_headless() -> bool:
    """Detect if running in a headless environment without a display."""
    # Check for explicit environment variable override
    if os.environ.get("TPSPLOTS_HEADLESS", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("TPSPLOTS_HEADLESS", "").lower() in ("0", "false", "no"):
        return False

    # On Linux/Unix, check for DISPLAY environment variable
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return True

    # Check for common CI/CD environment variables
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI"]
    return bool(any(os.environ.get(var) for var in ci_vars))


def _configure_matplotlib():
    import matplotlib

    if _is_headless():
        matplotlib.use("Agg")

    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    import matplotlib.style.core  # For reload_library

    return fm, plt


fm, plt = _configure_matplotlib()

# Version
__version__ = "1.0.0"

# The root directory of the 'tpsplots' package
PACKAGE_ROOT = Path(__file__).parent

# Style configuration
STYLE_DIR = (PACKAGE_ROOT / "views" / "style").resolve()
TPS_STYLE_FILE = (STYLE_DIR / "tps_base.mplstyle").resolve()

# Asset directories within the package
ASSETS_DIR = (PACKAGE_ROOT / "assets").resolve()
FONTS_DIR = (ASSETS_DIR / "fonts" / "Poppins").resolve()
IMAGES_DIR = (ASSETS_DIR / "images").resolve()

# Register custom Poppins fonts from the package assets directory
if FONTS_DIR.exists():
    for font_file in FONTS_DIR.glob("*.ttf"):
        fm.fontManager.addfont(str(font_file))

# Public API imports
from tpsplots.api import generate  # noqa: E402
from tpsplots.exceptions import (  # noqa: E402
    ConfigurationError,
    DataSourceError,
    RenderingError,
    TPSPlotsError,
)

__all__ = [
    "ASSETS_DIR",
    "FONTS_DIR",
    "IMAGES_DIR",
    # Package paths (for advanced usage)
    "PACKAGE_ROOT",
    "STYLE_DIR",
    "TPS_STYLE_FILE",
    "ConfigurationError",
    "DataSourceError",
    "RenderingError",
    # Exceptions
    "TPSPlotsError",
    "__version__",
    # Core API
    "generate",
]
