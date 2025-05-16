"""Concrete NASA budget charts."""
from pathlib import Path
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.views.subplot_view import SubplotView
from tpsplots.data_sources.nasa_budget_data_source import Historical, Directorates, ScienceDivisions
from matplotlib import pyplot as plt

class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def __init__(self):
        # Initialize with data source and output directory
        super().__init__(
            data_source=Historical(), # Historical NASA budget data source
            outdir=Path("charts") / "nasa_budget"
        )

    def generate_charts(self):
        """Generate all NASA budget charts."""
        self.nasa_budget_by_year_inflation_adjusted()
        self.nasa_by_presidential_administration()
    
    def nasa_budget_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart."""
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"].astype(int)  # Convert to int for x-axis
        
        # Determine the closest year in the future that is a multiple of 5 and greater
        # than the last year in the data to use as the x-axis limit
        x_limit = (fiscal_years.max() // 5 + 1) * 5
        y_limit = (df["PBR_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        # Prepare metadata
        metadata = {
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max()}",
        }
        
        # Generate charts via view
        self.view.line_plot(
            metadata=metadata,
            stem="nasa_budget_by_year_inflation_adjusted",
            x=fiscal_years,
            y=[df["PBR_adjusted_nnsi"], df["Appropriation_adjusted_nnsi"]],
            color=["#3696CE", self.view.COLORS["blue"]],
            linestyle=["--", "-"],
            label=["Presidential Budget Request", "Congressional Appropriation"],
            xlim=(1958, x_limit),
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
            
            # Generate charts via view with direct kwargs
            self.view.line_plot(
                metadata=metadata,
                stem=f"{president}_nasa_budget_inflation_adjusted",
                x=fiscal_years,
                y=[df_president["PBR_adjusted_nnsi"], df_president["Appropriation_adjusted_nnsi"]],
                color=[self.view.COLORS["light_blue"], self.view.COLORS["blue"]],
                linestyle=["--", "-"],
                label=["Presidential Request", "Congressional Appropriation"],
                xlim=(fiscal_years.min(), fiscal_years.max()),
                ylim=(1e-10, y_limit),
                scale="billions",
                xticks=fiscal_years,
                max_xticks=(fiscal_years.max() - fiscal_years.min() + 1)
            )

    def nasa_major_programs_by_year_inflation_adjusted(self):
        """ Line chart of NASA's directorate budgets from 2007 onwards."""
        self.data_source = Directorates()
        df = self.data_source.data().dropna(subset=["Science"]) # Drop rows without directorate data
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        y_limit = (df["Deep Space Exploration Systems_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        y_data = [df["Deep Space Exploration Systems_adjusted_nnsi"],df["Science_adjusted_nnsi"],
                  df["Aeronautics_adjusted_nnsi"], df["Space Technology_adjusted_nnsi"], df["STEM Education_adjusted_nnsi"],
                  df["LEO Space Operations_adjusted_nnsi"], df["Infrastructure/Overhead_adjusted_nnsi"]
                  ]
        labels = ["Deep Space Exploration Systems","Science Mission Directorate",
                  "Aeronautics", "Space Technology", "STEM Education",
                  "LEO Space Operations", "SSMS/CECR (Overhead)"]
        # Prepare metadata
        metadata = {
            "source": f"NASA Budget Justifications, FYs 2007-{fiscal_years.max()}",
        }
        
        # Generate charts via view
        self.view.line_plot(
            metadata=metadata,
            stem="nasa_major_programs_by_year_inflation_adjusted",
            x=fiscal_years,
            y=y_data,
            linestyle=["-"],
            label=labels,
            xlim=("2008", fiscal_years.max()),
            ylim=(1e-10, y_limit),
            scale="billions",
            legend={
                'loc': 'upper right',
                'ncol': 2,
                'handlelength': .8
            },
        )
    
    def nasa_science_divisions_by_year_inflation_adjusted(self):
        self.data_source = ScienceDivisions()
        self.view = SubplotView(outdir=Path("charts") / "science_divisions")
        df = self.data_source.data().dropna(subset=["Fiscal Year"]) # Drop rows without fiscal year data
        fiscal_years = df["Fiscal Year"]
        print(df)
        y_limit = (df["Planetary Science_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000



        plt.style.use(TPS_STYLE_FILE)
        plt.subplot(221)
        plt.plot( 'Fiscal Year', 'Planetary Science_adjusted_nnsi', data=df, linestyle='-')
        plt.subplot(222)
        plt.plot( 'Fiscal Year','Astrophysics_adjusted_nnsi', data=df, linestyle='-')
        plt.subplot(223)
        plt.plot( 'Fiscal Year','Earth Science_adjusted_nnsi', data=df, linestyle='-')
        plt.subplot(224)
        plt.plot( 'Fiscal Year','Heliophysics_adjusted_nnsi', data=df, linestyle='-')
        #plt.show()
        self.view.quadrants()


    def nasa_directorate_budget_waffle_chart(self):
        """ Generate NASA budget breakdown by directorate as a waffle chart."""
        self.data_source = Directorates()
        df = self.data_source.data().dropna(subset=["Science"]) # Drop rows without directorate data
        
        available_years = sorted(df["Fiscal Year"].unique())
        prior_fy = available_years[-2]
        
        # Convert the row where Fiscal Year is 2025 into a dictionary
        nasa_directorates = df[df["Fiscal Year"] == prior_fy].iloc[0].drop(
            labels=["Fiscal Year"] + [col for col in df.columns if "adjusted" in col]
        ).to_dict()
        
        # Define block value - each block represents $100M
        block_value = 50000000

        # Scale values to represent blocks ($50M each)
        scaled_directorates = {k: round(v / block_value) for k, v in nasa_directorates.items()}
        
        # Order directorates so largest values are first
        sorted_directorates = dict(sorted(scaled_directorates.items(), key=lambda item: item[1], reverse=True))

        # Calculate relative percentages for labels and sort from largest to smallest
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
            self.view.TPS_COLORS["Neptune Blue"],     # Strong blue for largest category
            self.view.TPS_COLORS["Plasma Purple"],    # Rich purple for contrast
            self.view.TPS_COLORS["Medium Neptune"],   # Lighter blue
            self.view.TPS_COLORS["Rocket Flame"],     # Warm orange-red
            self.view.TPS_COLORS["Medium Plasma"],    # Softer purple
            self.view.TPS_COLORS["Lunar Soil"],       # Neutral gray
            self.view.TPS_COLORS["Light Neptune"]     # Very light blue for smallest category
        ]
        
        self.view.waffle_chart(
            values=sorted_directorates,
            labels=repartition, 
            colors=category_colors,
            vertical=True,
            metadata=metadata,
            interval_ratio_x=0.11,
            interval_ratio_y=0.11,
            legend={
                'loc': 'lower left',
                'frameon': False,  # No border
                'bbox_to_anchor': (0, -0.10),
                'fontsize': "medium",  # Readable size
                'ncol': 4,
                'handlelength': .8
            },
            stem="nasa_directorate_breakdown"
        )
        
if __name__ == "__main__":
    # Create and use the chart controller
    chart = NASABudgetChart()
    #chart.nasa_budget_by_year_inflation_adjusted()
    #chart.nasa_by_presidential_administration()
    #chart.nasa_major_programs_by_year_inflation_adjusted()
    #chart.nasa_directorate_breakdown()
    chart.nasa_science_divisions_by_year_inflation_adjusted()
    print("All done.")