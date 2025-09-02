"""Concrete NASA budget charts using specialized chart views."""
from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.views.chart_view import ChartView
import pandas as pd
from datetime import datetime
import re

import logging

logger = logging.getLogger(__name__)

class ChinaComparisonCharts(ChartController):
    
    def _process_china_mission_data(self):
        """
        Process China mission data from Google Sheets.
        Returns a DataFrame with parsed dates, decades, status, and mass values.
        """
        # Load data from Google Sheets
        source = GoogleSheetsSource(url="https://docs.google.com/spreadsheets/d/1u0PPWwkJv4qNivgD9cfQIVodVymF0K7oigAx7k_dzbA/export?format=csv")
        data = source.data()
        
        # Parse dates to get launch year and month (if available)
        def parse_launch_date(date_str):
            """Parse launch date to get year and month for launched/planned determination."""
            if pd.isna(date_str):
                return None, None
            
            date_str = str(date_str).strip()
            
            # Try to parse as full datetime
            try:
                dt = pd.to_datetime(date_str, errors='coerce')
                if not pd.isna(dt):
                    return dt.year, dt.month
            except:
                pass
            
            # If that fails, try to extract just the year
            year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
            if year_match:
                return int(year_match.group()), None
            
            return None, None
        
        # Apply parsing to get years and months
        data[['launch_year', 'launch_month']] = data['Launch Date'].apply(
            lambda x: pd.Series(parse_launch_date(x))
        )
        
        # Remove entries without valid years
        data = data.dropna(subset=['launch_year'])
        data['launch_year'] = data['launch_year'].astype(int)
        
        # Determine current date for launched vs planned
        current_date = datetime(2025, 9, 1)  # Using the date from environment
        
        # Categorize as Launched or Planned
        def categorize_mission(row):
            year = row['launch_year']
            month = row['launch_month']
            
            if year < current_date.year:
                return 'Launched'
            elif year > current_date.year:
                return 'Planned'
            else:  # year == current_date.year
                if pd.isna(month):
                    # If no month specified and year is current year, consider as planned
                    return 'Planned'
                elif month < current_date.month:
                    return 'Launched'
                else:
                    return 'Planned'
        
        data['status'] = data.apply(categorize_mission, axis=1)
        
        # Bin into decades
        def get_decade(year):
            if 2000 <= year <= 2009:
                return '2000-2009'
            elif 2010 <= year <= 2019:
                return '2010-2019'
            elif 2020 <= year <= 2029:
                return '2020-2029'
            else:
                return None
        
        data['decade'] = data['launch_year'].apply(get_decade)
        
        # Filter to only include our target decades
        data = data.dropna(subset=['decade'])
        
        # Parse mass values
        def parse_mass(mass_str):
            """Extract numeric mass value from various formats."""
            if pd.isna(mass_str):
                return None
            
            mass_str = str(mass_str).strip()
            
            # Extract numeric value (handle "1000 kg", "1,000", etc.)
            # Look for patterns like numbers with optional commas and decimal points
            match = re.search(r'[\d,]+\.?\d*', mass_str)
            if match:
                try:
                    return float(match.group().replace(',', ''))
                except:
                    return None
            return None
        
        data['mass_numeric'] = data['Mass'].apply(parse_mass)
        
        return data

    
    def china_space_science_mission_count_bar_chart(self):
        """Generate stacked bar chart showing mission counts by decade."""
        
        data = self._process_china_mission_data()
        
        # Count missions by decade and status
        decade_counts = data.groupby(['decade', 'status']).size().unstack(fill_value=0)
        
        # Ensure all decades are present
        decades = ['2000-2009', '2010-2019', '2020-2029']
        for decade in decades:
            if decade not in decade_counts.index:
                decade_counts.loc[decade] = 0
        
        # Ensure both statuses are present
        for status in ['Launched', 'Planned']:
            if status not in decade_counts.columns:
                decade_counts[status] = 0
        
        # Reorder to match our desired order
        decade_counts = decade_counts.reindex(decades, fill_value=0)
        
        # Prepare data for stacked bar chart
        categories = ["2000s", "2010s", "2020s"]
        values = {
            'Launched': decade_counts['Launched'].tolist(),
            'Planned': decade_counts['Planned'].tolist()
        }
        
        # Create metadata for the chart
        metadata = {
            "title": "China's space science efforts are taking off",
            "subtitle": "In just two decades, China has gone from a handful of science missions to launching dozens of cutting-edge projects.",
            "source": "CNSA Technical Papers and Releases",
        }
        
        # Get the stacked bar chart view
        stacked_view = self.get_view('StackedBar')
        
        # Generate the stacked bar chart
        stacked_view.stacked_bar_plot(
            metadata=metadata,
            stem="china_space_science_mission_growth",
            categories=categories,
            values=values,
            labels=['Launched', 'Planned'],
            orientation='vertical',
            show_values=False,
            width=0.5,
            label_size=15,
            tick_size=16,
            ylim=(0.01,25),
            colors=[ChartView.COLORS['blue'],ChartView.TPS_COLORS['Medium Neptune']],
            legend={'loc': 'upper left'},
            ylabel='Number of Missions',
            export_data=data[['Mission Name','Launch Date','Area','Source']]
        )
    
    def china_space_science_mission_mass_growth_line_chart(self):
        """Generate line chart showing average mass per decade."""
        
        data = self._process_china_mission_data()
        
        # Calculate average mass per decade
        decades = ['2000-2009', '2010-2019', '2020-2029']
        
        # Group by decade and calculate mean mass, excluding NaN values
        mass_by_decade = data.groupby('decade')['mass_numeric'].mean()
        
        # Ensure all decades are present and reindex to match our order
        mass_by_decade = mass_by_decade.reindex(decades, fill_value=0)
        
        # Convert to list for the chart
        mass_values = mass_by_decade.tolist()
        
        # Create metadata for the chart
        metadata = {
            "title": "China's science spacecraft are bulking up",
            "subtitle": "The average launch mass has nearly doubled in the past two decades, suggesting increasing complexity and scope.",
            "source": "CNSA Technical Papers and Releases",
        }
        
        # Get the line chart view
        line_view = self.get_view('Line')
        
        # Generate the line chart
        # Note: y must be wrapped in a list to indicate it's a single series
        line_view.line_plot(
            metadata=metadata,
            stem="china_average_mass_by_decade",
            x=["2000s", "2010s", "2020s"],
            y=[mass_values],  # Wrapped in list to indicate single series
            marker='o',
            markersize=8,
            color=ChartView.COLORS['blue'],
            tick_rotation=0,
            label_size=15,
            tick_size=16,
            legend=False,
            ylabel='Avg Launch Mass (kg)',
            ylim=(0.01, max(mass_values) * 1.2 if mass_values and max(mass_values) > 0 else 5000),
            export_data=data[['Mission Name', 'Launch Date', 'Mass', 'mass_numeric']]
        )
