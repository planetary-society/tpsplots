"""Concrete NASA budget charts using specialized chart views."""

import logging
from datetime import datetime

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Directorates, Historical

logger = logging.getLogger(__name__)


class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def nasa_budget_by_year(self) -> dict:
        """Return comprehensive NASA budget data for YAML-driven chart generation.

        This method provides raw data without filtering or styling metadata.
        YAML files are responsible for:
        - Filtering via xlim
        - Styling (colors, linestyles, labels)
        - Axis configuration (ylim, scale)

        Returns:
            dict with keys:
                - fiscal_year: Series of fiscal years as datetime
                - presidential_administration: Series of president names
                - pbr: Nominal Presidential Budget Request values
                - appropriation: Nominal Congressional Appropriation values
                - white_house_projection: White House budget projections
                - pbr_adjusted: Inflation-adjusted PBR (NNSI)
                - appropriation_adjusted: Inflation-adjusted appropriation (NNSI)
                - export_df: DataFrame for CSV export
                - max_fiscal_year: Maximum fiscal year (for source attribution)
        """
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        # Get full dataset without filtering
        df = Historical().data()

        # Apply inflation adjustment explicitly
        inflation_config = InflationAdjustmentConfig(
            nnsi_columns=["PBR", "Appropriation"],
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Prepare export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "Presidential Administration",
                "PBR",
                "Appropriation",
                "White House Budget Projection",
                "PBR_adjusted_nnsi",
                "Appropriation_adjusted_nnsi",
            ],
        )

        # Get max fiscal year for source attribution
        max_fy = int(df["Fiscal Year"].max().strftime("%Y"))

        return {
            # Core data columns
            "fiscal_year": df["Fiscal Year"],
            "presidential_administration": df["Presidential Administration"],
            # Nominal dollar values
            "pbr": df["PBR"],
            "appropriation": df["Appropriation"],
            "white_house_projection": self._clean_projection_overlap(df),
            # Inflation-adjusted values
            "pbr_adjusted": df["PBR_adjusted_nnsi"],
            "appropriation_adjusted": df["Appropriation_adjusted_nnsi"],
            # Export and metadata
            "export_df": export_df,
            "max_fiscal_year": max_fy,
        }

    def nasa_major_programs_by_year_inflation_adjusted(self):
        """Line chart of NASA's directorate budgets from 2007 until the last fiscal year."""
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        df = Directorates().data().dropna(subset=["Science"])  # Drop rows without directorate data

        # Apply inflation adjustment explicitly to all directorate columns
        directorate_cols = [
            "Aeronautics",
            "Deep Space Exploration Systems",
            "LEO Space Operations",
            "Space Technology",
            "Science",
            "STEM Education",
            "Facilities, IT, & Salaries",
        ]
        inflation_config = InflationAdjustmentConfig(
            nnsi_columns=directorate_cols,
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Calculate the last fiscal year
        last_completed_fy = datetime(datetime.today().year - 1, 1, 1)

        # Filter out df to only include years up to the last completed fiscal year
        df = df[df["Fiscal Year"] <= last_completed_fy]

        # Prepare data for view
        fiscal_years = df["Fiscal Year"]

        y_limit = (
            df["Deep Space Exploration Systems_adjusted_nnsi"].max() // 5000000000 + 1
        ) * 5000000000

        y_data = [
            df["Deep Space Exploration Systems_adjusted_nnsi"],
            df["Science_adjusted_nnsi"],
            df["Aeronautics_adjusted_nnsi"],
            df["Space Technology_adjusted_nnsi"],
            df["STEM Education_adjusted_nnsi"],
            df["LEO Space Operations_adjusted_nnsi"],
            df["Facilities, IT, & Salaries_adjusted_nnsi"],
        ]
        labels = [
            "Deep Space Exploration Systems",
            "Science Mission Directorate",
            "Aeronautics",
            "Space Technology",
            "STEM Education",
            "LEO Space Operations",
            "SSMS/CECR (Overhead)",
        ]

        # Export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "Deep Space Exploration Systems",
                "Deep Space Exploration Systems_adjusted_nnsi",
                "Science",
                "Science_adjusted_nnsi",
                "Aeronautics",
                "Aeronautics_adjusted_nnsi",
                "Space Technology",
                "Space Technology_adjusted_nnsi",
                "STEM Education",
                "STEM Education_adjusted_nnsi",
                "LEO Space Operations",
                "LEO Space Operations_adjusted_nnsi",
                "Facilities, IT, & Salaries",
                "Facilities, IT, & Salaries_adjusted_nnsi",
            ],
        )

        return {
            "source": f"NASA Budget Justifications, FYs 2007-{fiscal_years.max():%Y}",
            "fiscal_years": fiscal_years,
            "y_data": y_data,
            "labels": labels,
            "start_date": datetime(2008, 1, 1),
            "end_date": fiscal_years.max(),
            "y_limit": y_limit,
            "ylim": (0, y_limit),
            "xlim": (datetime(2008, 1, 1), fiscal_years.max()),
            "legend": {
                "loc": "upper right",
                "fontsize": "medium",  # Readable size
                "ncol": 3,
                "handlelength": 0.8,
            },
            "export_df": export_df,
        }

    def nasa_major_activites_donut_chart(self):
        """Generate donut chart breakdown of NASA directorate budgets for the last fiscal year."""
        df = Directorates().data()

        # Calculate the last fiscal year
        last_completed_fy = datetime(datetime.today().year - 1, 1, 1)

        # Filter to just that fiscal year
        # First convert the Fiscal Year column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"]):
            df["Fiscal Year"] = pd.to_datetime(df["Fiscal Year"])

        # Filter the DataFrame to the last completed fiscal year
        year_df = df[df["Fiscal Year"].dt.year == last_completed_fy.year]

        # Check if we have data for the last completed fiscal year
        if year_df.empty:
            # Fall back to the most recent available year
            latest_available_year = df["Fiscal Year"].max()
            year_df = df[df["Fiscal Year"] == latest_available_year]

            # Provide a warning in the logs
            logger.warning(
                f"No data found for FY {last_completed_fy.year}, falling back to {latest_available_year:%Y}"
            )

        # Select only monetary columns (not fiscal year or adjusted columns)
        labels = [
            "Science",
            "Aeronautics",
            "Deep Space Exploration Systems",
            "LEO Space Operations",
            "Space Technology",
            "Facilities, IT, & Salaries",
        ]

        # Extract values from the single row
        directorates_df = year_df[labels]

        values = directorates_df.iloc[0].tolist()

        # Sort values labels
        sorted_data = list(zip(values, labels, strict=False))
        sorted_values, sorted_labels = zip(*sorted_data, strict=False)

        # Create export dataframe
        export_data = []
        for label, value in zip(sorted_labels, sorted_values, strict=False):
            export_data.append(
                {"Directorate": label, f"FY {last_completed_fy.year} Budget ($)": value}
            )
        export_data.append(
            {
                "Directorate": "STEM Education",
                f"FY {last_completed_fy.year} Budget ($)": year_df["STEM Education"].values[0],
            }
        )  # Add STEM Education back to export
        export_df = pd.DataFrame(export_data)

        return {
            "source": f"FY {last_completed_fy:%Y} Congressional Appropriations",
            "sorted_values": sorted_values,
            "sorted_labels": sorted_labels,
            "export_df": export_df,
        }
