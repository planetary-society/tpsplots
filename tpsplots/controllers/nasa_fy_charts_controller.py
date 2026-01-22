from datetime import datetime

import numpy as np
import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.data_sources.inflation import NNSI
from tpsplots.data_sources.nasa_budget_data_source import Historical
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig


class NASAFYChartsController(ChartController):
    def __init__(self):
        self.historical: pd.DataFrame = Historical().data()
        self.new_awards: pd.DataFrame = NewNASAAwards().data()
        if not hasattr(self, "FISCAL_YEAR"):
            raise ValueError("FISCAL_YEAR must be defined in the subclass")
        if not hasattr(self, "BUDGET_DETAIL_URL"):
            raise ValueError("BUDGET_DETAIL_URL must be defined in the subclass")
        self.budget_detail: pd.DataFrame = GoogleSheetsSource(self.BUDGET_DETAIL_URL).data()

        # Convert all columns except the first column to numeric, stripping any non-numeric characters
        for col in self.budget_detail.columns[1:]:
            self.budget_detail[col] = pd.to_numeric(
                self.budget_detail[col].astype(str).str.replace(r"[^\d.]", "", regex=True),
                errors="coerce",
            )
            self.budget_detail[col] = self.budget_detail[col] * 1_000_000

    # Methods for award tracking
    def _get_award_data(self, award_type: str = "Grant") -> dict:
        """Get processed award data using the generalized processor."""
        fy = self.FISCAL_YEAR
        fy_config = FiscalYearConfig(
            prior_years=[fy - 5, fy - 4, fy - 3, fy - 2, fy - 1],
            current_year=fy,
            comparison_year=fy - 1,
        )
        processor = AwardDataProcessor(
            fy_config=fy_config,
            award_type=award_type,
        )
        df = self.new_awards.data()
        return processor.process(df)

    def new_grants_awards_comparison_to_prior_year(self) -> dict:
        """Process grant award data for historical comparison."""
        return self._get_award_data(award_type="Grant")

    def new_contract_awards_comparison_to_prior_years(self) -> dict:
        """Process contract award data for historical comparison."""
        return self._get_award_data(award_type="Contract")

    def major_accounts(self) -> pd.DataFrame:
        """Returns NASA major accounts data for in-FY comparison."""
        data = self.budget_detail
        # Filter rows for matching major accounts names in first column
        if hasattr(self, "ACCOUNTS"):
            data = data[data.iloc[:, 0].isin(self.ACCOUNTS)]
        # Rename first column header to "Account"
        data = data.rename(columns={data.columns[0]: "Account"})

        return data

    def pbr_historical_context(self) -> dict:
        """Return historical budget data with current FY PBR and runout projections.

        Merges:
        1. Historical appropriation data (adjusted for inflation to FY-1)
        2. Current fiscal year PBR request from budget detail
        3. 4-year runout projections from budget detail

        Inflation adjustment uses FISCAL_YEAR - 1 as target year.

        Returns:
            dict with keys: fiscal_year, presidential_administration, pbr,
            appropriation, white_house_projection, pbr_adjusted,
            appropriation_adjusted, export_df, max_fiscal_year, source
        """
        df = self.historical.copy()
        fy = self.FISCAL_YEAR
        fy_datetime = datetime(fy, 1, 1)

        # Re-calculate inflation adjustment to FISCAL_YEAR - 1
        inflation_target = fy - 1
        nnsi = NNSI(year=str(inflation_target))
        for col in ["PBR", "Appropriation"]:
            if col in df.columns:
                df[f"{col}_adjusted_nnsi"] = df.apply(
                    lambda row, c=col: nnsi.calc(row["Fiscal Year"], row[c])
                    if pd.notna(row[c])
                    else np.nan,
                    axis=1,
                )

        # Extract total row from budget detail
        total_row = self.budget_detail[self.budget_detail.iloc[:, 0] == "Total"]
        if total_row.empty:
            raise ValueError("No 'Total' row found in budget detail data")

        # Column names in budget detail
        pbr_request_col = f"FY {fy} Request"
        runout_cols = [f"FY {fy + n}" for n in range(1, 5)]

        # Get PBR request value for current FY
        if pbr_request_col not in total_row.columns:
            raise ValueError(f"Column '{pbr_request_col}' not found in budget detail")
        pbr_value = total_row[pbr_request_col].values[0]

        # Update PBR column for current FY
        fy_mask = df["Fiscal Year"] == fy_datetime
        if fy_mask.any():
            df.loc[fy_mask, "PBR"] = pbr_value
        else:
            new_row = pd.DataFrame({"Fiscal Year": [fy_datetime], "PBR": [pbr_value]})
            df = pd.concat([df, new_row], ignore_index=True)
            df = df.sort_values("Fiscal Year").reset_index(drop=True)

        # Clear Appropriation for current and future FYs (FY >= current)
        future_mask = df["Fiscal Year"] >= fy_datetime
        df.loc[future_mask, "Appropriation"] = np.nan
        df.loc[future_mask, "Appropriation_adjusted_nnsi"] = np.nan

        # Build White House Budget Projection series:
        # 1. Clear all existing projection values
        # 2. Set FY-1 = prior year's appropriation (connection point)
        # 3. Set current FY = PBR value
        # 4. Set future FYs = runout values
        df["White House Budget Projection"] = np.nan

        # Set FY-1 projection to its appropriation value (creates connection to historical line)
        prior_fy_datetime = datetime(fy - 1, 1, 1)
        prior_fy_mask = df["Fiscal Year"] == prior_fy_datetime
        if prior_fy_mask.any():
            prior_appropriation = df.loc[prior_fy_mask, "Appropriation"].values[0]
            df.loc[prior_fy_mask, "White House Budget Projection"] = prior_appropriation

        # Set current FY projection to PBR value
        fy_mask = df["Fiscal Year"] == fy_datetime
        if fy_mask.any():
            df.loc[fy_mask, "White House Budget Projection"] = pbr_value

        # Set future FYs to runout values
        for runout_col in runout_cols:
            if runout_col in total_row.columns:
                runout_fy = int(runout_col.split(" ")[1])
                runout_datetime = datetime(runout_fy, 1, 1)
                runout_value = total_row[runout_col].values[0]

                runout_mask = df["Fiscal Year"] == runout_datetime
                if runout_mask.any():
                    df.loc[runout_mask, "White House Budget Projection"] = runout_value
                else:
                    new_row = pd.DataFrame(
                        {
                            "Fiscal Year": [runout_datetime],
                            "White House Budget Projection": [runout_value],
                        }
                    )
                    df = pd.concat([df, new_row], ignore_index=True)

        df = df.sort_values("Fiscal Year").reset_index(drop=True)

        # Prepare export data
        export_df = self._export_helper(
            df,
            [
                "Fiscal Year",
                "Presidential Administration",
                "PBR",
                "Appropriation",
                "White House Budget Projection",
                "PBR_adjusted_nnsi",
                "Appropriation_adjusted_nnsi",
            ],
        )

        max_fy = int(df["Fiscal Year"].max().strftime("%Y"))

        return {
            "fiscal_year": df["Fiscal Year"],
            "presidential_administration": df["Presidential Administration"],
            "pbr": df["PBR"],
            "appropriation": df["Appropriation"],
            "white_house_projection": df["White House Budget Projection"],
            "pbr_adjusted_nnsi": df["PBR_adjusted_nnsi"],
            "pbr_adjusted_gdp": df["PBR_adjusted_gdp"],
            "appropriation_adjusted_nnsi": df["Appropriation_adjusted_nnsi"],
            "appropriation_adjusted_gdp": df["Appropriation_adjusted_gdp"],
            "export_df": export_df,
            "max_fiscal_year": max_fy,
            "inflation_target_year": inflation_target,
        }
