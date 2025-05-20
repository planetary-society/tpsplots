"""Concrete NASA budget charts using specialized chart views."""
from pathlib import Path
from datetime import datetime
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.views import LineChartView, WaffleChartView  # Import specialized views
from tpsplots.data_sources.nasa_budget_data_source import Historical, Directorates, ScienceDivisions, Science
from matplotlib import pyplot as plt
import pandas as pd

class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Historical(),  # Historical NASA budget data source
        )

    def nasa_budget_pbr_appropriation_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart with PBR and Appropriations."""
        
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "PBR", "Appropriation", "PBR_adjusted_nnsi","Appropriation_adjusted_nnsi"])

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_rounded_axis_limit_y(df["PBR_adjusted_nnsi"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "Presidential funding levels for NASA are mostly met by Congress",
            "subtitle": "Except in the aftermath of Challenger, Congress has never exceeded a proposal by more than 10%.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_pbr_appropriation_by_year_inflation_adjusted",
            x=fiscal_years,
            y=[df["PBR_adjusted_nnsi"], df["Appropriation_adjusted_nnsi"]],
            color=["#3696CE", line_view.COLORS["blue"]],
            linestyle=[":", "-"],
            label=["Presidential Budget Request", "Congressional Appropriation"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim=(0, y_limit),
            scale="billions",
            export_data=export_df,
        )

    def nasa_budget_appropriation_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart with single appropriation line."""
        
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "Appropriation", "Appropriation_adjusted_nnsi"])

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_rounded_axis_limit_y(df["Appropriation_adjusted_nnsi"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "How NASA's budget has changed over time",
            "subtitle": "After peaking during Project Apollo, NASA's inflation-adjusted budget has held mostly steady for decades.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_appropriation_by_year_inflation_adjusted",
            x=fiscal_years,
            y=df["Appropriation_adjusted_nnsi"],
            color=line_view.COLORS["blue"],
            linestyle="-",
            label="Congressional Appropriation",
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim=(0, y_limit),
            scale="billions",
            export_data=export_df,
        )

    def nasa_budget_by_presidential_administration(self):
        """Generate NASA budget by presidential administration chart."""
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        presidents = df["Presidential Administration"].unique()
        i = 0
        
        # Plot as line chart
        line_view = self.get_view('Line')
        
        for president in presidents:
            df_president = df[df["Presidential Administration"] == president]
            fiscal_years = df_president["Fiscal Year"]
            
            if len(fiscal_years) < 3:
                continue
            
            export_df = self._export_helper(df_president,["Fiscal Year","PBR","Appropriation", "PBR_adjusted_nnsi","Appropriation_adjusted_nnsi"])
            
            y_limit = self._get_rounded_axis_limit_y(df_president["PBR_adjusted_nnsi"].max(),20e9)
            
            first_value = df_president["Appropriation_adjusted_nnsi"].iloc[0]
            last_value = df_president["Appropriation_adjusted_nnsi"].iloc[-1]
            
            # Calculate change during administration tenure
            change = last_value - first_value
            change_percentage = round((change)/first_value * 100)
            
            # Name corrections
            if president == "Trump I":
                president = "first Trump"
            elif president == "W. Bush":
                president = "George W. Bush"
            
            if change > 0:
                 # Make the overall value positive for display only
                change_str = self.round_to_millions(change)
                if change_str[0] == "-":
                    change_str = change_str[1:]
                subtitle = f"NASA grew by {change_str} ({change_percentage}%) this period."
            else:
                subtitle = f"NASA shrank by {change_str} ({change_percentage}%) this period."
            
            # Prepare metadata
            metadata = {
                "title": f"NASA's budget during the {president} administration",
                "subtitle": subtitle,
                "source": f"NASA Budget Justifications, FYs {fiscal_years.min():%Y}-{fiscal_years.max():%Y}"
            }

            # Generate charts via the specialized line chart view
            line_view.line_plot(
                metadata=metadata,
                stem=f"{president}_nasa_budget_inflation_adjusted",
                x=fiscal_years,
                y=[df_president["PBR_adjusted_nnsi"], df_president["Appropriation_adjusted_nnsi"]],
                color=["#3696CE", line_view.COLORS["blue"]],
                linestyle=[":", "-"],
                label=["Presidential Request", "Congressional Appropriation"],
                xlim=(fiscal_years.min(), fiscal_years.max()),
                ylim=(0, y_limit),
                scale="billions",
                fiscal_year_ticks = False,
                max_xticks=(len(fiscal_years) + 1),
                export_data=export_df
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
    
    def generate_charts(self):
        """Generate all NASA budget charts."""
        self.nasa_budget_pbr_appropriation_by_year_inflation_adjusted()
        self.nasa_directorate_budget_waffle_chart()
        self.nasa_major_programs_by_year_inflation_adjusted()
        self.nasa_science_by_year_inflation_adjusted()
    