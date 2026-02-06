from typing import ClassVar

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController


class NASAFY2027Controller(NASAFYChartsController):
    FISCAL_YEAR = 2027
    WORKFORCE_PROJECTION = 0  # FY2027 proposed workforce level

    # Mapping of CSV account names to short display names for charts.
    # Note: CSV uses "LEO & Space Ops" (not "Space Operations").
    # Inspector General excluded (too small relative to other accounts).
    ACCOUNTS: ClassVar[dict[str, str]] = {
        "Deep Space Exploration Systems": "Exploration",
        "LEO & Space Ops": "Space Ops",
        "Space Technology": "Space Tech",
        "Science": "Science",
        "Aeronautics": "Aero",
        "STEM Engagement": "STEM",
        "Safety, Security, & Mission Services": "SSMS",
        "Construction & Environmental Compliance & Restoration": "CECR",
    }
