import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.style.core  # For reload_library

# The root directory of the 'tpsplots' package
PACKAGE_ROOT = Path(__file__).parent

STYLE_DIR = (PACKAGE_ROOT / "views" / "style").resolve()

TPS_STYLE_FILE = (STYLE_DIR / "tps_base.mplstyle").resolve()