"""Concrete NASA budget charts using specialized chart views."""
import numpy as np
import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.views.chart_view import ChartView


class FY2025Charts(ChartController):
    
    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=NewNASAAwards(),  # Historical NASA budget data source
        )
    
    def _process_award_data(self, award_type="Grant"):
        """
        Process award data for historical comparison.
        
        Args:
            award_type: Either "Grant" or "Contract"
        
        Returns:
            dict containing all processed data needed for chart generation
        """
        # Get data from external data source
        df = self.data_source.data()
        
        # Filter out the "Total" row if present
        df = df[df['Month'] != 'Total'].copy()
        
        # Define months in fiscal year order
        months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar',
                  'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
        
        # Build award columns dictionary dynamically
        award_columns = {
            year: f'FY {year} New {award_type} Awards'
            for year in [2020, 2021, 2022, 2023, 2024, 2025]
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
            if award_columns[year] in df.columns:
                year_awards = df[award_columns[year]].tolist()
                year_cumulative = np.rint(np.cumsum(year_awards)).astype(int).tolist()
                
                cumulative_data[year] = year_cumulative
                
                y_series.append(year_cumulative)
                labels.append(None)
                colors.append(grey_color)
                linestyles.append("--")
                markers.append(None)
                linewidths.append(1.5)  # Lighter weight for past years
        
        # Calculate mean of prior years (2020-2024)
        if cumulative_data:
            prior_years_array = np.array(list(cumulative_data.values()))
            mean_cumulative = np.rint(np.mean(prior_years_array, axis=0)).astype(int).tolist()
            
            y_series.append(mean_cumulative)
            labels.append("2020-24\nAverage")
            colors.append(ChartView.COLORS["blue"])
            linestyles.append("-")
            markers.append("o")
            linewidths.append(4.0)  # Normal weight for average
        
        # Process FY 2025
        
        if pd.Timestamp.now() > pd.Timestamp(year=2025, month=9, day=30):
            # If current date is past FY 2025, use full data
            last_full_month = 12
            none_tail = []
        else:
            # Get month number for current month to slice data
            last_full_month = (pd.Timestamp.now().month - 1) + 3  # Fiscal year offset
            
            # Make a list of None for months beyond the last full month
            # last_full_month is the count of months available (0-11). Ensure non-negative.
            if last_full_month < 0:
                last_full_month = 0
            total_months = 12
            none_tail = [None] * max(0, total_months - last_full_month)

        fy2025_cumulative = []
            
        if award_columns[2025] in df.columns:
            fy2025_awards = df[award_columns[2025]].tolist()[:last_full_month]
            fy2025_cumulative = np.rint(np.cumsum(fy2025_awards)).astype(int).tolist()
            
            # Add None for August and September to maintain alignment
            fy2025_cumulative_padded = fy2025_cumulative + none_tail
            
            y_series.append(fy2025_cumulative_padded)
            labels.append("FY 2025")
            colors.append(ChartView.TPS_COLORS["Rocket Flame"])
            linestyles.append("-")  # Solid line
            markers.append("o")  # Add markers to show actual data points
            linewidths.append(4.0)  # Normal weight for current year
        
        # Calculate full-year projection for FY 2025 using June-July average rate
        shortfall_pct = 0
        if 'mean_cumulative' in locals() and len(fy2025_cumulative) > 0:
            # Extra prior two months needed for projection
            two_months_ago_awards = fy2025_awards[last_full_month-2]
            one_month_ago_awards = fy2025_awards[last_full_month-1]  # July (index 9)
            avg_monthly_rate = (two_months_ago_awards + one_month_ago_awards) / 2
            
            
            for month in range(last_full_month, 12):
                fy2025_cumulative.append(avg_monthly_rate + fy2025_cumulative[month-1])
            
            if len(fy2025_cumulative) != 12:
                raise ValueError("FY 2025 cumulative data does not have 12 months after projection.")
            
            # Calculate projected full-year FY 2025 cumulative total

            projected_fy2025_total = fy2025_cumulative[-1]
            # Compare to average September cumulative total (full fiscal year)
  
            avg_prior_year_total = cumulative_data[2024][-1]

            shortfall_pct = ((avg_prior_year_total - projected_fy2025_total) / avg_prior_year_total) * 100
        
        # Create export DataFrame with all series
        export_data = {'Month': months}
        for year_label, year_data in zip(labels, y_series, strict=False):
            if year_label is not None:  # Skip None labels
                export_data[f'{year_label} Cumulative'] = year_data
        
        export_df = pd.DataFrame(export_data)
        
        # Convert numeric columns to nullable integer type to avoid float conversion
        for col in export_df.columns:
            if col != 'Month':
                export_df[col] = pd.array(export_df[col], dtype=pd.Int64Dtype())
        
        return {
            'months': months,
            'y_series': y_series,
            'labels': labels,
            'colors': colors,
            'linestyles': linestyles,
            'markers': markers,
            'linewidths': linewidths,
            'shortfall_pct': shortfall_pct,
            'export_df': export_df
        }
        
    def new_grants_awards_comparison_to_prior_year(self):
        """
        Process grant award data for historical comparison.

        Returns:
            dict: Processed data dictionary containing all chart parameters
        """
        # Get processed grant data
        data = self._process_award_data(award_type="Grant")

        # Return the data dictionary for use by YAML processor
        return data
    
    def new_contract_awards_comparison_to_prior_years(self):
        """
        Process contract award data for historical comparison.

        Returns:
            dict: Processed data dictionary containing all chart parameters
        """
        # Get processed contract data
        data = self._process_award_data(award_type="Contract")

        # Return the data dictionary for use by YAML processor
        return data
        