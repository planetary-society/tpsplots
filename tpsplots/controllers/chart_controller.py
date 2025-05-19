"""tpsplots.base – shared chart infrastructure"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from tpsplots.views import ChartView, LineChartView, WaffleChartView

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
        return self._views[view_type]
    
    @abstractmethod
    def generate_charts(self):
        """
        Generate all charts provided by this controller.
        Subclasses must implement this method.
        """
        pass

    def _get_axis_limit_y(self, max_value: float, multiple: float = 5000000000, always_extend: bool = True) -> float:
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

    def _get_axis_limit_x(self, start_year: int, end_year: int, multiple: int = 5, always_extend: bool = False) -> int:
        """ Returns the next highest integer divisible by the multiple given a 
        start year and exceeding the limit of the end_year

        Example: If NASA's budget begins in 1959 and we have data through 2026,
        and we want the next highest year that is divisible by 5, the method will
        return 2029.

        This is helpful for ensuring clean and consistent x-axes for charts.

        Args:
            start_year (int): Starting point for fiscal year range
            end_year (int): End point for fiscal year with actual data
            multiple (int): The multiplier. Defaults to 5.
            always_extend (bool): When True, always adds at least one multiple beyond end_year,
                                even if end_year already falls on a multiple boundary.
                                When False, only extends if needed.

        Returns:
            int: The next year after end_year where (year - start_year) % multiple == 0
        """
        # Find the remainder when dividing the difference by multiple
        remainder = (end_year - start_year) % multiple

        # If the remainder is 0, end_year is already at a multiple boundary
        if remainder == 0:
            # If always_extend is True or we're on a boundary, add a full multiple
            return end_year + multiple if always_extend else end_year

        # Otherwise, add the difference needed to reach the next multiple boundary
        return end_year + (multiple - remainder)