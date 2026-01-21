"""Concrete NASA budget charts using specialized chart views."""

import logging
import re
from datetime import datetime

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.views.chart_view import ChartView

logger = logging.getLogger(__name__)


class ChinaComparisonCharts(ChartController):
    def _process_us_mission_data(self):
        """
        Process U.S. mission data from SpaceScienceMissions data source.
        Returns a DataFrame with parsed dates, decades, status, and mass values.
        """
        from tpsplots.data_sources.space_science_missions import SpaceScienceMissions

        # Load data from SpaceScienceMissions
        source = SpaceScienceMissions()
        data = source.data()

        # Filter for U.S. missions
        data = data[data["Nation"].str.startswith("United States", na=False)]

        # Parse dates to get launch year and month
        data["launch_datetime"] = pd.to_datetime(data["Mission Launch Date"], errors="coerce")
        data["launch_year"] = data["launch_datetime"].dt.year
        data["launch_month"] = data["launch_datetime"].dt.month

        # Remove entries without valid years
        data = data.dropna(subset=["launch_year"])
        data["launch_year"] = data["launch_year"].astype(int)

        # Determine current date for launched vs planned
        current_date = datetime(2025, 9, 1)  # Using consistent date

        # Categorize as Launched or Planned
        def categorize_mission(row):
            year = row["launch_year"]
            month = row["launch_month"]

            if year < current_date.year:
                return "Launched"
            elif year > current_date.year:
                return "Planned"
            else:  # year == current_date.year
                if pd.isna(month):
                    # If no month specified and year is current year, consider as planned
                    return "Planned"
                elif month < current_date.month:
                    return "Launched"
                else:
                    return "Planned"

        data["status"] = data.apply(categorize_mission, axis=1)

        # Bin into decades
        def get_decade(year):
            if 2000 <= year <= 2009:
                return "2000-2009"
            elif 2010 <= year <= 2019:
                return "2010-2019"
            elif 2020 <= year <= 2029:
                return "2020-2029"
            else:
                return None

        data["decade"] = data["launch_year"].apply(get_decade)

        # Filter to only include our target decades
        data = data.dropna(subset=["decade"])

        return data

    def _process_china_mission_data(self):
        """
        Process China mission data from Google Sheets.
        Returns a DataFrame with parsed dates, decades, status, and mass values.
        """
        # Load data from Google Sheets
        source = GoogleSheetsSource(
            url="https://docs.google.com/spreadsheets/d/1u0PPWwkJv4qNivgD9cfQIVodVymF0K7oigAx7k_dzbA/export?format=csv"
        )
        data = source.data()

        # Parse dates to get launch year and month (if available)
        def parse_launch_date(date_str):
            """Parse launch date to get year and month for launched/planned determination."""
            if pd.isna(date_str):
                return None, None

            date_str = str(date_str).strip()

            # Try to parse as full datetime
            try:
                dt = pd.to_datetime(date_str, errors="coerce")
                if not pd.isna(dt):
                    return dt.year, dt.month
            except (ValueError, TypeError):
                pass

            # If that fails, try to extract just the year
            year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
            if year_match:
                return int(year_match.group()), None

            return None, None

        # Apply parsing to get years and months
        data[["launch_year", "launch_month"]] = data["Launch Date"].apply(
            lambda x: pd.Series(parse_launch_date(x))
        )

        # Remove entries without valid years
        data = data.dropna(subset=["launch_year"])
        data["launch_year"] = data["launch_year"].astype(int)

        # Determine current date for launched vs planned
        current_date = datetime(2025, 9, 1)  # Using the date from environment

        # Categorize as Launched or Planned
        def categorize_mission(row):
            year = row["launch_year"]
            month = row["launch_month"]

            if year < current_date.year:
                return "Launched"
            elif year > current_date.year:
                return "Planned"
            else:  # year == current_date.year
                if pd.isna(month):
                    # If no month specified and year is current year, consider as planned
                    return "Planned"
                elif month < current_date.month:
                    return "Launched"
                else:
                    return "Planned"

        data["status"] = data.apply(categorize_mission, axis=1)

        # Bin into decades
        def get_decade(year):
            if 2000 <= year <= 2009:
                return "2000-2009"
            elif 2010 <= year <= 2019:
                return "2010-2019"
            elif 2020 <= year <= 2029:
                return "2020-2029"
            else:
                return None

        data["decade"] = data["launch_year"].apply(get_decade)

        # Filter to only include our target decades
        data = data.dropna(subset=["decade"])

        # Parse mass values
        def parse_mass(mass_str):
            """Extract numeric mass value from various formats."""
            if pd.isna(mass_str):
                return None

            mass_str = str(mass_str).strip()

            # Extract numeric value (handle "1000 kg", "1,000", etc.)
            # Look for patterns like numbers with optional commas and decimal points
            match = re.search(r"[\d,]+\.?\d*", mass_str)
            if match:
                try:
                    return float(match.group().replace(",", ""))
                except (ValueError, TypeError):
                    return None
            return None

        data["mass_numeric"] = data["Mass"].apply(parse_mass)

        return data

    def china_space_science_mission_count_bar_chart(self):
        """Generate grouped bar chart showing mission counts by decade for China vs U.S.

        Returns a dict with chart data for YAML processing.
        """
        # Process both datasets
        china_data = self._process_china_mission_data()
        us_data = self._process_us_mission_data()

        # Count missions by decade and status for both countries
        decades = ["2000-2009", "2010-2019", "2020-2029"]

        # China counts
        china_counts = china_data.groupby(["decade", "status"]).size().unstack(fill_value=0)
        china_counts = china_counts.reindex(decades, fill_value=0)
        for status in ["Launched", "Planned"]:
            if status not in china_counts.columns:
                china_counts[status] = 0

        # U.S. counts
        us_counts = us_data.groupby(["decade", "status"]).size().unstack(fill_value=0)
        us_counts = us_counts.reindex(decades, fill_value=0)
        for status in ["Launched", "Planned"]:
            if status not in us_counts.columns:
                us_counts[status] = 0

        # Extract values
        china_launched = china_counts["Launched"].tolist()
        china_planned = china_counts["Planned"].tolist()
        us_launched = us_counts["Launched"].tolist()
        us_planned = us_counts["Planned"].tolist()

        # Colors
        china_color_launched = "#8B0000"  # Dark red for China launched
        china_color_planned = "#CD5C5C"  # Light red for China planned
        us_color_launched = ChartView.COLORS["blue"]  # Blue for U.S. launched
        us_color_planned = ChartView.TPS_COLORS["Medium Neptune"]  # Light blue for U.S. planned

        # Build export data
        export_df = pd.concat(
            [
                china_data[["Mission Name", "Launch Date", "Area", "Source"]].assign(
                    Nation="China"
                ),
                us_data[["Full Name", "Mission Launch Date"]]
                .rename(columns={"Full Name": "Mission Name", "Mission Launch Date": "Launch Date"})
                .assign(Nation="United States", Area="", Source="NASA Mission Database"),
            ],
            ignore_index=True,
        )

        return {
            "title": "China's space science efforts are accelerating",
            "subtitle": "While the U.S. maintains a lead in total missions, China's growth rate in the 2020s shows rapid advancement.",
            "source": "CNSA Technical Papers and Releases; NASA Mission Database",
            "categories": ["2000s", "2010s", "2020s"],
            "groups": [
                {
                    "label": "China",
                    "values": china_launched,
                    "color": china_color_launched,
                    "stacked_values": [china_planned[2]],  # Only 2020s has stacking
                    "stacked_color": china_color_planned,
                },
                {
                    "label": "U.S.",
                    "values": us_launched,
                    "color": us_color_launched,
                    "stacked_values": [us_planned[2]],  # Only 2020s has stacking
                    "stacked_color": us_color_planned,
                },
            ],
            "width": 0.35,
            "show_values": True,
            "ylim": [0.01, 50],
            "legend": {"loc": "upper left"},
            "export_df": export_df,
        }

    def china_space_science_mission_mass_growth_line_chart(self):
        """Generate line chart showing average mass per decade for China vs U.S.

        Returns a dict with chart data for YAML processing.
        """
        # Process China data
        china_data = self._process_china_mission_data()

        # Process U.S. data
        us_data = self._process_us_mission_data()

        # Calculate average mass per decade
        decades = ["2000-2009", "2010-2019", "2020-2029"]

        # China: Group by decade and calculate mean mass, excluding NaN values
        china_mass_by_decade = china_data.groupby("decade")["mass_numeric"].mean()
        china_mass_by_decade = china_mass_by_decade.reindex(decades, fill_value=0)
        china_mass_values = china_mass_by_decade.tolist()

        # U.S.: Convert mass to numeric and calculate mean by decade
        us_data["mass_numeric"] = pd.to_numeric(us_data["Mass (kg)"], errors="coerce")
        us_mass_by_decade = us_data.groupby("decade")["mass_numeric"].mean()
        us_mass_by_decade = us_mass_by_decade.reindex(decades, fill_value=0)
        us_mass_values = us_mass_by_decade.tolist()

        # Determine y-axis limit based on max value across both datasets
        max_mass = (
            max(max(china_mass_values), max(us_mass_values))
            if china_mass_values and us_mass_values
            else 5000
        )

        # Build export data
        export_df = pd.concat(
            [
                china_data[["Mission Name", "Launch Date", "Mass", "mass_numeric"]].assign(
                    Nation="China"
                ),
                us_data[["Full Name", "Mission Launch Date", "Mass (kg)", "mass_numeric"]]
                .rename(
                    columns={
                        "Full Name": "Mission Name",
                        "Mission Launch Date": "Launch Date",
                        "Mass (kg)": "Mass",
                    }
                )
                .assign(Nation="United States"),
            ],
            ignore_index=True,
        )

        return {
            "title": "China's science spacecraft are catching up in mass",
            "subtitle": "Average launch mass comparison shows U.S. missions remain larger, but China's are rapidly increasing in complexity.",
            "source": "CNSA Technical Papers and Releases; NASA Mission Database",
            "x": ["2000s", "2010s", "2020s"],
            "y": [china_mass_values, us_mass_values],
            "label": ["China", "United States"],
            "marker": "o",
            "markersize": 8,
            "color": [ChartView.TPS_COLORS["Medium Neptune"], ChartView.COLORS["blue"]],
            "tick_rotation": 0,
            "label_size": 15,
            "tick_size": 16,
            "legend": {"loc": "upper left"},
            "ylabel": "Avg Launch Mass (kg)",
            "ylim": [0.01, max_mass * 1.2],
            "export_df": export_df,
        }
