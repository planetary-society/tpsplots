from typing import ClassVar

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController


class NASAFY2027Controller(NASAFYChartsController):
    """Controller for FY 2027 NASA budget charts and analysis."""

    FISCAL_YEAR = 2027
    WORKFORCE_PROJECTION = 0  # FY2027 proposed workforce level

    # Mapping of CSV account names to short display names for charts.
    # Note: CSV uses "LEO & Space Ops" (not "Space Operations").
    # Inspector General excluded (too small relative to other accounts).
    ACCOUNTS: ClassVar[dict[str, str]] = {
        "Exploration": "Exploration",
        "Space Operations": "Space Ops",
        "Space Technology": "Space Tech",
        "Science": "Science",
        "Aeronautics": "Aero",
        "STEM Engagement": "STEM",
        "Safety, Security, and Mission Services": "SSMS",
        "Construction and Environmental Compliance and Restoration": "CECR",
    }
