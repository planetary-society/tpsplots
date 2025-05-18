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