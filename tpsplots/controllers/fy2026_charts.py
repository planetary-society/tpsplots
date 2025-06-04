"""Concrete NASA budget charts using specialized chart views."""
from pathlib import Path
from datetime import datetime
import numpy as np
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Historical, ScienceDivisions, Science, Workforce
from tpsplots.data_sources.missions import Missions
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
            hlines=[18_800_000_000],
            hline_labels=["Lowest since 1961"],
            hline_label_position="center",
            hline_colors=[line_view.TPS_COLORS["Crater Shadow"]],
            hline_linestyle=["--"],
            hline_linewidth=[2]
        )
        
    def nasa_science_by_year_inflation_adjusted_fy2026_threat(self):
        """Generate historical NASA Science budget chart."""
        # Get data from model
        self.data_source = Science()
        df = self.data_source.data()  # Drop rows without directorate data

        # Prepare data for view
        # Only grab years through FY 2025
        fiscal_years = df[df["Fiscal Year"] < pd.to_datetime("2026-01-01")]["Fiscal Year"]
        
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
            export_data=export_df,
            hlines=[3_907_600_000],
            hline_labels=["Lowest since 1984"],
            hline_label_position="center",
            hline_colors=[line_view.TPS_COLORS["Crater Shadow"]],
            hline_linestyle=["--"],
            hline_linewidth=[2]
        )
    
    def nasa_science_divisions_quad_plot_fy2026_threat(self):
        """Generate quad plot showing NASA's four science divisions with historical and proposed budgets."""
        # Load ScienceDivisions data
        self.data_source = ScienceDivisions()
        df = self.data_source.data()
        
        # Filter data from 1990 to 2025
        df_filtered = df[
            (df["Fiscal Year"] >= pd.to_datetime("1990-01-01")) & 
            (df["Fiscal Year"] <= pd.to_datetime("2025-01-01"))
        ].copy()
        
        # Define the four science divisions
        divisions = ["Astrophysics", "Planetary Science", "Earth Science", "Heliophysics"]
        
        # For each division, set the 2025 proposed value to match the adjusted value
        # and set a placeholder for 2026
        for division in divisions:
            adjusted_col = f"{division}_adjusted_nnsi"
            proposed_col = f"{division} Proposed"
            
            # Find the 2025 row
            mask_2025 = df_filtered["Fiscal Year"] == pd.to_datetime("2025-01-01")
            if mask_2025.any():
                # Set 2025 proposed value to match adjusted value
                df_filtered.loc[mask_2025, proposed_col] = df_filtered.loc[mask_2025, adjusted_col].values[0]
        
        # Add a 2026 row with placeholder values if it doesn't exist
        if not (df_filtered["Fiscal Year"] == pd.to_datetime("2026-01-01")).any():
            # Create a new row for 2026
            new_row = pd.Series()
            new_row["Fiscal Year"] = pd.to_datetime("2026-01-01")
            
            # Set all division values to NaN except the proposed columns
            for division in divisions:
                new_row[division] = np.nan
                new_row[f"{division}_adjusted_nnsi"] = np.nan
                new_row[f"{division}_adjusted_gdp"] = np.nan
            
            
            new_row = {
                "Fiscal Year": pd.to_datetime("2026-01-01"),
                "Astrophysics Proposed": 523_000_000,
                "Planetary Science Proposed": 1_891_300_000,
                "Earth Science Proposed": 1_035_900_000,
                "Heliophysics Proposed": 432_500_000
                }
        
            # Append the new row
            df_filtered = pd.concat([df_filtered, pd.DataFrame([new_row])], ignore_index=True)
        
        # Sort by fiscal year to ensure proper ordering
        df_filtered = df_filtered.sort_values("Fiscal Year")
        
        # Prepare data for each subplot
        subplot_data = []
        colors = [self.get_view('Line').COLORS["blue"], self.get_view('Line').TPS_COLORS["Rocket Flame"]]
        
        for division in divisions:
            # Get fiscal years
            fiscal_years = df_filtered["Fiscal Year"]
            
            # Get adjusted values (historical data)
            adjusted_values = df_filtered[f"{division}_adjusted_nnsi"]
            
            # Get proposed values (only for 2025-2026)
            proposed_values = df_filtered[f"{division} Proposed"]
            
            subplot_data.append({
                'x': fiscal_years,
                'y': [adjusted_values, proposed_values],
                'title': division,
                'labels': ['Division funding', 'Proposed'],
                'colors': colors,
                'linestyles': ['-'],
                'markers': ['', 'o'],
                'linewidths': [3],
                'legend': True,
                'share_legent': True
            })
        
        # Calculate y-axis limit based on max value across all divisions
        max_value = 0
        for division in divisions:
            div_max = df_filtered[f"{division}_adjusted_nnsi"].max()
            if not pd.isna(div_max):
                max_value = max(max_value, div_max)
        
        y_limit = self._get_rounded_axis_limit_y(max_value, 1_000_000_000)  # Round to nearest billion
        
        # Prepare metadata
        metadata = {
            "title": "All NASA sciences face severe cuts in 2026",
            "subtitle": "The White House would slash each division from 30% to 65%, reducing some to historic lows when adjusted for inflation.",
            "source": "NASA Presidential Budget Requests, FYs 1990-2026",
        }
        
        # Prepare export data
        export_columns = ["Fiscal Year"]
        for division in divisions:
            export_columns.extend([
                division,
                f"{division}_adjusted_nnsi",
                f"{division} Proposed"
            ])
        export_df = self._export_helper(df_filtered, export_columns)
        
        # Get the LineSubplotsView
        subplots_view = self.get_view('LineSubplots')
        
        # Generate the quad plot
        subplots_view.line_subplots(
            metadata=metadata,
            stem="nasa_science_divisions_quad_plot_fy2026_threat",
            subplot_data=subplot_data,
            grid_shape=(2, 2),
            xlim=(pd.to_datetime("1990-01-01"), pd.to_datetime("2030-01-01")),
            ylim=(0, y_limit),
            scale="billions",
            shared_x=False,
            shared_y=False,
            shared_legend=True,
            legend=True,
            subplot_title_size=14,
            export_data=export_df
        )
    
    def cancelled_missions_lollipop_chart(self):
        data_source = Missions()
        df = data_source.data()
        
        # Add explicit cancellation date
        df["Cancellation Date"] = datetime(2026, 1, 1)
        
        df["Launch Year"] = df["Launch Date"].dt.year
        df["End Year"] = df["Cancellation Date"].dt.year
        # Safely extract year, accounting for NaT/NaN values
        df['Formulation Start Year'] = df["Formulation Start"].apply(lambda x: pd.to_datetime(x).year if pd.notnull(x) else pd.NA)
        
        # Calculate 'Duration (years)' only for valid rows
        df['Duration (years)'] = (df['End Year'] - df['Launch Year']).fillna(0)
        
        df['Development Time (years)'] = (df['Launch Year'] - df['Formulation Start Year']).fillna(0)
        
        # Filter by only NASA-led missions
        df = df[df["NASA Led?"].isin([True])]
        
        # Copy for use in 2nd chart
        df_dev = df.copy()
        
        # Filter to active missions led by NASA
        df = df[df["Status"].isin(["Prime Mission", "Extended Mission"])]
        
        total_development_time = round(df['Development Time (years)'].sum())
        total_value = self.round_to_millions(df['LCC'].sum())
        total_projects = len(df)
        
        # Rename every mission to just use the values if parentheses (if present)
        # If the mission name contains parentheses, extract the text inside; otherwise, keep the original name
        df["Mission"] = df["Mission"].str.extract(r"\(([^)]+)\)", expand=False).fillna(df["Mission"])
        
        
        # Prepare export data
        export_df = df.copy().drop(columns=["NASA Led?"])
        
        # Prepare metadata
        metadata = {
            "title": f"{total_projects} active science missions cancelled",
            "subtitle": f"These projects reflect more than {total_value} of investment by U.S. taxpayers and {total_development_time} of combined years to build.",
            "source": "FY 2026 White House NASA Request"
        }
        
        lollipop_view = self.get_view("Lollipop")
        
        # Generate the chart
        lollipop_view.lollipop_plot(
            metadata=metadata,
            stem="fy_2026_proposed_mission_cancellations",
            categories=df['Mission'],
            start_values=df['Launch Year'],
            end_values=df['End Year'],
            sort_by='start',  # Sort by start year
            sort_ascending=False,
            colors=lollipop_view.TPS_COLORS["Neptune Blue"],
            xlim=(1990, 2027),
            start_value_labels=True,
            xlabel=None,
            grid=True,
            y_axis_position='right',  # Category labels on the right
            hide_y_spine=True,
            grid_axis='x',
            tick_size=12,
            end_marker_style='X',
            end_marker_color='red',
            marker_size=11,
            value_labels=False,  # Don't show individual year labels
            range_labels=False,   # Show duration in years
            category_wrap_length=25,
            export_data=export_df
        )
        
        # Generate the 2nd chart of development missions
        
        # Prepare metadata
        metadata = {
            "title": f"{len(df_dev)} future science projects cancelled",
            "subtitle": f"The FY 2026 budget proposal ends most future mission work.",
            "source": "FY 2026 White House NASA Request"
        }
        
        # Filter by missions in development
        df_dev = df_dev[df_dev["Status"].isin(["Development"])].reset_index(drop=True)
        # Filter out entries where "Formulation Start Year" is NA
        df_dev = df_dev[df_dev["Formulation Start Year"].notna()].reset_index(drop=True)
        
        # Count the number of entries in df_dev
        num_dev_projects = len(df_dev)
        lollipop_view.lollipop_plot(
            metadata=metadata,
            stem="fy_2026_proposed_in_development_cancellations",
            categories=df_dev['Mission'],
            start_values=df_dev['Formulation Start Year'],
            end_values=df_dev['End Year'],
            sort_by='start',  # Sort by start year
            sort_ascending=False,
            colors=lollipop_view.TPS_COLORS["Neptune Blue"],
            xlim=(2010, 2027),
            start_value_labels=True,
            xlabel=None,
            grid=True,
            y_axis_position='right',  # Category labels on the right
            hide_y_spine=True,
            grid_axis='x',
            tick_size=12,
            end_marker_style='X',
            end_marker_color='red',
            marker_size=11,
            value_labels=False,  # Don't show individual year labels
            range_labels=False,   # Show duration in years
            category_wrap_length=25,
            export_data=export_df
        )
    
    def nasa_center_workforce_map(self):
        """Generate a map showing workforce breakdown at NASA centers."""
        
        pie_data = {
            'HQ': {
                'values': [1366, 475],  
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'ARC': {
                'values': [755, 470],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'AFRC': {
                'values': [309, 191],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'GRC': {
                'values': [837, 554],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'GSFC': {
                'values': [1549, 1335],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'JSC': {
                'values': [2594, 698],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'KSC': {
                'values': [1506, 510],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'LaRC': {
                'values': [1058, 672],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'MSFC': {
                'values': [1714, 526],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'SSC': {
                'values': [166, 108],
                'labels': ['Cut','Retained'],
                'colors': ['#037CC2', '#FF5D47'],
            }
        }
        
        # Create export data
        export_data = []
        for center, data in pie_data.items():
            for label, value in zip(data['labels'], data['values']):
                export_data.append({
                    'NASA Center': center,
                    'Job Category': label,
                    'Number of Employees': value
                })
        
        export_df = pd.DataFrame(export_data)
        
        metadata = {
            "title": "NASA's workforce reflects each center's specialization",
            "subtitle": "From astronauts at Johnson to scientists at Goddard, each center's staffing matches its mission focus.",
            "source": "NASA Workforce Data FY 2024 (Example Data)",
        }
        
        map_view = self.get_view('USMapPie')
        
        map_view.us_map_pie_plot(
            metadata=metadata,
            stem="nasa_center_map",
            pie_data=pie_data,
            show_percentages=True,
            show_pie_labels=True,
            base_pie_size=4000,
            show_state_boundaries=True,
            export_data=export_df
        )
    
    def fy2026_nasa_workforce_projections(self):
        df = Workforce().data()
        
        # Limit fiscal years to those through FY 2025
        fiscal_years = df[df["Fiscal Year"] <= pd.to_datetime("2026-01-01")]["Fiscal Year"]

        # Convert strings with commans into integers before plotting
        for col in ["Full-time Permanent (FTP)", "Full-time Equivalent (FTE)"]:
            if col in df.columns:
                # Remove commas and convert to int
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce").astype("Int64")

        # Add a column for FY2026 Projection with projected workforce size for FY 2026
        df["FY2026 Projection"] = np.where(
            df["Fiscal Year"] == pd.to_datetime("2026-01-01"),
            int(11853),
            np.nan
        )
        
        # Copy Workforce value for 2025-01-01 to the Projection column to ensure clean ploting
        df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "FY2026 Projection"] = df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "Full-time Equivalent (FTE)"]

        # Prepare cleaned export data for CSV
        export_df = self._export_helper(df, ["Fiscal Year", "Full-time Equivalent (FTE)", "FY2026 Projection"])

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        x_limit = 2027
        y_limit = 40_000
        
        # Prepare metadata
        metadata = {
            "title": "The smallest NASA workforce since 1960",
            "subtitle": "The White House's 2026 budget proposal cuts NASA's workforce to levels not seen since the dawn of the space age.",  
            "source": f"NASA FTE Workforce Reporting, FYs 1960-2026",
        }
                

        # Load the Line plotter view
        line_view = self.get_view('Line')
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="fy2026_nasa_workforce_cuts",
            x=fiscal_years,
            y=[df["Full-time Equivalent (FTE)"],df["FY2026 Projection"]],
            color=[line_view.COLORS["blue"], line_view.TPS_COLORS["Rocket Flame"]],
            linestyle=["-","-"],
            marker=["","o"],
            label=["","2026 White House proposal"],
            xlim=(datetime(1958,1,1), datetime(x_limit,1,1)),
            ylim={"bottom":0, "top":y_limit},
            legend={"loc":"lower right"},
            export_data=export_df,
            hlines=[11853],
            hline_labels=["Lowest since 1960"],
            hline_label_position="center",
            hline_colors=[line_view.TPS_COLORS["Crater Shadow"]],
            hline_linestyle=["--"],
            hline_linewidth=[2],
            ticksize=15
        )
    
    def generate_charts(self):
        """Generate all FY2026 charts."""
        self.nasa_budget_historical_with_fy_2026_proposed()
        self.nasa_science_by_year_inflation_adjusted_fy2026_threat()
        self.nasa_science_divisions_quad_plot_fy2026_threat()
        