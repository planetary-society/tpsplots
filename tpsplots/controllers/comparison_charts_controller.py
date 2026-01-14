"""Concrete NASA budget charts using specialized chart views."""
import logging

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController

logger = logging.getLogger(__name__)

class ComparisonCharts(ChartController):
    def nasa_spending_as_part_of_annual_us_expenditures(self):
        """Generate NASA's portion of U.S. spending using a waffle chart."""
        
        # Load View for Waffle Charts
        waffle_view = self.get_view('Waffle')
        
        comparisons = {"Non-NASA U.S. Spending": 6_800_000_000_000, "NASA": 25_000_000_000}
        
        # Define block value
        block_value = 25_000_000_000

        # Scale values to represent blocks
        scaled_directorates = {k: round(v / block_value) for k, v in comparisons.items()}
        
        # Order directorates so largest values are first
        sorted_directorates = dict(sorted(scaled_directorates.items(), key=lambda item: item[1], reverse=False))

        # Calculate relative percentages for labels
        labels = [
            f"{k} ({v / sum(comparisons.values()) * 100:.2f}%)" if v / sum(comparisons.values()) * 100 < 1 
            else f"{k} ({v / sum(comparisons.values()) * 100:.2f}%)" 
            for k, v in sorted(comparisons.items(), key=lambda item: item[1], reverse=False)
        ]

        # Add block value explanation to the title or subtitle
        metadata = {
            "title": "NASA is a fraction of U.S. spending",
            "subtitle": "One small block for NASA ($25 billion), one giant expenditure for everything else ($6.8 trillion).",
            "source": "Congressional Budget Office, FY 2024",
        }
        
        category_colors = [
            waffle_view.TPS_COLORS["Neptune Blue"],
            waffle_view.TPS_COLORS["Comet Dust"],
        ]
        
        export_df = pd.DataFrame({
            "Category": ["NASA", "U.S. Total Outlays"],
            "FY 2024 Spending ($)": [v * block_value for v in sorted_directorates.values()]
        })
        
        waffle_view.waffle_chart(
            metadata=metadata,
            stem="nasa_spending_as_part_of_annual_us_expenditures",
            values=sorted_directorates,
            labels=labels, 
            colors=category_colors,
            vertical=True,
            starting_location='SW',
            interval_ratio_x=0.25,
            interval_ratio_y=0.25,
            legend={
                'loc': 'lower left',
                'frameon': False,  # No border
                'bbox_to_anchor': (0,-0.09),
                'ncol': 2,
                'handlelength': .8
            },
            export_data=export_df
        )