"""CSV file data controller for YAML-driven chart generation."""
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime
from tpsplots.controllers.chart_controller import ChartController

logger = logging.getLogger(__name__)


class MissionSpendingController(ChartController):
    """
    Prepares mission outlay and obligations data for charting

    """

    def __init__(self, csv_path: str = None):
        """
        Initialize the CSVController with a CSV file path.

        Args:
            csv_path: Path to the CSV file to load
        """
        super().__init__()
        self.csv_path = "../science-missions-reference/data/spending/"

    def process_mission_spending_data(self):
        missions = ["OSIRIS-APEX","Gold","IBEX","Juno","JWST","Mars 2020","MMS","MRO","New Horizons","OCO-2",
                    "ODY","Roman","SWOT","Terra"]
        for mission_name in missions:
            # snake case mission name to file name
            stem = self._snake_case(mission_name)
        
            for reporting_type in ['outlays','obligations']:            
                file_name = f"{self.csv_path}/{stem}_{reporting_type}_summary.csv"
                
                if Path(file_name).is_file():
                    data = self._process_mission_spending_data(file_name, reporting_type)
                    self._plot_chart(data, mission_name, reporting_type)
                else:
                    logger.warning(f"{reporting_type.capitalize} summary CSV file not found: {file_name}")
                
    
    def _process_mission_spending_data(self, file_name: str = None, type: str = "") -> dict:
        """
        Process mission spending data from CSV file.
        Returns a DataFrame with parsed dates, decades, status, and mass values.
        """
        
        if type == "outlays":
            fy_field = "fiscal_year"
            value_field = "cumulative_outlay"
            fy_period_field = "fiscal_period"
        elif type == "obligations":
            fy_field = "reporting_fiscal_year"
            value_field = "cumulative_obligations"
            fy_period_field = "reporting_fiscal_month"
        
        # Load data from CSV file
        df = self._read_csv(file_name)
        
        current_fy = 2025 # Interested in FY 2025 for now
        prior_fy = current_fy - 1
        
        # Months:
        fiscal_month_abbrs = [
            'Oct/Nov',
            'Dec',
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep'
        ]
        
        # Ensure sure dataframe is sorted by fiscal_year desc, fiscal_period asc
        df = df.sort_values(by=[fy_field, fy_period_field], ascending=[False, True])
        
        # Select current fiscal year values only:
        current_fy_values = df[df[fy_field] == current_fy][value_field].values
        
        # Append current_fy_values with None for each month not yet reported (USASpending combines Oct/Nov into 2nd period,
        # so there are only ever 11 periods (months) total
        if len(current_fy_values) < 11:
            current_fy_values = list(current_fy_values) + [None] * (11 - len(current_fy_values))
        
        prior_fy_values = df[df[fy_field] == prior_fy][value_field].values
        
        return {
            'dataframe': df,
            'current_fy': current_fy,
            'prior_fy': prior_fy,
            'x': fiscal_month_abbrs,
            'y1': current_fy_values,
            'y2': prior_fy_values,
        }
    
    def _snake_case(self, name: str) -> str:
        """Convert a string to snake_case."""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    def _plot_chart(self, data: dict, mission_name: str, reporting_type: str):
        line_view = self.get_view('Line')
        metadata = {
            "title": "{reporting_type} for {mission_name} in FY {current_fy} vs FY {prior_fy}".format(
                reporting_type=reporting_type.capitalize(),
                mission_name=mission_name,
                current_fy=data['current_fy'],
                prior_fy=data['prior_fy']
            ),
            "subtitle": "Shows cumulative actual spending by fiscal period as reported by USASpending.gov.",
            "source": "USASpending.gov"
        }
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem=f"{self._snake_case(mission_name)}_{reporting_type}_fy{data['current_fy']}_vs_fy{data['prior_fy']}",
            x=data['x'],
            y=[data['y1'], data['y2']],
            color=[line_view.COLORS["blue"], line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-", "--"],
            marker=["o", "o"],
            label=[f"FY {data['current_fy']}", f"FY {data['prior_fy']}"],
            scale="millions",
            legend=False,
            direct_line_labels=True,
            ylabel=f"{reporting_type.capitalize()} (millions USD)",
            export_data=data['dataframe'],
        )



    def get_current_fy(self):
        """
        Get the current fiscal year for mission spending data.

        Returns:
            int: Current fiscal year (e.g., 2024)
        """
        # The US federal fiscal year starts in October, so if the current month is October or later,
        # the fiscal year is the next calendar year.
        if datetime.today().month >= 10:
            return datetime.today().year + 1
        else:
            return datetime.today().year

    def _read_csv(self,file_name: str):
        """
        Load data from CSV file and return as dict for YAML processing.

        Args:
            file_name: Name of the CSV file to load (within the csv_path directory)

        Returns:
            dict: pandas DataFrame of csv data

        Raises:
            ValueError: If csv_path is not provided
            RuntimeError: If CSV file cannot be read
        """
        if not self.csv_path:
            raise ValueError("csv_path must be provided to load CSV data")

        try:
            df = pd.read_csv(file_name)
            logger.info(f"Loaded CSV data from {file_name} ({len(df)} rows, {len(df.columns)} columns)")
            return df
        except Exception as e:
            raise RuntimeError(f"Error reading CSV file {self.csv_path}: {e}")

    def get_data_summary(self,file_name: str) -> dict:
        """
        Get a summary of the loaded data for debugging purposes.

        Returns:
            dict: Summary information about the loaded data
        """
        if not self.csv_path:
            return {"error": "No CSV path specified"}

        try:
            df = pd.read_csv(file_name)
            return {
                "file_path": file_name,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict('records')
            }
        except Exception as e:
            return {"error": f"Could not analyze CSV file: {e}"}