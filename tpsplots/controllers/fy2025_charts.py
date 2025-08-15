"""Concrete NASA budget charts using specialized chart views."""
import numpy as np
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.views.chart_view import ChartView
import pandas as pd

class FY2025Charts(ChartController):
    
    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=NewNASAAwards(),  # Historical NASA budget data source
        )
        
    def new_awards_comparison_to_prior_year(self):
        # Get data from external data source
        df = self.data_source.data()
        
        # Filter out the "Total" row if present
        df = df[df['Month'] != 'Total'].copy()
        
        # Define months in fiscal year order
        months = ['October', 'November', 'December', 'January', 'February', 'March',
                  'April', 'May', 'June', 'July', 'August', 'September']
        
        # Extract grant award data for each fiscal year
        grant_columns = {
            2020: 'FY 2020 New Grant Awards',
            2021: 'FY 2021 New Grant Awards', 
            2022: 'FY 2022 New Grant Awards',
            2023: 'FY 2023 New Grant Awards',
            2024: 'FY 2024 New Grant Awards',
            2025: 'FY 2025 New Grant Awards'
        }
        
        # Calculate cumulative sums for each year
        cumulative_data = {}
        y_series = []
        labels = []
        colors = []
        linestyles = []
        markers = []
        linewidths = []
        
        # Grey color palette for prior years (2020-2024)
        grey_color = ChartView.COLORS["medium_gray"]
        
        # Process prior years (2020-2024) - full fiscal year data
        for year in [2020, 2021, 2022, 2023, 2024]:
            if grant_columns[year] in df.columns:
                year_grants = df[grant_columns[year]].tolist()
                year_cumulative = np.cumsum(year_grants).tolist()
                cumulative_data[year] = year_cumulative
                
                y_series.append(year_cumulative)
                labels.append(None)
                colors.append(grey_color)
                linestyles.append("-")  # Solid lines
                markers.append(None)
                linewidths.append(1.5)  # Lighter weight for past years
        
        # Calculate mean of prior years (2020-2024)
        if cumulative_data:
            prior_years_array = np.array(list(cumulative_data.values()))
            mean_cumulative = np.mean(prior_years_array, axis=0).tolist()
            
            y_series.append(mean_cumulative)
            labels.append("Avg 2020-24")
            colors.append(ChartView.COLORS["blue"])  # 
            linestyles.append("-")
            markers.append("o")
            linewidths.append(4.0)  # Normal weight for average
        
        # Process FY 2025 - only October through July (first 10 months)
        if grant_columns[2025] in df.columns:
            fy2025_grants = df[grant_columns[2025]].tolist()[:10]  # Oct-July only
            fy2025_cumulative = np.cumsum(fy2025_grants).tolist()
            
            # Add None for August and September to maintain alignment
            fy2025_cumulative_padded = fy2025_cumulative + [None, None]
            
            y_series.append(fy2025_cumulative_padded)
            labels.append("FY 2025")
            colors.append(ChartView.TPS_COLORS["Rocket Flame"])
            linestyles.append("-")  # Solid line
            markers.append("o")  # Add markers to show actual data points
            linewidths.append(4.0)  # Normal weight for current year
        
        # Calculate projection for subtitle (based on FY 2025 data through July)
        if 'mean_cumulative' in locals() and len(fy2025_cumulative) > 0:
            # Compare FY 2025 July cumulative to average July cumulative
            fy2025_july_total = fy2025_cumulative[9]  # July (index 9)
            avg_july_total = mean_cumulative[9]  # July average
            shortfall_pct = ((avg_july_total - fy2025_july_total) / avg_july_total) * 100
        else:
            shortfall_pct = 0
        
        # Create export DataFrame with all series
        export_data = {'Month': months}
        for year_label, year_data in zip(labels, y_series):
            export_data[f'{year_label} Cumulative'] = year_data
        
        export_df = pd.DataFrame(export_data)
        
        line_view = self.get_view('Line')
        
        metadata = {
            "title": "NASA grant awards trail historical patterns in FY 2025",
            "subtitle": f"Through July, NASA is awarding {shortfall_pct:.0f}% fewer grants compared to the 5-year average.",
            "source": "USASpending.gov"
        }
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="new_grants_historical_comparison",
            x=months,
            y=y_series,
            color=colors,
            linestyle=linestyles,
            linewidth=linewidths,
            marker=markers,
            label=labels,
            ylim=(0, 2500),  # Scale for cumulative totals
            ylabel="Cumulative New Grants Awarded",
            label_size=13,
            tick_size=14,
            direct_line_labels={'fontsize':10},  # Use direct line labels instead of standard legend
            legend=False, # Disable traditional legend
            grid=True,
            export_data=export_df
        )
        