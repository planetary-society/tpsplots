"""tpsplots.base – shared chart infrastructure"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from chart_view import ChartView

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
        
        # The chart generator (view)
        self.view = ChartView(outdir)
    
    @abstractmethod
    def generate_charts(self):
        """
        Generate all charts provided by this controller.
        Subclasses must implement this method.
        """
        pass