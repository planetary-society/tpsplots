"""tpsplots.base - shared chart infrastructure"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ChartController:
    """
    Base class for chart controllers in the MVC pattern.

    This class provides shared utilities for data preparation and formatting.
    Subclasses implement methods that return data dictionaries for YAML-driven
    chart generation.
    """

    def _get_rounded_axis_limit_y(
        self, max_value: float, multiple: float = 5000000000, always_extend: bool = True
    ) -> float:
        """
        Returns a reasonable upper boundary for the y-axis based on the maximum value in the data.

        This method rounds up the maximum value to the next multiple of the specified value,
        ensuring clean and consistent y-axis limits for charts, particularly for financial data.

        Example: For a maximum value of $23.7 billion and a multiple of $5 billion,
        this returns $25 billion.

        Args:
            max_value (float): The maximum value in the dataset
            multiple (float): The value to round up to. Defaults to 5 billion ($5,000,000,000)
            always_extend (bool): When True, ensures the limit is at least one multiple
                                higher than the max_value. When False, only extends if needed.
                                Defaults to True to provide headroom in charts.

        Returns:
            float: The rounded upper limit suitable for y-axis plotting
        """
        # If max_value is less than multiple, just return multiple for a cleaner chart
        if max_value < multiple:
            return multiple

        # Calculate how many whole multiples fit into max_value
        whole_multiples = max_value // multiple

        # Check if max_value is exactly at a multiple boundary
        if max_value % multiple == 0:
            # If always_extend is True or we're exactly at a boundary, add a full multiple
            return (whole_multiples + 1) * multiple if always_extend else max_value

        # Otherwise, round up to the next multiple
        return (whole_multiples + 1) * multiple

    def _get_rounded_axis_limit_x(
        self, upper_value: int, multiple: int = 10, always_extend: bool = False
    ) -> int:
        """Returns the next highest integer divisible by the multiple given a
        beyond the given upper_value

        Example: If we have data through FY 2026, and we want the next highest year that is
        divisible by 10, the method will return 2030.

        This is helpful for ensuring clean and consistent x-axes for charts.

        Args:
            upper_value (int): End point for fiscal year with actual data
            multiple (int): The multiplier. Defaults to 10.
            always_extend (bool): When True, always adds at least one multiple beyond upper_value,
                                even if upper_value already falls on a multiple boundary.
                                When False, only extends if needed.

        Returns:
            int: The next year after upper_value where % multiple == 0
        """
        # Find the remainder
        remainder = upper_value % multiple

        # If the remainder is 0, upper_value is already at a multiple boundary
        if remainder == 0:
            # If always_extend is True or we're on a boundary, add a full multiple
            return upper_value + multiple if always_extend else upper_value

        # Otherwise, add the difference needed to reach the next multiple boundary
        return upper_value + (multiple - remainder)

    def _export_helper(
        self, original_df: pd.DataFrame, columns_to_export: list[str]
    ) -> pd.DataFrame:
        """Helper method to prepare columns for export, assuming it will mostly be Fiscal Year and dollar amounts"""
        export_df = original_df[columns_to_export].copy().reset_index(drop=True)

        if "Fiscal Year" in columns_to_export:
            try:
                export_df["Fiscal Year"] = pd.to_datetime(export_df["Fiscal Year"]).dt.strftime(
                    "%Y"
                )
            except Exception:
                export_df["Fiscal Year"] = export_df["Fiscal Year"].astype(
                    str
                )  # Fallback to string

        for col in columns_to_export:
            if col == "Fiscal Year":
                continue
            numeric_series = pd.to_numeric(export_df[col], errors="coerce")
            export_df[col] = numeric_series.round(0)
        return export_df

    def _clean_projection_overlap(self, df: pd.DataFrame) -> pd.Series:
        """Clean White House Budget Projection to create smooth chart transitions.

        For overlapping fiscal years (where projection AND appropriation/PBR exist):
        - Set all but the LAST overlapping projection to NA
        - Replace the LAST overlapping projection with Appropriation (or PBR)

        This creates a clean visual connection between actual data and projections.

        Args:
            df: DataFrame with columns: "White House Budget Projection", "Appropriation", "PBR"

        Returns:
            pd.Series: Cleaned projection series
        """
        projection = df["White House Budget Projection"].copy()
        appropriation = df["Appropriation"]
        pbr = df["PBR"]

        # Find overlapping rows: projection exists AND (appropriation OR pbr exists)
        has_projection = projection.notna()
        has_actual = appropriation.notna() | pbr.notna()
        overlap_mask = has_projection & has_actual

        if not overlap_mask.any():
            return projection  # No overlaps, return as-is

        # Get indices of overlapping rows
        overlap_indices = df.index[overlap_mask].tolist()

        # Last overlapping index
        last_overlap_idx = overlap_indices[-1]

        # Set all overlapping projections to NA except the last one
        for idx in overlap_indices[:-1]:
            projection.loc[idx] = np.nan

        # For the last overlap, use Appropriation if available, else PBR
        if pd.notna(appropriation.loc[last_overlap_idx]):
            projection.loc[last_overlap_idx] = appropriation.loc[last_overlap_idx]
        elif pd.notna(pbr.loc[last_overlap_idx]):
            projection.loc[last_overlap_idx] = pbr.loc[last_overlap_idx]

        return projection

    @staticmethod
    def round_to_millions(amount: float) -> str:
        """Format money amount with commas and 2 decimal places, display as millions or billions based on the amount."""
        if amount < 0:
            is_neg = True
            amount = amount * -1
        else:
            is_neg = False

        if amount >= 1_000_000_000:
            formatted = f"${amount / 1_000_000_000:,.0f} billion"
        elif amount >= 10_000_000 or amount >= 1_000_000:
            formatted = f"${amount / 1_000_000:,.0f} million"
        else:
            formatted = f"${amount:,.2f}"

        if is_neg:
            formatted = "-" + formatted

        return formatted
