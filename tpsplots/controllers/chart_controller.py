"""tpsplots.base - shared chart infrastructure"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import ClassVar

import pandas as pd

from tpsplots.views import (
    BarChartView,
    DonutChartView,
    LineChartView,
    LineSubplotsView,
    LollipopChartView,
    StackedBarChartView,
    USMapPieChartView,
    WaffleChartView,
)

logger = logging.getLogger(__name__)


class ChartController:
    """
    Base class for chart controllers in the MVC pattern.

    This class coordinates between data sources (models) and the ChartView.
    Subclasses should implement methods that prepare data and call
    appropriate view methods.
    """

    # Registry mapping view type names to their classes.
    # This follows the Open/Closed Principle - extend by adding entries,
    # not by modifying get_view() method.
    VIEW_REGISTRY: ClassVar[dict[str, type]] = {
        "Line": LineChartView,
        "Bar": BarChartView,
        "Donut": DonutChartView,
        "LineSubplots": LineSubplotsView,
        "Lollipop": LollipopChartView,
        "StackedBar": StackedBarChartView,
        "USMapPie": USMapPieChartView,
        "Waffle": WaffleChartView,
    }

    def __init__(self, data_source=None, outdir: Path = Path("charts")):
        """
        Initialize a chart controller.

        Args:
            data_source: The data source (model) to use for chart data
            outdir: Output directory for chart files
        """
        self.data_source = data_source
        self.outdir = outdir
        self._views: dict[str, object] = {}

    def get_view(self, view_type: str):
        """
        Get or create a view of the specified type.

        Uses lazy initialization - views are only created when first requested
        and then cached for reuse.

        Args:
            view_type: The type of view to get (e.g., 'Line', 'Bar', 'Donut')

        Returns:
            An instance of the requested view type

        Raises:
            ValueError: If view_type is not registered
        """
        if view_type not in self._views:
            if view_type not in self.VIEW_REGISTRY:
                available = ", ".join(sorted(self.VIEW_REGISTRY.keys()))
                raise ValueError(f"Unknown view type: '{view_type}'. Available types: {available}")
            self._views[view_type] = self.VIEW_REGISTRY[view_type](self.outdir)
        return self._views[view_type]

    def generate_charts(self):
        """
        Generate all charts provided by this controller.

        This default implementation automatically discovers and calls all public
        methods in the controller that appear to be chart generation methods.

        Subclasses can override this method if they need custom behavior.
        """
        # Get all methods defined in the subclass
        subclass_methods = []

        # Get the class hierarchy to filter out base class methods
        base_methods = set(dir(ChartController))

        # Get all attributes of the instance
        for name in dir(self):
            # Skip private/protected methods and base class methods
            if name.startswith("_") or name in base_methods:
                continue

            # Get the attribute
            attr = getattr(self, name)

            # Check if it's a callable (method or function)
            if not callable(attr):
                continue

            # Check if it's a simple method (only takes self)
            try:
                sig = inspect.signature(attr)
                params = list(sig.parameters.keys())
                # Only include methods that take just 'self' as parameter
                if len(params) == 0 or (len(params) == 1 and params[0] == "self"):
                    subclass_methods.append((name, attr))
            except Exception:
                # Skip if we can't inspect the signature
                continue

        # Sort methods by name for consistent ordering
        subclass_methods.sort(key=lambda x: x[0])

        if not subclass_methods:
            logger.warning(f"No chart generation methods found in {self.__class__.__name__}")
            return

        logger.info(f"Generating {len(subclass_methods)} charts from {self.__class__.__name__}")

        # Call each method
        for method_name, method in subclass_methods:
            try:
                logger.info(f"Generating chart: {method_name}")
                method()
            except Exception as e:
                logger.error(f"Error generating chart {method_name}: {e}", exc_info=True)

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
