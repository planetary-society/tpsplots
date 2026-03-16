"""Concrete NASA budget charts using specialized chart views."""

import logging
from datetime import datetime

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Directorates, Historical, Workforce

logger = logging.getLogger(__name__)


class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def nasa_spending_share_by_year(self) -> dict:
        """Return cleaned spending-share series for dual-axis budget charts.

        Produces inflation-adjusted appropriation values and spending-share
        percentages cleaned by the data source layer.
        """
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        df = Historical().data()

        inflation_config = InflationAdjustmentConfig(nnsi_columns=["Appropriation"])
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        spending_col = "% of U.S. Spending"
        discretionary_col = "% of U.S. Discretionary Spending"
        if discretionary_col not in df.columns:
            df = df.copy()
            df[discretionary_col] = pd.Series(pd.NA, index=df.index)

        # Drop rows where primary right-axis series is invalid.
        df = df[df[spending_col].notna()].copy()

        export_cols = [
            "Fiscal Year",
            "Appropriation_adjusted_nnsi",
            spending_col,
            discretionary_col,
        ]
        export_df = self._export_helper(df, export_cols)

        metadata = self._build_metadata(
            df,
            fiscal_year_col="Fiscal Year",
            value_columns={
                "appropriation_adjusted": "Appropriation_adjusted_nnsi",
                "us_spending_percent": spending_col,
                "us_discretionary_spending_percent": discretionary_col,
            },
        )

        return {
            "data": df,
            "fiscal_year": df["Fiscal Year"],
            "appropriation_adjusted": df["Appropriation_adjusted_nnsi"],
            "us_spending_percent": df[spending_col],
            "us_spending_share": df[spending_col] / 100.0,
            "us_discretionary_spending_percent": df[discretionary_col],
            "us_discretionary_spending_share": df[discretionary_col] / 100.0,
            "export_df": export_df,
            "metadata": metadata,
        }

    def nasa_budget_by_year(self) -> dict:
        """Return comprehensive NASA budget data for YAML-driven chart generation.

        This method provides historical data without projections. For charts that
        need White House Budget Projections, use the FY-specific controller's
        pbr_historical_context() method instead.

        Returns:
            dict with keys:
                - fiscal_year: Series of fiscal years as datetime
                - presidential_administration: Series of president names
                - pbr: Nominal Presidential Budget Request values
                - appropriation: Nominal Congressional Appropriation values
                - pbr_adjusted: Inflation-adjusted PBR (NNSI)
                - appropriation_adjusted: Inflation-adjusted appropriation (NNSI)
                - export_df: DataFrame for CSV export
                - max_fiscal_year: Maximum fiscal year (for source attribution)
                - metadata: dict with helpful context values:
                    - max_fiscal_year, min_fiscal_year: Overall FY range
                    - max_pbr_fiscal_year, min_pbr_fiscal_year: FY range for PBR data
                    - max_appropriation_fiscal_year, min_appropriation_fiscal_year: FY range for appropriation data
                    - inflation_adjusted_year: Target FY for inflation adjustment (e.g., 2024)
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
                "PBR_adjusted_nnsi",
                "Appropriation_adjusted_nnsi",
            ],
        )

        # Build metadata with fiscal year ranges for each data column
        metadata = self._build_metadata(
            df,
            fiscal_year_col="Fiscal Year",
            value_columns={
                "pbr": "PBR",
                "appropriation": "Appropriation",
            },
        )

        # Keep max_fiscal_year at top level for backwards compatibility
        max_fy = metadata["max_fiscal_year"]

        return {
            "data": df,
            # Core data columns
            "fiscal_year": df["Fiscal Year"],
            "presidential_administration": df["Presidential Administration"],
            # Nominal dollar values
            "pbr": df["PBR"],
            "appropriation": df["Appropriation"],
            # Inflation-adjusted values
            "pbr_adjusted": df["PBR_adjusted_nnsi"],
            "appropriation_adjusted": df["Appropriation_adjusted_nnsi"],
            # Export and metadata
            "export_df": export_df,
            "max_fiscal_year": max_fy,  # Backwards compatible
            "metadata": metadata,
        }

    def nasa_major_programs_by_year_inflation_adjusted(self):
        """Line chart of NASA's directorate budgets from 2007 until the last fiscal year.

        Returns columnar data for flexible YAML-driven chart generation.

        Returns:
            dict with keys:
                - fiscal_year: Series of fiscal year dates
                - deep_space_exploration_systems: Series of adjusted budget values
                - science: Series of adjusted budget values
                - aeronautics: Series of adjusted budget values
                - space_technology: Series of adjusted budget values
                - stem_education: Series of adjusted budget values
                - space_operations: Series of adjusted budget values
                - overhead: Series of adjusted budget values (Facilities, IT, & Salaries)
                - export_df: DataFrame for CSV export
                - metadata: dict with max_fiscal_year, min_fiscal_year, source,
                  inflation_adjusted_year
        """
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        df = Directorates().data().dropna(subset=["Science"])  # Drop rows without directorate data

        # Apply inflation adjustment explicitly to all directorate columns
        directorate_cols = [
            "Aeronautics",
            "Deep Space Exploration Systems",
            "Space Operations",
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

        # Calculate max fiscal year for metadata
        max_fy = df["Fiscal Year"].max().year

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
                "Space Operations",
                "Space Operations_adjusted_nnsi",
                "Facilities, IT, & Salaries",
                "Facilities, IT, & Salaries_adjusted_nnsi",
            ],
        )

        # Metadata for YAML template interpolation
        metadata = self._build_metadata(
            df,
            source=f"NASA Budget Justifications, FYs 2007-{max_fy}",
            min_fiscal_year=2008,
        )

        return {
            "data": df,
            # Core data columns (individual series for YAML binding)
            "fiscal_year": df["Fiscal Year"],
            "deep_space_exploration_systems": df["Deep Space Exploration Systems_adjusted_nnsi"],
            "science": df["Science_adjusted_nnsi"],
            "aeronautics": df["Aeronautics_adjusted_nnsi"],
            "space_technology": df["Space Technology_adjusted_nnsi"],
            "stem_education": df["STEM Education_adjusted_nnsi"],
            "space_operations": df["Space Operations_adjusted_nnsi"],
            "overhead": df["Facilities, IT, & Salaries_adjusted_nnsi"],
            # Export and metadata
            "export_df": export_df,
            "metadata": metadata,
        }

    def nasa_major_activites_donut_chart(self) -> dict:
        """Generate donut chart breakdown of NASA directorate budgets for the last fiscal year.

        Returns columnar data for flexible YAML-driven chart generation, following
        the patterns established in nasa_fy_charts_controller.py.

        Returns:
            dict with keys:
                - Directorate: Series of directorate names (sorted by budget descending)
                - Budget: Series of budget values in dollars
                - fiscal_year: int - The fiscal year of the data
                - source: str - Source attribution text
                - total_budget: float - Total budget across displayed directorates
                - export_df: DataFrame for CSV export (includes STEM Education)
        """
        from tpsplots.processors.dataframe_to_yaml_processor import (
            DataFrameToYAMLConfig,
            DataFrameToYAMLProcessor,
        )

        df = Directorates().data()

        # Calculate the last completed fiscal year
        last_completed_fy = datetime(datetime.today().year - 1, 1, 1)

        # Ensure Fiscal Year is datetime for consistent filtering
        if not pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"]):
            df["Fiscal Year"] = pd.to_datetime(df["Fiscal Year"])

        # Filter to just that fiscal year
        year_df = df[df["Fiscal Year"].dt.year == last_completed_fy.year]

        # Fallback if no data for last completed FY
        if year_df.empty:
            latest_available_year = df["Fiscal Year"].max()
            year_df = df[df["Fiscal Year"] == latest_available_year]
            actual_fy = latest_available_year.year
            logger.warning(
                f"No data found for FY {last_completed_fy.year}, falling back to {actual_fy}"
            )
        else:
            actual_fy = last_completed_fy.year

        # Directorates to include in chart (STEM Education excluded due to small relative size)
        chart_directorates = [
            "Science",
            "Aeronautics",
            "Deep Space Exploration Systems",
            "Space Operations",
            "Space Technology",
            "Facilities, IT, & Salaries",
        ]

        # Build chart DataFrame with Directorate and Budget columns
        # Preserve original order for consistent display
        chart_data = [{"Directorate": d, "Budget": year_df[d].iloc[0]} for d in chart_directorates]
        chart_df = pd.DataFrame(chart_data)

        # Store metadata in DataFrame attrs (consistent with nasa_fy_charts_controller.py)
        chart_df.attrs["fiscal_year"] = actual_fy
        chart_df.attrs["source"] = f"FY {actual_fy} Congressional Appropriations"
        chart_df.attrs["total_budget"] = chart_df["Budget"].sum()

        # Build export DataFrame with all directorates (including STEM Education)
        all_directorates = [*chart_directorates, "STEM Education"]
        export_data = [
            {"Directorate": d, f"FY {actual_fy} Budget ($)": year_df[d].iloc[0]}
            for d in all_directorates
        ]
        export_df = pd.DataFrame(export_data)

        # Use DataFrameToYAMLProcessor for consistent conversion
        # Configure for categorical data (no fiscal year column in output)
        config = DataFrameToYAMLConfig(
            fiscal_year_column="__none__",  # Column doesn't exist, skips FY-specific logic
            export_df_key="export_df",
        )
        result = DataFrameToYAMLProcessor(config).process(chart_df)

        result["metadata"] = self._build_metadata(
            chart_df,
            fiscal_year_col=None,
            source=f"FY {actual_fy} Congressional Appropriations",
            max_fiscal_year=actual_fy,
            min_fiscal_year=actual_fy,
        )
        result["metadata"]["total_budget"] = float(chart_df.attrs["total_budget"])

        # Convert Series to lists for donut chart view compatibility
        # (DonutChartView expects lists, not Series, for values/labels)
        result["Directorate"] = result["Directorate"].tolist()
        result["Budget"] = result["Budget"].tolist()

        # Override export_df with our complete version (includes STEM Education)
        result["export_df"] = export_df

        return result

    def workforce(self) -> dict:
        """Return NASA workforce headcount data with year-over-year changes.

        Returns:
            dict with keys:
                - fiscal_year: Series of fiscal years as datetime
                - fte: Series of Full-time Equivalent counts
                - ftp: Series of Full-time Permanent counts
                - yoy_fte_change: Series of year-over-year FTE change (absolute)
                - yoy_pct_fte_change: Series of year-over-year FTE change (decimal fraction)
                - export_df: DataFrame for CSV export
                - metadata: dict with fiscal year ranges, per-column min/max/FY stats,
                  and peak/trough fiscal years (which FY had the highest/lowest value)
        """
        df = Workforce().data()

        export_cols = [
            "Fiscal Year",
            "Full-time Permanent (FTP)",
            "Full-time Equivalent (FTE)",
            "YOY FTE Change",
            "YOY % FTE Change",
        ]
        export_df = self._export_helper(df, export_cols, rounding={"YOY % FTE Change": 4})

        # Build standard metadata with per-column FY ranges and value stats
        metadata = self._build_metadata(
            df,
            fiscal_year_col="Fiscal Year",
            value_columns={
                "fte": "Full-time Equivalent (FTE)",
                "ftp": "Full-time Permanent (FTP)",
                "yoy_fte_change": "YOY FTE Change",
                "yoy_pct_fte_change": "YOY % FTE Change",
            },
            source="NASA Workforce Data",
        )

        # Add fiscal years where peak/trough occurred.
        # (The peak/trough *values* are already in max_{label}/min_{label} from
        # _build_metadata; these keys add the *when* — which FY had the extremum.)
        for label, col in [
            ("fte", "Full-time Equivalent (FTE)"),
            ("ftp", "Full-time Permanent (FTP)"),
        ]:
            valid = df[df[col].notna()]
            if not valid.empty:
                fy = valid["Fiscal Year"]
                metadata[f"peak_{label}_fiscal_year"] = int(
                    fy.loc[valid[col].idxmax()].strftime("%Y")
                )
                metadata[f"trough_{label}_fiscal_year"] = int(
                    fy.loc[valid[col].idxmin()].strftime("%Y")
                )

        return {
            "data": df,
            # Core data columns
            "fiscal_year": df["Fiscal Year"],
            "fte": df["Full-time Equivalent (FTE)"],
            "ftp": df["Full-time Permanent (FTP)"],
            "yoy_fte_change": df["YOY FTE Change"],
            "yoy_pct_fte_change": df["YOY % FTE Change"],
            # Export and metadata
            "export_df": export_df,
            "metadata": metadata,
        }
