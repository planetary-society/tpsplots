import warnings
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.style.core  # For reload_library

# The root directory of the 'tpsplots' package
PACKAGE_ROOT = Path(__file__).parent

STYLE_DIR = (PACKAGE_ROOT / "views" / "style").resolve()

TPS_STYLE_FILE = (STYLE_DIR / "tps_base.mplstyle").resolve()

# Register custom Poppins fonts from the package fonts directory
FONTS_DIR = (PACKAGE_ROOT.parent / "fonts" / "Poppins").resolve()
if FONTS_DIR.exists():
    for font_file in FONTS_DIR.glob("*.ttf"):
        fm.fontManager.addfont(str(font_file))
