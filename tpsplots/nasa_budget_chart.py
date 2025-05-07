"""Concrete NASA budget charts."""
from pathlib import Path
from chart_controller import ChartController
from data_sources.nasa_budget_data_source import Historical

class NASABudgetChart(ChartController):
    """Controller for NASA budget charts."""

    def __init__(self):
        # Initialize with data source and output directory
        super().__init__(
            data_source=Historical(), # Historical NASA budget data source
            outdir=Path("charts") / "nasa_budget"
        )

    def generate_charts(self):
        """Generate all NASA budget charts."""
        self.nasa_historical_appropriation_pbr_inflation_adjusted()
        self.nasa_by_presidential_administration()
    
    def nasa_historical_appropriation_pbr_inflation_adjusted(self):
        """Generate historical NASA budget chart."""
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        x_data = df["Fiscal Year"].astype(int)  # Convert to int for x-axis
        y_data_list = [
            df["PBR_adjusted_nnsi"],
            df["Appropriation_adjusted_nnsi"]
        ]
        
        # Determine the closest year in the future that is a multiple of 5 and greater
        # than the last year in the data to use as the x-axis limit
        x_limit = (int(x_data.max()) // 5 + 1) * 5
        y_limit = (df["PBR_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        # Prepare metadata
        metadata = {
            "labels": ["Presidential Budget Request", "Congressional Appropriation"],
            "colors": [self.view.COLORS["light_blue"], self.view.COLORS["blue"]],
            "formats": ["--", "-"],
            "scale": "billions",
            "source": f"NASA Budget Justifications, FYs 1961-{x_data.max()}",
            "mpl_args": {
                "axes": {
                    "xlim": (1958, x_limit),
                    "ylim": (0, y_limit),
                },
            }
        }
        
        # Generate charts via view
        self.view.line_plot(x_data, y_data_list, metadata, "nasa_pbr_by_year")

    def nasa_by_presidential_administration(self):
        """Generate NASA budget by presidential administration chart."""
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        presidents = df["Presidential Administration"].unique()
        
        for president in presidents:
            df_president = df[df["Presidential Administration"] == president]
            x_data = df_president["Fiscal Year"].astype(int)
            y_data_list = [
                df_president["PBR_adjusted_nnsi"],
                df_president["Appropriation_adjusted_nnsi"]
            ]
            
            y_limit = (df_president["PBR_adjusted_nnsi"].max() // 10000000000 + 1) * 10000000000
            
            # Prepare metadata
            metadata = {
                "title": f"NASA budget during the {president} administration",
                "labels": ["Presidential Budget Request", "Congressional Appropriation"],
                "colors": [self.view.COLORS["light_blue"], self.view.COLORS["blue"]],
                "source": f"NASA Budget Justifications, FYs {x_data.min()}-{x_data.max()+2}",
                "formats": ["--", "-"],
                "scale": "billions",
                "mpl_args": {
                    "axes": {
                        "xlim": (x_data.min(), x_data.max()),
                        "ylim": (1e-10, y_limit),
                        "custom_xticks": True,  # Enable custom x-ticks
                        "xticks": x_data,       # Use the actual years as ticks
                        "hide_y_zero": True
                    },
                    "max_xticks": (x_data.max() - x_data.min() + 1)
                }
            }
        
            # Generate charts via view
            self.view.line_plot(x_data, y_data_list, metadata, f"{president}_nasa_budget")

        
if __name__ == "__main__":
    # Create and use the chart controller
    chart = NASABudgetChart()
    #chart.nasa_by_presidential_administration()
    chart.generate_charts()
    print("All done.")