from importlib import metadata
from pathlib import Path
import matplotlib.pyplot as plt

# Load TPS brand style globally
plt.style.use(Path(__file__).parent / "style" / "tps.mplstyle")

__all__ = ["base", "charts"]
__version__ = metadata.version(__name__) if metadata else "0.0.0"