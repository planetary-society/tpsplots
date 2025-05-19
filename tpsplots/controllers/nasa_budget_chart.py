"""Concrete NASA budget charts using specialized chart views."""
from pathlib import Path
from datetime import datetime
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.views import LineChartView, WaffleChartView  # Import specialized views
from tpsplots.data_sources.nasa_budget_data_source import Historical, Directorates, ScienceDivisions, Science
from matplotlib import pyplot as plt

class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Historical(),  # Historical NASA budget data source
            outdir=Path("charts") / "nasa_budget"
        )
        
        # Initialize specialized chart views
        self.line_view = LineChartView(self.outdir, TPS_STYLE_FILE)
        waffle_view = WaffleChartView(self.outdir, TPS_STYLE_FILE)

    def generate_charts(self):
        """Generate all NASA budget charts."""
        self.nasa_budget_by_year_inflation_adjusted()
        self.nasa_directorate_budget_waffle_chart()
        self.nasa_major_programs_by_year_inflation_adjusted()
        self.nasa_science_by_year_inflation_adjusted()
    
    def nasa_budget_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart."""
        
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_axis_limit_y(df["PBR_adjusted_nnsi"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "NASA Budget History (Inflation-Adjusted)",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max()}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_by_year_inflation_adjusted",
            x=fiscal_years,
            y=[df["PBR_adjusted_nnsi"], df["Appropriation_adjusted_nnsi"]],
            color=["#3696CE", self.line_view.COLORS["blue"]],
            linestyle=["--", "-"],
            label=["Presidential Budget Request", "Congressional Appropriation"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim=(0, y_limit),
            scale="billions"
        )

    def nasa_science_by_year_inflation_adjusted(self):
        """Generate historical NASA Science budget chart."""
        # Get data from model
        self.data_source = Science()
        df = self.data_source.data()  # Drop rows without directorate data

        # Prepare data for view
        fiscal_years = df["Fiscal Year"].astype(int)  # Convert to int for x-axis
        
        # Determine the closest year in the future that is a multiple of 5
        x_limit = (fiscal_years.max() // 5 + 1) * 5
        y_limit = (df["NASA Science_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        # Prepare metadata
        metadata = {
            "title": "NASA Science faces an existential threat",
            "source": f"NASA Budget Justifications, FYs 1980-{fiscal_years.max()}",
        }
        
        # Plot as line chart
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_science_by_year_inflation_adjusted",
            x=fiscal_years,
            y=[df["NASA Science_adjusted_nnsi"], df["FY 2026 PBR"]],
            color=[self.line_view.COLORS["blue"], self.line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-", "--"],
            label=["NASA Science", "FY2026 Presidential Request"],
            xlim=(1980, x_limit),
            ylim=(0, y_limit),
            scale="billions"
        )

    def nasa_budget_by_presidential_administration(self):
        """Generate NASA budget by presidential administration chart."""
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        presidents = df["Presidential Administration"].unique()
        
        for president in presidents:
            df_president = df[df["Presidential Administration"] == president]
            fiscal_years = df_president["Fiscal Year"].astype(int)
            
            y_limit = (df_president["PBR_adjusted_nnsi"].max() // 10000000000 + 1) * 10000000000
            
            # Prepare metadata
            metadata = {
                "title": f"NASA budget during the {president} administration",
                "source": f"NASA Budget Justifications, FYs {fiscal_years.min()}-{fiscal_years.max()+2}"
            }
            
            # Plot as line chart
            line_view = self.get_view('Line')
            
            # Generate charts via the specialized line chart view
            line_view.line_plot(
                metadata=metadata,
                stem=f"{president}_nasa_budget_inflation_adjusted",
                x=fiscal_years,
                y=[df_president["PBR_adjusted_nnsi"], df_president["Appropriation_adjusted_nnsi"]],
                color=[self.line_view.COLORS["light_blue"], self.line_view.COLORS["blue"]],
                linestyle=["--", "-"],
                label=["Presidential Request", "Congressional Appropriation"],
                xlim=(fiscal_years.min(), fiscal_years.max()),
                ylim=(1e-10, y_limit),
                scale="billions",
                xticks=fiscal_years,
                max_xticks=(fiscal_years.max() - fiscal_years.min() + 1)
            )

    def nasa_major_programs_by_year_inflation_adjusted(self):
        """Line chart of NASA's directorate budgets from 2007 onwards."""
        self.data_source = Directorates()
        df = self.data_source.data().dropna(subset=["Science"])  # Drop rows without directorate data
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"].astype(int)
        
        y_limit = (df["Deep Space Exploration Systems_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        y_data = [df["Deep Space Exploration Systems_adjusted_nnsi"], df["Science_adjusted_nnsi"],
                  df["Aeronautics_adjusted_nnsi"], df["Space Technology_adjusted_nnsi"], df["STEM Education_adjusted_nnsi"],
                  df["LEO Space Operations_adjusted_nnsi"], df["Infrastructure/Overhead_adjusted_nnsi"]
                  ]
        labels = ["Deep Space Exploration Systems", "Science Mission Directorate",
                  "Aeronautics", "Space Technology", "STEM Education",
                  "LEO Space Operations", "SSMS/CECR (Overhead)"]
        # Prepare metadata
        metadata = {
            "title": "NASA Program Areas (Inflation-Adjusted)",
            "source": f"NASA Budget Justifications, FYs 2007-{fiscal_years.max()}",
        }
        # Generate charts via the specialized line chart view
        line_view = self.get_view('Line')
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_major_programs_by_year_inflation_adjusted",
            x=fiscal_years,
            y=y_data,
            linestyle="-",
            label=labels,
            xlim=(2008, max(fiscal_years)),
            ylim=(1e-10, y_limit),
            scale="billions",
            legend={
                'loc': 'upper right',
                'ncol': 2,
                'handlelength': .8
            },
        )
        
    def nasa_directorate_budget_waffle_chart(self):
        """Generate NASA budget breakdown by directorate as a waffle chart."""
        
        # Load View for Waffle Charts
        waffle_view = self.get_view('Waffle')
        
        self.data_source = Directorates()
        df = self.data_source.data().dropna(subset=["Science"])  # Drop rows without directorate data
        
        available_years = sorted(df["Fiscal Year"].unique())
        prior_fy = available_years[-2]
        
        # Convert the row where Fiscal Year is the prior FY into a dictionary
        nasa_directorates = df[df["Fiscal Year"] == prior_fy].iloc[0].drop(
            labels=["Fiscal Year"] + [col for col in df.columns if "adjusted" in col]
        ).to_dict()
        
        # Define block value - each block represents $50M
        block_value = 50000000

        # Scale values to represent blocks ($50M each)
        scaled_directorates = {k: round(v / block_value) for k, v in nasa_directorates.items()}
        
        # Order directorates so largest values are first
        sorted_directorates = dict(sorted(scaled_directorates.items(), key=lambda item: item[1], reverse=True))

        # Calculate relative percentages for labels
        repartition = [
            f"{k} ({v / sum(nasa_directorates.values()) * 100:.1f}%)" if v / sum(nasa_directorates.values()) * 100 < 1 
            else f"{k} ({int(v / sum(nasa_directorates.values()) * 100)}%)" 
            for k, v in sorted(nasa_directorates.items(), key=lambda item: item[1], reverse=True)
        ]

        # Add block value explanation to the title or subtitle
        metadata = {
            "title": f"NASA Budget by Directorate, FY {prior_fy}",
            "subtitle": "Each block represents $50 million",
            "source": f"FY{prior_fy} NASA Budget Justification",
        }
        
        category_colors = [
            waffle_view.TPS_COLORS["Neptune Blue"],     # Strong blue for largest category
            waffle_view.TPS_COLORS["Plasma Purple"],    # Rich purple for contrast
            waffle_view.TPS_COLORS["Medium Neptune"],   # Lighter blue
            waffle_view.TPS_COLORS["Rocket Flame"],     # Warm orange-red
            waffle_view.TPS_COLORS["Medium Plasma"],    # Softer purple
            waffle_view.TPS_COLORS["Lunar Soil"],       # Neutral gray
            waffle_view.TPS_COLORS["Light Neptune"]     # Very light blue for smallest category
        ]
        
        waffle_view.waffle_chart(
            metadata=metadata,
            stem="nasa_directorate_breakdown",
            values=sorted_directorates,
            labels=repartition, 
            colors=category_colors,
            vertical=True,
            interval_ratio_x=0.11,
            interval_ratio_y=0.11,
            legend={
                'loc': 'lower left',
                'frameon': False,  # No border
                'bbox_to_anchor': (0, -0.10),
                'fontsize': "medium",  # Readable size
                'ncol': 4,
                'handlelength': .8
            }
        )