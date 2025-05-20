"""tpsplots.base – shared chart infrastructure"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from tpsplots.views import ChartView, LineChartView, WaffleChartView, DonutChartView
import pandas as pd

class ChartController(ABC):
    """
    Base class for chart controllers in the MVC pattern.
    
    This class coordinates between data sources (models) and the ChartView.
    Subclasses should implement methods that prepare data and call
    appropriate view methods.
    """

    def __init__(self, data_source=None, outdir: Path = Path("charts")):
        """
        Initialize a chart controller.
        
        Args:
            data_source: The data source (model) to use for chart data
            outdir: Output directory for chart files
        """
        # The data source (model)
        self.data_source = data_source
        
        # Write directory for output fiels
        self.outdir = outdir

        # The chart output generator (view)
        # Set at the implemenation level using get_view()
        self._views = {}
        
    def get_view(self, view_type):
        """Get or create a view of the specified type."""
        if view_type not in self._views:
            if view_type == 'Line':
                self._views[view_type] = LineChartView(self.outdir)
            elif view_type == 'Waffle':
                self._views[view_type] = WaffleChartView(self.outdir)
            elif view_type == 'Donut':
                self._views[view_type] = DonutChartView(self.outdir)
        return self._views[view_type]
    
    @abstractmethod
    def generate_charts(self):
        """
        Generate all charts provided by this controller.
        Subclasses must implement this method.
        """
        pass

    def _get_rounded_axis_limit_y(self, max_value: float, multiple: float = 5000000000, always_extend: bool = True) -> float:
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

    def _get_rounded_axis_limit_x(self, upper_value: int, multiple: int = 10, always_extend: bool = False) -> int:
        """ Returns the next highest integer divisible by the multiple given a 
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
    
    def _export_helper(self,original_df: pd.DataFrame, columns_to_export: list[str]) -> pd.DataFrame:
        """ Helper method to prepare columns for export, assuming it will mostly be Fiscal Year and dollar amounts """
        export_df = original_df[columns_to_export].copy().reset_index(drop=True)
        
        if "Fiscal Year" in columns_to_export:
            try:
                export_df["Fiscal Year"] = pd.to_datetime(export_df["Fiscal Year"]).dt.strftime('%Y')
            except Exception as e:
                export_df["Fiscal Year"] = export_df["Fiscal Year"].astype(str) # Fallback to string
        
        for col in columns_to_export:
            if col == "Fiscal Year":
                continue
            numeric_series = pd.to_numeric(export_df[col], errors='coerce')
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
            formatted = "${:,.0f} billion".format(amount / 1_000_000_000)
        elif amount >= 10_000_000:
            formatted =  "${:,.0f} million".format(amount / 1_000_000)
        elif amount >= 1_000_000:
            formatted =  "${:,.0f} million".format(amount / 1_000_000)
        else:
            formatted = "${:,.2f}".format(amount)
        
        if is_neg:
            formatted = "-" + formatted
        
        return formatted

