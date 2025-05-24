"""Concrete NASA budget charts using specialized chart views."""
from pathlib import Path
from datetime import datetime
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.views import LineChartView, WaffleChartView  # Import specialized views
from tpsplots.data_sources.nasa_budget_data_source import Historical, Directorates, ScienceDivisions, Science
from matplotlib import pyplot as plt
import pandas as pd

class FY2026Charts(ChartController):
    
    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Science(),  # Historical NASA budget data source
        )
    def nasa_budget_historical_with_fy_2026_proposed(self):
        """Generate historical NASA budget chart with single appropriation line."""
        self.data_source = Historical()
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Limit fiscal years to those through FY 2025
        fiscal_years = df[df["Fiscal Year"] <= pd.to_datetime("2026-01-01")]["Fiscal Year"]
        
        # Copy Appropriation value for 2025-01-01 to the White House Budget Projection for 2025-01-01
        df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "White House Budget Projection"] = df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "Appropriation"]
        
        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "Appropriation", "White House Budget Projection","Appropriation_adjusted_nnsi"])

        # Remove "White House Budget Proposal" values where "Appropriation" is present, for clarity
        export_df.loc[df["Appropriation"].notna(), "White House Budget Projection"] = pd.NA

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_rounded_axis_limit_y(df["Appropriation_adjusted_nnsi"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "The largest cut to NASA ever proposed",
            "subtitle": "The White House proposed a 24% cut in 2026, the smallest budget requested since 1961, when adjusted for inflation.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_historical_inflation_adjusted_fy2026_threat",
            x=fiscal_years,
            y=[df["Appropriation_adjusted_nnsi"],df["White House Budget Projection"]],
            color=[line_view.COLORS["blue"], line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-","-"],
            marker=["","o"],
            label=["","2026 White House proposal"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim={"bottom":0, "top":y_limit},
            scale="billions",
            legend={"loc":"lower right"},
            export_data=export_df,
        )
        
    def nasa_science_by_year_inflation_adjusted_fy2026_threat(self):
        """Generate historical NASA Science budget chart."""
        # Get data from model
        self.data_source = Science()
        df = self.data_source.data()  # Drop rows without directorate data

        # Prepare data for view
        # Only grab years through FY 2025
        fiscal_years = df[df["Fiscal Year"] <= pd.to_datetime("2026-01-01")]["Fiscal Year"]
        
        # Prepare cleaned data for export
        export_df = self._export_helper(df, ["Fiscal Year", "NASA Science", "NASA Science_adjusted_nnsi", "FY 2026 PBR"])
        
        x_limit = 2030
        y_limit = self._get_rounded_axis_limit_y(df["NASA Science_adjusted_nnsi"].max(), 5_000_000_000)
        
        # Prepare metadata
        metadata = {
            "title": "The biggest science cut in NASA history",
            "subtitle": "The proposed 47% reduction would result in the smallest science budget since 1984, when adjusted for inflation.",
            "source": f"NASA Budget Justifications, FYs 1980-{fiscal_years.max():%Y}",
        }
        
        # Plot as line chart
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_science_by_year_inflation_adjusted_fy2026_threat",
            x=fiscal_years,
            y=[df["NASA Science_adjusted_nnsi"], df["FY 2026 PBR"]],
            color=[line_view.COLORS["blue"], line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-", "-"],
            marker=["", "o"],
            label=["NASA science funding", "2026 White House proposal"],
            xlim=(datetime(1980,1,1), datetime(x_limit,1,1)),
            ylim=(0, y_limit),
            scale="billions",
            legend={"loc":"lower right"},
            export_data=export_df
        )
    
    def generate_charts(self):
        self.nasa_science_by_year_inflation_adjusted_fy2026_threat()