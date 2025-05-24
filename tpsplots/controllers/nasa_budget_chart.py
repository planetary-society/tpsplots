"""Concrete NASA budget charts using specialized chart views."""
from datetime import datetime
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Historical, Directorates, ScienceDivisions, Science
import pandas as pd

import logging

logger = logging.getLogger(__name__)

class NASABudgetChart(ChartController):
    """Controller for top-line NASA budget charts."""

    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Historical(),  # Historical NASA budget data source
        )

    def nasa_budget_pbr_appropriation_by_year_inflation_adjusted(self):
        """Generate historical NASA budget chart with PBR and Appropriations."""
        self.data_source = Historical()  # Reset data source to Historical for this chart
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "PBR", "Appropriation", "PBR_adjusted_nnsi","Appropriation_adjusted_nnsi"])

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_rounded_axis_limit_y(df["PBR"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "The President's budget proposal sets the tone",
            "subtitle": "Except in the aftermath of Challenger, Congress has never exceeded a NASA budget proposal by more than 9%.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_pbr_appropriation_by_year",
            x=fiscal_years,
            y=[df["PBR"], df["Appropriation"]],
            color=["#3696CE", line_view.COLORS["blue"]],
            linestyle=[":", "-"],
            label=["NASA Budget Request", "Congressional Appropriation"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim=(0, y_limit),
            scale="billions",
            legend={"loc":"lower right"},
            export_data=export_df,
        )

    def nasa_budget_by_year_with_projection_inflation_adjusted(self):
        """Generate historical NASA budget chart with single appropriation line."""
        self.data_source = Historical()  # Reset data source to Historical for this chart
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "Appropriation", "White House Budget Projection", "Appropriation_adjusted_nnsi"])

        # Remove "White House Budget Proposal" values where "Appropriation" is present, for clarity
        export_df.loc[df["Appropriation"].notna(), "White House Budget Projection"] = pd.NA

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year,10,True)
        y_limit = self._get_rounded_axis_limit_y(df["Appropriation_adjusted_nnsi"].max(), 5000000000)
        
        # Prepare metadata
        metadata = {
            "title": "How NASA's budget has changed over time",
            "subtitle": "After its peak during Apollo, NASA's inflation-adjusted budget has held relatively steady, though that may change.",
            "source": f"NASA Budget Justifications, FYs 1961-{fiscal_years.max():%Y}",
        }
        
        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="nasa_budget_by_year_with_projection_inflation_adjusted",
            x=fiscal_years,
            y=[df["Appropriation_adjusted_nnsi"],df["White House Budget Projection"]],
            color=[line_view.COLORS["blue"], line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-","-"],
            marker=["","o"],
            label=["","Proposed"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim={"bottom":0, "top":y_limit},
            scale="billions",
            legend={"loc":"lower right"},
            export_data=export_df,
        )

    def nasa_budget_by_presidential_administration(self):
        """Generate NASA budget by presidential administration chart."""
        self.data_source = Historical()  # Reset data source to Historical for this chart
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
        """Line chart of NASA's directorate budgets from 2007 until the last fiscal year."""
        self.data_source = Directorates()
        df = self.data_source.data().dropna(subset=["Science"])  # Drop rows without directorate data
        
        # Calculate the last fiscal year
        last_completed_fy = datetime(datetime.today().year - 1, 1, 1)
        
        # Filter out df to only include years up to the last completed fiscal year
        df = df[df["Fiscal Year"] <= last_completed_fy]
        
        # Prepare data for view
        fiscal_years = df["Fiscal Year"]
        
        y_limit = (df["Deep Space Exploration Systems_adjusted_nnsi"].max() // 5000000000 + 1) * 5000000000
        
        y_data = [df["Deep Space Exploration Systems_adjusted_nnsi"], df["Science_adjusted_nnsi"],
                  df["Aeronautics_adjusted_nnsi"], df["Space Technology_adjusted_nnsi"], df["STEM Education_adjusted_nnsi"],
                  df["LEO Space Operations_adjusted_nnsi"], df["Facilities, IT, & Salaries_adjusted_nnsi"]
                  ]
        labels = ["Deep Space Exploration Systems", "Science Mission Directorate",
                  "Aeronautics", "Space Technology", "STEM Education",
                  "LEO Space Operations", "SSMS/CECR (Overhead)"]
        
        # Export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "Deep Space Exploration Systems", "Deep Space Exploration Systems_adjusted_nnsi",
                                            "Science", "Science_adjusted_nnsi", "Aeronautics", "Aeronautics_adjusted_nnsi",
                                            "Space Technology", "Space Technology_adjusted_nnsi",
                                            "STEM Education", "STEM Education_adjusted_nnsi",
                                            "LEO Space Operations", "LEO Space Operations_adjusted_nnsi",
                                            "Facilities, IT, & Salaries", "Facilities, IT, & Salaries_adjusted_nnsi"])
    
        
        # Prepare metadata
        metadata = {
            "title": "NASA directorates can have diverging fortunes",
            "subtitle": "Each major activity gets its own budget from Congress, and they don't always grow together.",
            "source": f"NASA Budget Justifications, FYs 2007-{fiscal_years.max():%Y}",
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
            xlim=(datetime(2008,1,1), fiscal_years.max()),
            ylim=(0, y_limit),
            fiscal_year_ticks=True,
            tick_rotation=0,
            scale="billions",
            legend={
                'loc': 'upper right',
                'fontsize': "medium",  # Readable size
                'ncol': 3,
                'handlelength': .8
            },
            export_data=export_df
        )
    
    def nasa_major_activites_donut_chart(self):
        """ Generate donut chart breakdown of NASA directorate budgets for the last fiscal year."""
        self.data_source = Directorates()
        donut_view = self.get_view("Donut")
        
        # Get data
        df = self.data_source.data()
        
        # Calculate the last fiscal year
        last_completed_fy = datetime(datetime.today().year - 1, 1, 1)
        
        # Filter to just that fiscal year
        # First convert the Fiscal Year column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"]):
            df["Fiscal Year"] = pd.to_datetime(df["Fiscal Year"])
        
        # Filter the DataFrame to the last completed fiscal year
        year_df = df[df["Fiscal Year"].dt.year == last_completed_fy.year]
        
        # Check if we have data for the last completed fiscal year
        if year_df.empty:
            # Fall back to the most recent available year
            latest_available_year = df["Fiscal Year"].max()
            year_df = df[df["Fiscal Year"] == latest_available_year]
            
            # Provide a warning in the logs
            logger.warning(f"No data found for FY {last_completed_fy.year}, falling back to {latest_available_year:%Y}")
        
        # Select only monetary columns (not fiscal year or adjusted columns)
        labels = ["Science", "Aeronautics", "Deep Space Exploration Systems", "LEO Space Operations",
                  "Space Technology", "Facilities, IT, & Salaries"]
        
        # Extract values from the single row
        directorates_df = year_df[labels]
        
        values = directorates_df.iloc[0].tolist()
        
        # Sort values labels
        sorted_data = list(zip(values, labels))
        sorted_values, sorted_labels = zip(*sorted_data)
        
        # Create export dataframe
        export_data = []
        for label, value in zip(sorted_labels, sorted_values):
            export_data.append({
                "Directorate": label, 
                f"FY {last_completed_fy.year} Budget ($)": value
            })
        export_data.append({
                "Directorate": "STEM Education", 
                f"FY {last_completed_fy.year} Budget ($)": year_df["STEM Education"].values[0]
            }) # Add STEM Education back to export
        export_df = pd.DataFrame(export_data)
 
        # Prepare metadata
        metadata = {
            "title": "NASA's budget is subdivided by mission area",
            "subtitle": "Directorates are responsible for distinct activities — from science to facilities — and they don't share funding.",
            "source": f"FY {last_completed_fy:%Y} Congressional Appropriations",
        }
        
        # Generate the donut chart
        donut_view.donut_plot(
            metadata=metadata,
            stem="nasa_directorate_breakdown_donut_chart",
            values=sorted_values,
            labels=sorted_labels,
            show_percentages=True,
            label_distance=1.1,
            hole_size=0.6,
            center_text="NASA",
            center_color="white",
            export_data=export_df
        )
    
    def generate_charts(self):
        """Generate every chart in the class."""
        self.nasa_budget_pbr_appropriation_by_year_inflation_adjusted()
        self.nasa_major_programs_by_year_inflation_adjusted()
        self.nasa_major_activites_donut_chart()
        self.nasa_budget_by_year_with_projection_inflation_adjusted()
        #self.nasa_budget_by_presidential_administration()
