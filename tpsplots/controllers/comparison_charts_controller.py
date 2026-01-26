"""Concrete NASA budget charts using specialized chart views."""

import logging
from datetime import datetime

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController

logger = logging.getLogger(__name__)


class ComparisonCharts(ChartController):
    """Controller for comparison charts (waffle, etc.)."""

    # Default fiscal year for spending data (can be overridden in subclass)
    FISCAL_YEAR = datetime.today().year - 1

    def nasa_spending_as_part_of_annual_us_expenditures(self) -> dict:
        """Generate NASA's portion of U.S. spending for waffle chart.

        Returns data for YAML-driven chart generation, following patterns
        from nasa_fy_charts_controller.py. View-related config (colors,
        layout, legend) should be defined in YAML.

        Returns:
            dict with keys:
                - values: dict mapping category names to block counts
                - labels: list of formatted labels with percentages
                - fiscal_year: int - The fiscal year of the data
                - source: str - Source attribution text
                - block_value: int - Dollar value per block
                - export_df: DataFrame for CSV export
        """
        from tpsplots.processors.dataframe_to_yaml_processor import (
            DataFrameToYAMLConfig,
            DataFrameToYAMLProcessor,
        )

        fiscal_year = 2024

        # Raw spending data (nominal dollars)
        comparisons = {
            "Non-NASA U.S. Spending": 6_800_000_000_000,
            "NASA": 25_000_000_000,
        }

        # Each block represents $25 billion
        block_value = 25_000_000_000

        # Scale values to block counts
        scaled_values = {k: round(v / block_value) for k, v in comparisons.items()}

        # Order by value ascending (NASA first, then Non-NASA)
        sorted_values = dict(sorted(scaled_values.items(), key=lambda item: item[1], reverse=False))

        # Calculate percentage labels
        total = sum(comparisons.values())
        labels = [
            f"{k} ({v / total * 100:.2f}%)"
            for k, v in sorted(comparisons.items(), key=lambda item: item[1], reverse=False)
        ]

        # Build export DataFrame
        export_data = [
            {"Category": k, f"FY {fiscal_year} Spending ($)": v} for k, v in comparisons.items()
        ]
        export_df = pd.DataFrame(export_data)

        # Store metadata in a DataFrame for consistency with other controllers
        # (even though waffle chart uses dict values, we follow the attrs pattern)
        metadata_df = pd.DataFrame({"_placeholder": [0]})
        metadata_df.attrs["fiscal_year"] = fiscal_year
        metadata_df.attrs["source"] = f"Congressional Budget Office, FY {fiscal_year}"
        metadata_df.attrs["block_value"] = block_value

        # Use processor to extract attrs as top-level keys
        config = DataFrameToYAMLConfig(
            fiscal_year_column="__none__",
            export_df_key="export_df",
        )
        result = DataFrameToYAMLProcessor(config).process(metadata_df)

        # Remove placeholder column, add actual data
        result.pop("_placeholder", None)
        result["values"] = sorted_values
        result["labels"] = labels
        result["export_df"] = export_df

        return result
