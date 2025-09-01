"""Concrete NASA budget charts using specialized chart views."""
from datetime import datetime
import numpy as np
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Historical, ScienceDivisions, Science, Workforce, Directorates
from tpsplots.data_sources.missions import Missions
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
            "title": "The smallest NASA budget since 1961",
            "subtitle": "The White House's proposed NASA budget, adjusted for inflation, is the lowest since the start of human spaceflight.",
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
        """
        Generate a lollipop chart showing the launch date to end of all NASA missions
        proposed as cancelled in FY 2026.
        """
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
            xlim=(1997, 2027),
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
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'ARC': {
                'values': [755, 470],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'AFRC': {
                'values': [309, 191],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'GRC': {
                'values': [837, 554],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'GSFC': {
                'values': [1549, 1335],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'JSC': {
                'values': [2594, 698],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'KSC': {
                'values': [1506, 510],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'LaRC': {
                'values': [1058, 672],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'MSFC': {
                'values': [1714, 526],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            },
            'SSC': {
                'values': [166, 108],
                'labels': ['Workforce Remaining','Proposed Staff Cuts'],
                'colors': ['#037CC2', '#FF5D47'],
            }
        }
        
        # Create export data
        export_data = []
        for center, data in pie_data.items():
            fy2025_staffing = sum(data['values'])
            proposed_fy2026_staffing = data['values'][0]
            export_data.append({
                "NASA Center": center,
                "FY 2025 Staffing": fy2025_staffing,
                "Proposed FY 2026 Staffing": proposed_fy2026_staffing
            })
            
        export_df = pd.DataFrame(export_data)
        
        metadata = {
            "title": "NASA faces nation-wide workforce cuts",
            "subtitle": "The White House's 2026 budget proposal slashes staffing at each of the agency's 10 field centers by 20% - 46%.",
            "source": "NASA FY 2026 Budget Request",
        }
        
        map_view = self.get_view('USMapPie')
        
        map_view.us_map_pie_plot(
            metadata=metadata,
            stem="fy2026_nasa_center_workforce_reductions",
            pie_data=pie_data,
            show_percentages=[False,True], # Only show cuts
            show_pie_labels=True,
            base_pie_size=4500,
            show_state_boundaries=True,
            offset_line_color='#666666',
            offset_line_style='-.',
            offset_line_width=2,
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
            "source": "NASA FTE Workforce Reporting, FYs 1960-2026",
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
    
    
    def directorate_changes_stacked_bar_chart(self):
        """Example: Horizontal stacked bar chart comparing mission costs."""
        df = Directorates().data()
        
        # Remove any column from df that has "(2025)" in the column name
        df = df[[col for col in df.columns if all(x not in col for x in ["(2025)", "gdp", "nnsi"])]]
        
        # Filter the DataFrame to just FY2025/26
        year_df = df[df["Fiscal Year"].dt.year == (datetime(2025,1,1).year or datetime(2026,1,1).year)]
        
        # Sample data - Mission costs by category
        categories = [col for col in year_df.columns if "Fiscal Year" not in col]
        # Rename categories using the provided mapping
        category_rename = {
            'Aeronautics': 'Aero',
            'Deep Space Exploration Systems': 'Exploration',
            'LEO Space Operations': 'Space Ops',
            'Space Technology': 'Tech',
            'Science': 'Science',
            'STEM Education': 'STEM',
            'Facilities, IT, & Salaries': 'SSMS/CECR'
        }
        categories = [category_rename.get(cat, cat) for cat in categories]
        # Calculate difference between FY 2025 and 2026:
        fy2025_row = df[df["Fiscal Year"].dt.year == datetime(2025,1,1).year].iloc[0]
        fy2026_row = df[df["Fiscal Year"].dt.year == datetime(2026,1,1).year].iloc[0]
        diff_list = [-(fy2026_row[col] - fy2025_row[col]) for col in df.columns if col not in ["Fiscal Year"]]
        # Remove "Fiscal Year" from the data rows
        fy2025_values = [fy2025_row[col] for col in df.columns if col != "Fiscal Year"]
        fy2026_values = [fy2026_row[col] for col in df.columns if col != "Fiscal Year"]
        diff_values = [-(fy2026_row[col] - fy2025_row[col]) if (fy2026_row[col] - fy2025_row[col]) < 0 else 0 for col in df.columns if col != "Fiscal Year"]
        # Sort fy2026_values from large to small, and apply the same order to diff_values and categories
        sorted_indices = np.argsort(fy2026_values)[::-1]
        fy2026_values = [fy2026_values[i] for i in sorted_indices]
        diff_values = [diff_values[i] for i in sorted_indices]
        categories = [categories[i] for i in sorted_indices]
        data = {
            "FY26": fy2026_values,
            "FY26 Diff": diff_values
        }

        # Create an exportable dataframe of categories and fy2025 and 2026 values
        export_df = pd.DataFrame({
            "Category": categories,
            "FY2025": [fy2025_row[col] for col in df.columns if col != "Fiscal Year"],
            "FY2026": fy2026_values
        })
        
        metadata = {
            "title": "Cuts are proposed across NASA",
            "subtitle": "The FY 2026 White House budget impacts all parts of NASA — except human exploration beyond Earth.",
            "source": "NASA FY 2026 Budget Request"
        }

        stacked_view = self.get_view('StackedBar')

        stacked_view.stacked_bar_plot(
            metadata=metadata,
            stem="fy2026_directorate_cuts",
            categories=categories,
            values=data,
            labels=["FY2026 Proposed","Amount Cut from FY 2025"],
            orientation='vertical',
            show_values=True,
            value_format='monetary',
            value_threshold=0,
            value_fontsize=10,
            stack_labels=False,
            stack_label_format='monetary',
            scale='billions',
            colors=['#037CC2', '#FF5D47'],
            legend={'loc': 'upper right'},
            export_data=export_df
        )
    
    def fy2026_budget_relative_proposed_change(self):
        df = Historical().data().dropna(subset=["PBR"])
        df = df[
            (df["Fiscal Year"] <= pd.to_datetime("2026-01-01"))
        ]
    
        # Calculate relative change of PBR to prior year's appropriations
        df = df.sort_values("Fiscal Year").reset_index(drop=True)
        df["Prior Year Appropriation"] = df["Appropriation"].shift(1)
        df["Relative Change"] = ((df["PBR"] - df["Prior Year Appropriation"]) / df["Prior Year Appropriation"]) * 100
        
        # Remove 1959 since there is no prior comparison
        df = df[df["Fiscal Year"] != datetime(1959, 1, 1)]
    
        # Add empty rows to 2030 for display purposes
        new_rows = pd.DataFrame({
            "Fiscal Year": [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1), datetime(2030, 1, 1)],
            "Relative Change": [0, 0, 0, 0]
        })
        df = pd.concat([df, new_rows], ignore_index=True).sort_values("Fiscal Year").reset_index(drop=True)
        # Set fiscal years from 
        fiscal_years = [str(round(val, 0)) if pd.notnull(val) else val for val in df["Fiscal Year"].dt.year.to_list()]
        values = [round(val, 1) if pd.notnull(val) else val for val in df["Relative Change"].to_list()]
    
        # Create Export df
        export_df = pd.DataFrame({
            "Fiscal Year": fiscal_years[:-4], # remove placeholder values for data output
            "Relative Change (%)": values[:-4]
        })
    
        # Prepare metadata
        metadata = {
            "title": "The largest cut to NASA ever proposed",
            "subtitle": "The White House's 2026 budget proposes a 25% cut from the prior year — the largest ever.",  
            "source": "NASA Budget Requests FYs 1960-2026",
        }

        bar_view = self.get_view('Bar')
        bar_view.bar_plot(
            metadata=metadata,
            negative_color=bar_view.TPS_COLORS["Rocket Flame"],
            stem="fy2026_largest_cut_in_nasa_history",
            categories=df["Fiscal Year"],
            values=values,
            ylabel="% change of proposed budget from prior year",
            show_values=False,
            value_format="percentage",
            export_data=export_df
        )
    
    def congressional_vs_white_house_nasa_budget_stacked_bar_chart(self):
        """Horizontal stacked bar chart comparing funding by major account."""

        # These data are fixed for the FY 2026 budget request, so let's hardcode them here
        
        categories = [
            "PBR",
            "House",
            "Senate"
        ]
        
        # Account as key, then WH, House, Senate values listed in that order
        # data = {
        #     "Exploration": [8_312_900_000, 9_715_800_000, 7_900_000_000],
        #     "Science": [3_907_600_000, 6_000_000_000, 7_300_000_000],
        #     "Space Ops": [3_131_900_000, 4_150_000_000, 4_314_000_000],
        #     "SSMS/CECR": [(2_111_830_000+140_100_000), (3_044_000_000+200_000_000), (3_107_100_000+275_000_000)],
        #     "Tech": [568_900_000, 912_800_000, 975_000_000],
        #     "Aero": [588_700_000, 775_000_000, 950_000_000],
        #     "STEM": [0,84_000_000,148_000_000]
        # }
        
        data = {
            "NASA": [18_800_000_000, 24_838_300_000, 24_899_700_000]
        }
        

        # Create an exportable dataframe of categories and fy2025 and 2026 values
        export_df = pd.DataFrame({
            "Proposal": categories,
            "NASA FY 2026": data["NASA"],
        })
        
        metadata = {
            "title": "Congress rejects massive NASA cuts",
            "subtitle": "The President's Budget Request (PBR) proposed the largest cut in history, but Congress wants to maintain funding.",
            "source": "NASA FY 2026 PBR, HAC-CJS, SAC-CJS"
        }

        stacked_view = self.get_view('StackedBar')
        
        stacked_view.stacked_bar_plot(
            metadata=metadata,
            stem="fy2026_congressional_vs_white_house_nasa_budgets",
            categories=categories,
            values=data,
            labels=None,
            orientation='vertical',
            show_values=True,
            value_format='monetary',
            value_threshold=0,
            value_fontsize=15,
            width=0.5,
            stack_labels=False,
            stack_label_format='monetary',
            scale='billions',
            colors=['#037CC2'],
            legend={'loc': 'upper right'},
            export_data=export_df
        )
        
        