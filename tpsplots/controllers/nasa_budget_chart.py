"""Concrete NASA budget charts using specialized chart views."""

import logging
from datetime import datetime

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Directorates, Historical

logger = logging.getLogger(__name__)


class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Historical(),  # Historical NASA budget data source
        )

    def nasa_budget_pbr_appropriation_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart with PBR and Appropriations."""
        self.data_source = Historical()  # Reset data source to Historical for this chart
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])

        # Prepare data for view
        fiscal_years = df["Fiscal Year"]

        # Prepare cleaned export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "PBR",
                "Appropriation",
                "PBR_adjusted_nnsi",
                "Appropriation_adjusted_nnsi",
            ],
        )

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year, 10, True)
        y_limit = self._get_rounded_axis_limit_y(df["PBR"].max(), 5000000000)

        # Load the Line plotter view to access colors
        line_view = self.get_view("Line")

        return {
            "title": "The President's budget proposal sets the tone",
            "subtitle": "Except in the aftermath of Challenger, Congress has never exceeded a NASA budget proposal by more than 9%.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
            "fiscal_years": fiscal_years,
            "pbr_data": df["PBR"],
            "appropriation_data": df["Appropriation"],
            "colors": ["#3696CE", line_view.COLORS["blue"]],
            "linestyles": [":", "-"],
            "labels": ["NASA Budget Request", "Congressional Appropriation"],
            "xlim": [datetime(1958, 1, 1), datetime(x_limit, 1, 1)],
            "ylim": [0, y_limit],
            "legend": {"loc": "lower right"},
            "export_df": export_df,
        }

    def nasa_budget_by_year_with_projection_inflation_adjusted(self):
        """Generate historical NASA budget chart with single appropriation line."""
        self.data_source = Historical()  # Reset data source to Historical for this chart
        # Get data from model
        df = self.data_source.data()

        # Prepare data for view
        fiscal_years = df["Fiscal Year"]

        # Prepare cleaned export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "Appropriation",
                "White House Budget Projection",
                "Appropriation_adjusted_nnsi",
            ],
        )

        # Remove "White House Budget Proposal" values where "Appropriation" is present, for clarity
        export_df.loc[df["Appropriation"].notna(), "White House Budget Projection"] = pd.NA

        # Select the first Fiscal Year of the first non-empty White House Budget Projection
        first_projection_year = df.loc[
            df["White House Budget Projection"].notna(), "Fiscal Year"
        ].min()
        if pd.isna(first_projection_year):
            first_projection_year = (
                fiscal_years.max()
            )  # If no projections, set to max fiscal year to avoid filtering
        first_projection_year = int(first_projection_year.strftime("%Y")) + 1

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year, 10, False)
        y_limit = self._get_rounded_axis_limit_y(
            df["Appropriation_adjusted_nnsi"].max(), 5000000000
        )

        return {
            "fiscal_years": fiscal_years,
            "appropriation_adjusted_nnsi": df["Appropriation_adjusted_nnsi"],
            "white_house_budget_projection": df["White House Budget Projection"],
            "xlim": [datetime(1958, 1, 1), datetime(x_limit, 1, 1)],
            "ylim": [0, y_limit],
            "legend": {"loc": "lower right"},
            "source": f"NASA Budget Justifications, FYs 1961-{first_projection_year}",
            "export_df": export_df,
            "dataframe": df,
        }

    def nasa_budget_by_presidential_administration(self):
        """Generate NASA budget by presidential administration - returns full historical data.

        Returns a dict with full budget data for YAML processing. Individual president
        YAML files filter the data using xlim.
        """
        self.data_source = Historical()  # Reset data source to Historical for this chart
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])

        # Prepare data for view
        fiscal_years = df["Fiscal Year"]

        # Prepare export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "PBR",
                "Appropriation",
                "PBR_adjusted_nnsi",
                "Appropriation_adjusted_nnsi",
                "Presidential Administration",
            ],
        )

        # Get line view for colors
        line_view = self.get_view("Line")

        # Calculate y limit based on max value in full dataset
        y_limit = self._get_rounded_axis_limit_y(df["PBR_adjusted_nnsi"].max(), 20e9)

        return {
            "fiscal_years": fiscal_years,
            "pbr_adjusted": df["PBR_adjusted_nnsi"],
            "appropriation_adjusted": df["Appropriation_adjusted_nnsi"],
            "color": ["#3696CE", line_view.COLORS["blue"]],
            "linestyle": [":", "-"],
            "label": ["Presidential Request", "Congressional Appropriation"],
            "ylim": [0, y_limit],
            "scale": "billions",
            "fiscal_year_ticks": False,
            "export_df": export_df,
        }

    def nasa_major_programs_by_year_inflation_adjusted(self):
        """Line chart of NASA's directorate budgets from 2007 until the last fiscal year."""
        self.data_source = Directorates()
        df = self.data_source.data().dropna(
            subset=["Science"]
        )  # Drop rows without directorate data

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
        self.data_source = Directorates()

        # Get data
        df = self.data_source.data()

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
