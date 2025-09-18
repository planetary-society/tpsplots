"""CSV file data controller for YAML-driven chart generation."""
from pathlib import Path
import pandas as pd
import logging
from tpsplots.controllers.chart_controller import ChartController

logger = logging.getLogger(__name__)


class CSVController(ChartController):
    """
    Controller for processing CSV file data sources.

    This controller provides a standard interface for loading CSV files
    within the YAML chart generation system, while maintaining consistency
    with other controllers that inherit from ChartController.
    """

    def __init__(self, csv_path: str = None):
        """
        Initialize the CSVController with a CSV file path.

        Args:
            csv_path: Path to the CSV file to load
        """
        super().__init__()
        self.csv_path = csv_path

    def load_data(self):
        """
        Load data from CSV file and return as dict for YAML processing.

        Returns:
            dict: Dictionary containing 'data' key with pandas DataFrame

        Raises:
            ValueError: If csv_path is not provided
            RuntimeError: If CSV file cannot be read
        """
        if not self.csv_path:
            raise ValueError("csv_path must be provided to load CSV data")

        try:
            df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded CSV data from {self.csv_path} ({len(df)} rows, {len(df.columns)} columns)")
            return {'data': df}
        except Exception as e:
            raise RuntimeError(f"Error reading CSV file {self.csv_path}: {e}")

    def get_data_summary(self):
        """
        Get a summary of the loaded data for debugging purposes.

        Returns:
            dict: Summary information about the loaded data
        """
        if not self.csv_path:
            return {"error": "No CSV path specified"}

        try:
            df = pd.read_csv(self.csv_path)
            return {
                "file_path": self.csv_path,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict('records')
            }
        except Exception as e:
            return {"error": f"Could not analyze CSV file: {e}"}