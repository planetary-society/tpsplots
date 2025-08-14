"""Concrete NASA budget charts using specialized chart views."""
from pathlib import Path
from datetime import datetime
import numpy as np
from tpsplots import TPS_STYLE_FILE
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import Historical, ScienceDivisions, Science, Workforce, Directorates
from tpsplots.data_sources.missions import Missions
from matplotlib import pyplot as plt
import pandas as pd

class FY2026Charts(ChartController):
    
    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Science(),  # Historical NASA budget data source
        )
        
    def new_awards_comparison_to_prior_year(self):
        fy2024_baseline = {
            'Category': ['Contracts', 'Grants', 'Total'],
            'Oct': [164, 74, 238],
            'Nov': [196, 146, 342],
            'Dec': [246, 126, 372],
            'Jan': [270, 176, 446],
            'Feb': [285, 135, 420],
            'Mar': [360, 126, 486],
            'Apr': [342, 99, 441],
            'May': [398, 99, 497],
            'Jun': [427, 112, 539],
            'Jul': [712, 202, 914],
            'Aug': [858, 302, 1160],
            'Sep': [652, 415, 1067],
        }
        
        fy2025 = {
            'Category': ['Contracts', 'Grants', 'Total'],
            'Oct': [210, 22, 232],
            'Nov': [223, 95, 318],
            'Dec': [261, 125, 386],
            'Jan': [274, 64, 338],
            'Feb': [312, 79, 391],
            'Mar': [313, 70, 383],
            'Apr': [393, 58, 451],
            'May': [373, 215, 588],
            'Jun': [408, 145, 553],
            'Jul': [628, 198, 826],
            'Aug': [253, 121, 374],
        }
        
        # Define months in fiscal year order
        months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar',
                  'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
        
        # Extract grant values for each month
        fy2024_grants = [fy2024_baseline[month][1] for month in months]
        fy2025_grants = [fy2025[month][1] for month in months[:10]]  # Through July only
        
        # Calculate cumulative sums
        fy2024_cumulative = np.cumsum(fy2024_grants).tolist()
        fy2025_cumulative = np.cumsum(fy2025_grants).tolist()
        
        # Add None for September in FY2025 to maintain alignment
        fy2025_cumulative = fy2025_cumulative + [None,None]
        
        # Calculate estimated FY2025 total based on June/July average
        june_july_avg = (fy2025['Jun'][1] + fy2025['Jul'][1]) / 2  # (145 + 198) / 2 = 171.5
        current_total_through_july = sum(fy2025_grants)  # Current cumulative through July
        estimated_aug_sep = june_july_avg * 2  # Estimate for remaining 2 months (Aug + Sep)
        projected_fy2025_total = current_total_through_july + estimated_aug_sep
        
        # Calculate shortfall percentage
        fy2024_total = sum(fy2024_grants)  # Total FY2024 grants (2012)
        shortfall_pct = ((fy2024_total - projected_fy2025_total) / fy2024_total) * 100
        
        # Create export DataFrame
        export_df = pd.DataFrame({
            'Month': months,
            'FY 2024 Cumulative': fy2024_cumulative,
            'FY 2025 Cumulative': fy2025_cumulative
        })
        
        line_view = self.get_view('Line')
        
        metadata = {
            "title": "NASA is awarding fewer grants in 2025",
            "subtitle": f"Based on recent trends, NASA is on track to award {shortfall_pct:.0f}% fewer grants this year than in 2024.",
            "source": "USASpending.gov"
        }
        
        # Import ChartView to access color constants
        from tpsplots.views.chart_view import ChartView
        
        # Generate charts via the specialized line chart view
        line_view.line_plot(
            metadata=metadata,
            stem="new_grants_2024_vs_2025_cumulative",
            x=months,
            y=[fy2024_cumulative, fy2025_cumulative],
            color=[ChartView.COLORS["blue"], ChartView.TPS_COLORS["Rocket Flame"]],
            linestyle=["--", "-"],
            marker=["o", "o"],  # Add markers to FY2025 to show actual data points
            label=["FY 2024 New Grant Awards", "FY 2025 New Grant Awards"],
            ylim=(0, 2500),  # Scale for cumulative totals
            ylabel="Cumulative Number of Grants Awarded",
            label_size=13,
            tick_size=14,
            legend=True,
            grid=True,
            export_data=export_df
        )
        