from datetime import datetime
from typing import ClassVar

import pandas as pd

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController
from tpsplots.data_sources.missions import Missions


class NASAFY2026Controller(NASAFYChartsController):
    FISCAL_YEAR = 2026
    WORKFORCE_PROJECTION = 11853  # FY2026 proposed workforce level

    # Mapping of CSV account names to short display names for charts.
    # Note: CSV uses "LEO & Space Ops" (not "Space Operations").
    # Inspector General excluded (too small relative to other accounts).
    ACCOUNTS: ClassVar[dict[str, str]] = {
        "Deep Space Exploration Systems": "Exploration",
        "LEO & Space Ops": "Space Ops",
        "Space Technology": "Tech",
        "Science": "Science",
        "Aeronautics": "Aero",
        "STEM Engagement": "STEM",
        "Safety, Security, & Mission Services": "SSMS",
        "Construction & Environmental Compliance & Restoration": "CECR",
    }

    # Custom charts for FY 2026
    def nasa_center_workforce_map(self):
        """Prepare a map showing workforce breakdown at NASA centers."""

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

        return {
            "pie_data": pie_data,
            "export_df": export_df,
        }

    def cancelled_missions_lollipop_chart(self):
        """
        Prepare a lollipop chart showing the launch date to end of all NASA missions
        proposed as cancelled in FY 2026.
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

        # Filter to active missions led by NASA
        df = df[df["Status"].isin(["Prime Mission", "Extended Mission"])]

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

        return {
            "categories": df["Mission"],
            "start_values": df["Launch Year"],
            "end_values": df["End Year"],
            "xlim": (1997, 2027),
            "export_df": export_df,
            "total_projects": total_projects,
            "total_value": total_value,
            "total_development_time": total_development_time,
        }
