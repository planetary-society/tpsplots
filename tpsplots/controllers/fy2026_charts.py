"""Concrete NASA budget charts using specialized chart views."""

from datetime import datetime

import numpy as np
import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.missions import Missions
from tpsplots.data_sources.nasa_budget_data_source import (
    Directorates,
    Historical,
    Science,
    ScienceDivisions,
    Workforce,
)
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig
from tpsplots.views.chart_view import ChartView


class FY2026Charts(ChartController):
    CONGRESSIONAL_CUTOFF_YEAR = 2025
    PRESIDENTIAL_REQUEST_YEAR_START = 2026
    PRESIDENTIAL_REQUEST_YEAR_END = 2030
    PRESIDENTIAL_REQUEST_VALUE = 18_009_100_000

    def __init__(self):
        # Initialize with data source
        super().__init__(
            data_source=Science(),  # Historical NASA budget data source
        )

        # Define the fiscal year configuration for FY 2026 award tracking
        self.fy2026_award_config = FiscalYearConfig(
            prior_years=[2021, 2022, 2023, 2024, 2025],
            current_year=2026,
            comparison_year=2025,
        )

    def nasa_budget_historical_with_fy_2026_proposed(self):
        """Prepare historical NASA budget chart data with FY 2026 proposal."""
        self.data_source = Historical()
        # Get data from model
        df = self.data_source.data().dropna(subset=["PBR"])

        congressional_cutoff = pd.Timestamp(f"{self.CONGRESSIONAL_CUTOFF_YEAR}-01-01")
        congressional_mask = df["Fiscal Year"] > congressional_cutoff
        for col in ["Appropriation", "Appropriation_adjusted_nnsi"]:
            if col in df.columns:
                df.loc[congressional_mask, col] = pd.NA

        # Copy Appropriation value for 2025-01-01 to the White House Budget Projection for 2025-01-01
        df.loc[
            df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "White House Budget Projection"
        ] = df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "Appropriation"]
        request_mask = df["Fiscal Year"].dt.year.between(
            self.PRESIDENTIAL_REQUEST_YEAR_START, self.PRESIDENTIAL_REQUEST_YEAR_END
        )
        df.loc[request_mask, "White House Budget Projection"] = self.PRESIDENTIAL_REQUEST_VALUE

        fiscal_years = df[
            df["Fiscal Year"] <= pd.to_datetime(f"{self.PRESIDENTIAL_REQUEST_YEAR_END}-01-01")
        ]["Fiscal Year"]

        # Prepare cleaned export data for CSV
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "Appropriation",
                "White House Budget Projection",
                "Appropriation_adjusted_nnsi",
            ],
        )

        # Remove "White House Budget Proposal" values where "Appropriation" is present, for clarity
        export_df.loc[df["Appropriation"].notna(), "White House Budget Projection"] = pd.NA

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        max_fiscal_year = int(fiscal_years.max().strftime("%Y"))
        x_limit = self._get_rounded_axis_limit_x(max_fiscal_year, 10, True)
        y_limit = self._get_rounded_axis_limit_y(
            df["Appropriation_adjusted_nnsi"].max(), 5000000000
        )

        return {
            "fiscal_years": fiscal_years,
            "appropriation_adjusted_nnsi": df["Appropriation_adjusted_nnsi"],
            "white_house_budget_projection": df["White House Budget Projection"],
            "xlim": (datetime(1958, 1, 1), datetime(x_limit, 1, 1)),
            "ylim": {"bottom": 0, "top": y_limit},
            "legend": {"loc": "lower right"},
            "export_df": export_df,
        }

    def nasa_science_by_year_inflation_adjusted_fy2026_threat(self):
        """Prepare historical NASA Science budget chart data."""
        # Get data from model
        self.data_source = Science()
        df = self.data_source.data()  # Drop rows without directorate data

        # Prepare data for view
        congressional_cutoff = pd.Timestamp(f"{self.CONGRESSIONAL_CUTOFF_YEAR}-01-01")
        congressional_mask = df["Fiscal Year"] > congressional_cutoff
        for col in ["NASA Science", "NASA Science_adjusted_nnsi"]:
            if col in df.columns:
                df.loc[congressional_mask, col] = pd.NA

        fiscal_years = df[
            df["Fiscal Year"] <= pd.to_datetime(f"{self.PRESIDENTIAL_REQUEST_YEAR_START}-01-01")
        ]["Fiscal Year"]

        # Prepare cleaned data for export
        export_df = self._export_helper(
            df, ["Fiscal Year", "NASA Science", "NASA Science_adjusted_nnsi", "FY 2026 PBR"]
        )

        x_limit = 2030
        y_limit = self._get_rounded_axis_limit_y(
            df["NASA Science_adjusted_nnsi"].max(), 5_000_000_000
        )

        return {
            "fiscal_years": fiscal_years,
            "nasa_science_adjusted_nnsi": df["NASA Science_adjusted_nnsi"],
            "fy_2026_pbr": df["FY 2026 PBR"],
            "xlim": (datetime(1980, 1, 1), datetime(x_limit, 1, 1)),
            "ylim": (0, y_limit),
            "legend": {"loc": "lower right"},
            "export_df": export_df,
        }

    def nasa_science_divisions_quad_plot_fy2026_threat(self):
        """Prepare quad plot data for NASA's four science divisions."""
        # Load ScienceDivisions data
        self.data_source = ScienceDivisions()
        df = self.data_source.data()

        # Filter data from 1990 to 2025
        df_filtered = df[
            (df["Fiscal Year"] >= pd.to_datetime("1990-01-01"))
            & (df["Fiscal Year"] <= pd.to_datetime("2025-01-01"))
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
                df_filtered.loc[mask_2025, proposed_col] = df_filtered.loc[
                    mask_2025, adjusted_col
                ].values[0]

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
                "Heliophysics Proposed": 432_500_000,
            }

            # Append the new row
            df_filtered = pd.concat([df_filtered, pd.DataFrame([new_row])], ignore_index=True)

        # Sort by fiscal year to ensure proper ordering
        df_filtered = df_filtered.sort_values("Fiscal Year")

        # Prepare data for each subplot
        subplot_data = []
        colors = [ChartView.COLORS["blue"], ChartView.TPS_COLORS["Rocket Flame"]]

        for division in divisions:
            # Get fiscal years
            fiscal_years = df_filtered["Fiscal Year"]

            # Get adjusted values (historical data)
            adjusted_values = df_filtered[f"{division}_adjusted_nnsi"]

            # Get proposed values (only for 2025-2026)
            proposed_values = df_filtered[f"{division} Proposed"]

            subplot_data.append(
                {
                    "x": fiscal_years,
                    "y": [adjusted_values, proposed_values],
                    "title": division,
                    "labels": ["Division funding", "Proposed"],
                    "colors": colors,
                    "linestyles": ["-", "-"],
                    "markers": ["", "o"],
                    "linewidths": [3, 3],
                }
            )

        # Calculate y-axis limit based on max value across all divisions
        max_value = 0
        for division in divisions:
            div_max = df_filtered[f"{division}_adjusted_nnsi"].max()
            if not pd.isna(div_max):
                max_value = max(max_value, div_max)

        y_limit = self._get_rounded_axis_limit_y(
            max_value, 1_000_000_000
        )  # Round to nearest billion

        # Prepare export data
        export_columns = ["Fiscal Year"]
        for division in divisions:
            export_columns.extend([division, f"{division}_adjusted_nnsi", f"{division} Proposed"])
        export_df = self._export_helper(df_filtered, export_columns)
        return {
            "subplot_data": subplot_data,
            "grid_shape": (2, 2),
            "xlim": (pd.to_datetime("1990-01-01"), pd.to_datetime("2030-01-01")),
            "ylim": (0, y_limit),
            "scale": "billions",
            "shared_x": False,
            "shared_y": False,
            "shared_legend": True,
            "legend": True,
            "subplot_title_size": 14,
            "export_df": export_df,
        }

    def cancelled_missions_lollipop_chart(self):
        """
        Prepare a lollipop chart showing the launch date to end of all NASA missions
        proposed as cancelled in FY 2026.
        """
        data_source = Missions()
        df = data_source.data()

        # Add explicit cancellation date
        df["Cancellation Date"] = datetime(2026, 1, 1)

        df["Launch Year"] = df["Launch Date"].dt.year
        df["End Year"] = df["Cancellation Date"].dt.year
        # Safely extract year, accounting for NaT/NaN values
        df["Formulation Start Year"] = df["Formulation Start"].apply(
            lambda x: pd.to_datetime(x).year if pd.notnull(x) else pd.NA
        )

        # Calculate 'Duration (years)' only for valid rows
        df["Duration (years)"] = pd.to_numeric(
            df["End Year"] - df["Launch Year"], errors="coerce"
        ).fillna(0)

        df["Development Time (years)"] = pd.to_numeric(
            df["Launch Year"] - df["Formulation Start Year"], errors="coerce"
        ).fillna(0)

        # Filter by only NASA-led missions
        df = df[df["NASA Led?"].isin([True])]

        # Filter to active missions led by NASA
        df = df[df["Status"].isin(["Prime Mission", "Extended Mission"])]

        total_development_time = round(df["Development Time (years)"].sum())
        total_value = self.round_to_millions(df["LCC"].sum())
        total_projects = len(df)

        # Rename every mission to just use the values if parentheses (if present)
        # If the mission name contains parentheses, extract the text inside; otherwise, keep the original name
        df["Mission"] = (
            df["Mission"].str.extract(r"\(([^)]+)\)", expand=False).fillna(df["Mission"])
        )

        # Prepare export data
        export_df = df.copy().drop(columns=["NASA Led?"])

        return {
            "categories": df["Mission"],
            "start_values": df["Launch Year"],
            "end_values": df["End Year"],
            "xlim": (1997, 2027),
            "export_df": export_df,
            "total_projects": total_projects,
            "total_value": total_value,
            "total_development_time": total_development_time,
        }

    def nasa_center_workforce_map(self):
        """Prepare a map showing workforce breakdown at NASA centers."""

        pie_data = {
            "HQ": {
                "values": [1366, 475],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "ARC": {
                "values": [755, 470],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "AFRC": {
                "values": [309, 191],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "GRC": {
                "values": [837, 554],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "GSFC": {
                "values": [1549, 1335],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "JSC": {
                "values": [2594, 698],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "KSC": {
                "values": [1506, 510],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "LaRC": {
                "values": [1058, 672],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "MSFC": {
                "values": [1714, 526],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
            "SSC": {
                "values": [166, 108],
                "labels": ["Workforce Remaining", "Proposed Staff Cuts"],
                "colors": ["#037CC2", "#FF5D47"],
            },
        }

        # Create export data
        export_data = []
        for center, data in pie_data.items():
            fy2025_staffing = sum(data["values"])
            proposed_fy2026_staffing = data["values"][0]
            export_data.append(
                {
                    "NASA Center": center,
                    "FY 2025 Staffing": fy2025_staffing,
                    "Proposed FY 2026 Staffing": proposed_fy2026_staffing,
                }
            )

        export_df = pd.DataFrame(export_data)

        return {
            "pie_data": pie_data,
            "export_df": export_df,
        }

    def fy2026_nasa_workforce_projections(self):
        df = Workforce().data()

        # Limit fiscal years to those through FY 2025
        fiscal_years = df[df["Fiscal Year"] <= pd.to_datetime("2026-01-01")]["Fiscal Year"]

        # Convert strings with commans into integers before plotting
        for col in ["Full-time Permanent (FTP)", "Full-time Equivalent (FTE)"]:
            if col in df.columns:
                # Remove commas and convert to int
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""), errors="coerce"
                ).astype("Int64")

        # Add a column for FY2026 Projection with projected workforce size for FY 2026
        df["FY2026 Projection"] = np.where(
            df["Fiscal Year"] == pd.to_datetime("2026-01-01"), 11853, np.nan
        )

        # Copy Workforce value for 2025-01-01 to the Projection column to ensure clean ploting
        df.loc[df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "FY2026 Projection"] = df.loc[
            df["Fiscal Year"] == pd.to_datetime("2025-01-01"), "Full-time Equivalent (FTE)"
        ]

        # Prepare cleaned export data for CSV
        export_df = self._export_helper(
            df, ["Fiscal Year", "Full-time Equivalent (FTE)", "FY2026 Projection"]
        )

        # Set x limit to be the the nearest multiple of 10 of x_min greater than x_max
        x_limit = 2027
        y_limit = 40_000

        return {
            "fiscal_years": fiscal_years,
            "fte": df["Full-time Equivalent (FTE)"],
            "fy2026_projection": df["FY2026 Projection"],
            "xlim": (datetime(1958, 1, 1), datetime(x_limit, 1, 1)),
            "ylim": {"bottom": 0, "top": y_limit},
            "legend": {"loc": "lower right"},
            "export_df": export_df,
        }

    def directorate_changes_stacked_bar_chart(self):
        """Prepare stacked bar chart comparing directorate changes."""
        df = Directorates().data()

        # Remove any column from df that has "(2025)" in the column name
        df = df[[col for col in df.columns if all(x not in col for x in ["(2025)", "gdp", "nnsi"])]]

        # Filter the DataFrame to just FY2025/26
        year_df = df[
            df["Fiscal Year"].dt.year == (datetime(2025, 1, 1).year or datetime(2026, 1, 1).year)
        ]

        # Sample data - Mission costs by category
        categories = [col for col in year_df.columns if "Fiscal Year" not in col]
        # Rename categories using the provided mapping
        category_rename = {
            "Aeronautics": "Aero",
            "Deep Space Exploration Systems": "Exploration",
            "LEO Space Operations": "Space Ops",
            "Space Technology": "Tech",
            "Science": "Science",
            "STEM Education": "STEM",
            "Facilities, IT, & Salaries": "SSMS/CECR",
        }
        categories = [category_rename.get(cat, cat) for cat in categories]
        # Calculate difference between FY 2025 and 2026:
        fy2025_row = df[df["Fiscal Year"].dt.year == datetime(2025, 1, 1).year].iloc[0]
        fy2026_row = df[df["Fiscal Year"].dt.year == datetime(2026, 1, 1).year].iloc[0]
        [-(fy2026_row[col] - fy2025_row[col]) for col in df.columns if col not in ["Fiscal Year"]]
        # Remove "Fiscal Year" from the data rows
        [fy2025_row[col] for col in df.columns if col != "Fiscal Year"]
        fy2026_values = [fy2026_row[col] for col in df.columns if col != "Fiscal Year"]
        diff_values = [
            -(fy2026_row[col] - fy2025_row[col]) if (fy2026_row[col] - fy2025_row[col]) < 0 else 0
            for col in df.columns
            if col != "Fiscal Year"
        ]
        # Sort fy2026_values from large to small, and apply the same order to diff_values and categories
        sorted_indices = np.argsort(fy2026_values)[::-1]
        fy2026_values = [fy2026_values[i] for i in sorted_indices]
        diff_values = [diff_values[i] for i in sorted_indices]
        categories = [categories[i] for i in sorted_indices]
        data = {"FY26": fy2026_values, "FY26 Diff": diff_values}

        # Create an exportable dataframe of categories and fy2025 and 2026 values
        export_df = pd.DataFrame(
            {
                "Category": categories,
                "FY2025": [fy2025_row[col] for col in df.columns if col != "Fiscal Year"],
                "FY2026": fy2026_values,
            }
        )

        return {
            "categories": categories,
            "values": data,
            "export_df": export_df,
        }

    def fy2026_budget_relative_proposed_change(self):
        df = Historical().data().dropna(subset=["PBR"])
        congressional_cutoff = pd.Timestamp(f"{self.CONGRESSIONAL_CUTOFF_YEAR}-01-01")
        congressional_mask = df["Fiscal Year"] > congressional_cutoff
        if "Appropriation" in df.columns:
            df.loc[congressional_mask, "Appropriation"] = pd.NA

        request_mask = df["Fiscal Year"].dt.year.between(
            self.PRESIDENTIAL_REQUEST_YEAR_START, self.PRESIDENTIAL_REQUEST_YEAR_END
        )
        df.loc[request_mask, "PBR"] = self.PRESIDENTIAL_REQUEST_VALUE

        df = df[df["Fiscal Year"] <= pd.to_datetime(f"{self.PRESIDENTIAL_REQUEST_YEAR_END}-01-01")]

        # Calculate relative change of PBR to prior year's appropriations
        df = df.sort_values("Fiscal Year").reset_index(drop=True)
        df["Prior Year Appropriation"] = df["Appropriation"].shift(1)
        df["Relative Change"] = (
            (df["PBR"] - df["Prior Year Appropriation"]) / df["Prior Year Appropriation"]
        ) * 100

        # Remove 1959 since there is no prior comparison
        df = df[df["Fiscal Year"] != datetime(1959, 1, 1)]

        # Add empty rows to 2030 for display purposes
        new_rows = pd.DataFrame(
            {
                "Fiscal Year": [
                    datetime(2027, 1, 1),
                    datetime(2028, 1, 1),
                    datetime(2029, 1, 1),
                    datetime(2030, 1, 1),
                ],
                "Relative Change": [0, 0, 0, 0],
            }
        )
        df = (
            pd.concat([df, new_rows], ignore_index=True)
            .sort_values("Fiscal Year")
            .reset_index(drop=True)
        )
        # Set fiscal years from
        fiscal_years = [
            str(round(val, 0)) if pd.notnull(val) else val
            for val in df["Fiscal Year"].dt.year.to_list()
        ]
        values = [
            round(val, 1) if pd.notnull(val) else val for val in df["Relative Change"].to_list()
        ]

        # Create Export df
        export_df = pd.DataFrame(
            {
                "Fiscal Year": fiscal_years[:-4],  # remove placeholder values for data output
                "Relative Change (%)": values[:-4],
            }
        )

        return {
            "categories": df["Fiscal Year"],
            "values": values,
            "export_df": export_df,
        }

    def congressional_vs_white_house_nasa_budget_stacked_bar_chart(self):
        """Prepare stacked bar chart comparing NASA budget proposals."""

        # These data are fixed for the FY 2026 budget request, so let's hardcode them here

        categories = ["PBR", "House", "Senate"]

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

        data = {"NASA": [18_800_000_000, 24_838_300_000, 24_899_700_000]}

        # Create an exportable dataframe of categories and fy2025 and 2026 values
        export_df = pd.DataFrame(
            {
                "Proposal": categories,
                "NASA FY 2026": data["NASA"],
            }
        )

        return {
            "categories": categories,
            "values": data,
            "export_df": export_df,
        }

    def new_grants_awards_comparison_to_prior_years(self):
        """Track FY 2026 grant awards compared to prior fiscal years."""
        # Use the generalized award data processor
        processor = AwardDataProcessor(
            fy_config=self.fy2026_award_config,
            award_type="Grant",
        )
        df = NewNASAAwards().data()
        data = processor.process(df)
        return data

    def new_contract_awards_comparison_to_prior_years(self):
        """Track FY 2026 contract awards compared to prior fiscal years."""
        # Use the generalized award data processor
        processor = AwardDataProcessor(
            fy_config=self.fy2026_award_config,
            award_type="Contract",
        )
        df = NewNASAAwards().data()
        data = processor.process(df)
        return data
