from typing import ClassVar

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController


class NASAFY2025Controller(NASAFYChartsController):
    FISCAL_YEAR = 2025

    ACCOUNTS: ClassVar[list[str]] = [
        "Deep Space Exploration Systems",
        "Space Operations",
        "Space Technology",
        "Science",
        "Aeronautics",
        "STEM Engagement",
        "Safety, Security, & Mission Services",
        "Construction & Environmental Compliance & Restoration",
        "Inspector General",
    ]
