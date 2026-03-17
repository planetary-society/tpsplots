from datetime import datetime
from typing import ClassVar

import pandas as pd

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController
from tpsplots.data_sources.missions import Missions


class NASAFY2026Controller(NASAFYChartsController):
    """Controller for FY 2026 NASA budget charts and analysis."""

    FISCAL_YEAR = 2026
    WORKFORCE_PROJECTION = 11853  # FY2026 proposed workforce level

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

    # Custom charts for FY 2026
    def nasa_center_workforce_map(self):
        """Return workforce data for each NASA center as a US map pie chart.

        Provides per-center pie data showing proposed FY 2026 staffing cuts
        vs remaining workforce, suitable for the us_map_pie chart type.

        Returns:
            dict with keys:
                - data: DataFrame with per-center staffing totals
                - pie_data: dict mapping center abbreviations to pie configs
                  (values, labels, colors)
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys
        """

        pie_data = {
            "HQ": {
                "values": [1366, 475],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "ARC": {
                "values": [755, 470],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "AFRC": {
                "values": [309, 191],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "GRC": {
                "values": [837, 554],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "GSFC": {
                "values": [1549, 1335],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "JSC": {
                "values": [2594, 698],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "KSC": {
                "values": [1506, 510],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "LaRC": {
                "values": [1058, 672],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "MSFC": {
                "values": [1714, 526],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "SSC": {
                "values": [166, 108],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
        }

        # Create export data
        export_data = []
        for center, data in pie_data.items():
            fy2025_staffing = sum(data["values"])
            proposed_fy2026_staffing = data["values"][0]
            export_data.append(
                {
                    "NASA Center": center,
                    "FY 2025 Staffing": fy2025_staffing,
                    "Proposed FY 2026 Staffing": proposed_fy2026_staffing,
                }
            )

        export_df = pd.DataFrame(export_data)

        metadata = self._build_metadata(
            export_df,
            fiscal_year_col=None,
        )

        return {
            "data": export_df,
            "pie_data": pie_data,
            "export_df": export_df,
            "metadata": metadata,
        }

    def cancelled_missions_lollipop_chart(self):
        """Return lollipop chart data for NASA missions proposed as cancelled in FY 2026.

        Shows the launch date to cancellation date range for each active
        NASA-led mission proposed for cancellation in the FY 2026 budget.

        Returns:
            dict with keys:
                - data: DataFrame with mission details
                - categories: Series of mission names
                - start_values: Series of launch years
                - end_values: Series of end years (2026)
                - xlim: tuple of x-axis limits
                - total_projects: int count of affected missions
                - total_value: str formatted total lifecycle cost
                - total_development_time: int total development years
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys
        """
        data_source = Missions()
        df = data_source.data()

        # Add explicit cancellation date
        df["Cancellation Date"] = datetime(2026, 1, 1)

        df["Launch Year"] = df["Launch Date"].dt.year
        df["End Year"] = df["Cancellation Date"].dt.year
        # Safely extract year, accounting for NaT/NaN values
        df["Formulation Start Year"] = df["Formulation Start"].apply(
            lambda x: pd.to_datetime(x).year if pd.notnull(x) else pd.NA
        )

        # Calculate 'Duration (years)' only for valid rows
        df["Duration (years)"] = pd.to_numeric(
            df["End Year"] - df["Launch Year"], errors="coerce"
        ).fillna(0)

        df["Development Time (years)"] = pd.to_numeric(
            df["Launch Year"] - df["Formulation Start Year"], errors="coerce"
        ).fillna(0)

        # Filter by only NASA-led missions
        df = df[df["NASA Led?"].isin([True])]

        # Filter to active missions led by NASA (case-insensitive)
        allowed_statuses = {"prime mission", "extended mission"}
        normalized_status = df["Status"].astype(str).str.strip().str.casefold()
        df = df[normalized_status.isin(allowed_statuses)]

        total_development_time = round(df["Development Time (years)"].sum())
        total_value = self.round_to_millions(df["LCC"].sum())
        total_projects = len(df)

        # Rename every mission to just use the values if parentheses (if present)
        # If the mission name contains parentheses, extract the text inside; otherwise, keep the original name
        df["Mission"] = (
            df["Mission"].str.extract(r"\(([^)]+)\)", expand=False).fillna(df["Mission"])
        )

        # Prepare export data
        export_df = df.copy().drop(columns=["NASA Led?"])

        metadata = self._build_metadata(df, fiscal_year_col=None)

        return {
            "data": df,
            "categories": df["Mission"],
            "start_values": df["Launch Year"],
            "end_values": df["End Year"],
            "xlim": (1997, 2027),
            "export_df": export_df,
            "total_projects": total_projects,
            "total_value": total_value,
            "total_development_time": total_development_time,
            "metadata": metadata,
        }
