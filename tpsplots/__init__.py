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

from pathlib import Path


def _configure_matplotlib():
    """Use a single non-interactive backend for all package rendering."""
    import matplotlib

    # tpsplots only renders charts to files or HTTP responses. Forcing Agg
    # avoids GUI FigureManager creation and keeps preview rendering safe in
    # worker threads on macOS and other desktop platforms.
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
