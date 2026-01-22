"""Processor for budget data with PBR and runout projections."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class BudgetProjectionConfig:
    """Configuration for budget projection processing.

    This config determines how the processor extracts and merges budget data:
    - At NASA top-line level: uses "Total", "Appropriation", "PBR"
    - At directorate level (e.g., Science): uses "Science", "Science"
    - At division level (e.g., Astrophysics): uses "Astrophysics", "Astrophysics Proposed"
    """

    fiscal_year: int
    inflation_target_year: int | None = None  # Defaults to FY-1

    # Budget detail extraction - which row to extract from budget_detail
    budget_detail_row_name: str = "Total"  # "Total" | "Science" | "Astrophysics" etc.

    # Column mapping for historical data
    appropriation_column: str = "Appropriation"
    pbr_column: str = "PBR"

    # Runout config
    runout_years: int = 4

    def __post_init__(self):
        if self.inflation_target_year is None:
            self.inflation_target_year = self.fiscal_year - 1

    @property
    def pbr_request_column(self) -> str:
        """Column name for the PBR request in budget detail."""
        return f"FY {self.fiscal_year} Request"

    @property
    def runout_columns(self) -> list[str]:
        """Column names for runout years in budget detail."""
        return [f"FY {self.fiscal_year + n}" for n in range(1, self.runout_years + 1)]


class BudgetProjectionProcessor:
    """Processes historical budget data with PBR and runout projections.

    This processor "grafts" Presidential Budget Request (PBR) data and multi-year
    runout projections onto historical appropriation data. It creates a "White House
    Budget Projection" series that connects to the historical appropriation line
    at FY-1 and extends through the runout period.

    The processor works at different budget hierarchy levels:
    - NASA top-line (Total)
    - Directorate level (Science, Exploration, etc.)
    - Division level (Astrophysics, Planetary Science, etc.)
    """

    def __init__(self, config: BudgetProjectionConfig):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying fiscal year, column mappings,
                   and budget detail extraction parameters.
        """
        self.config = config

    def process(
        self,
        historical_df: pd.DataFrame,
        budget_detail_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Process historical and budget detail data into a DataFrame.

        The processing pipeline:
        1. Extract PBR + runout values from budget_detail
        2. Graft PBR value onto current FY
        3. Clear future appropriations (FY >= current)
        4. Build White House Projection series

        Note: Inflation adjustment is NOT applied by this processor.
        Use InflationAdjustmentProcessor explicitly in controllers before
        or after calling this processor.

        This processor focuses on data grafting only. For calculated columns
        (like YoY changes), use CalculatedColumnProcessor. For conversion to
        YAML-ready dict, use DataFrameToYAMLProcessor.

        Args:
            historical_df: DataFrame with Fiscal Year, appropriation, and PBR columns
            budget_detail_df: DataFrame with budget detail rows including PBR and runout

        Returns:
            DataFrame with columns: Fiscal Year, PBR, Appropriation,
            White House Budget Projection
        """
        df = historical_df.copy()
        fy = self.config.fiscal_year
        fy_datetime = datetime(fy, 1, 1)

        # Step 1: Extract PBR and runout from budget detail
        pbr_value, runout_dict = self._extract_budget_detail(budget_detail_df)

        # Step 2: Graft PBR value onto current FY
        df = self._graft_pbr_value(df, pbr_value, fy_datetime)

        # Step 3: Clear future appropriations
        df = self._clear_future_appropriations(df, fy_datetime)

        # Step 4: Build projection series
        df = self._build_projection_series(df, pbr_value, runout_dict, fy_datetime)

        # Store config metadata in DataFrame attrs for downstream processors
        df.attrs["fiscal_year"] = fy
        df.attrs["inflation_target_year"] = self.config.inflation_target_year
        df.attrs["pbr_column"] = self.config.pbr_column
        df.attrs["appropriation_column"] = self.config.appropriation_column
        df.attrs["current_pbr_request"] = pbr_value

        return df

    def _extract_budget_detail(
        self, budget_detail_df: pd.DataFrame
    ) -> tuple[float, dict[int, float]]:
        """Extract PBR request and runout values from budget detail.

        Args:
            budget_detail_df: DataFrame with budget detail rows

        Returns:
            Tuple of (pbr_value, runout_dict) where runout_dict maps FY -> value

        Raises:
            ValueError: If required row or column not found
        """
        row_name = self.config.budget_detail_row_name
        detail_row = budget_detail_df[budget_detail_df.iloc[:, 0] == row_name]

        if detail_row.empty:
            raise ValueError(f"No '{row_name}' row found in budget detail data")

        # Get PBR request value
        pbr_col = self.config.pbr_request_column
        if pbr_col not in detail_row.columns:
            raise ValueError(f"Column '{pbr_col}' not found in budget detail")
        pbr_value = detail_row[pbr_col].values[0]

        # Get runout values
        runout_dict = {}
        for runout_col in self.config.runout_columns:
            if runout_col in detail_row.columns:
                runout_fy = int(runout_col.split(" ")[1])
                runout_dict[runout_fy] = detail_row[runout_col].values[0]

        return pbr_value, runout_dict

    def _graft_pbr_value(
        self, df: pd.DataFrame, pbr_value: float, fy_datetime: datetime
    ) -> pd.DataFrame:
        """Update or insert PBR value for current fiscal year.

        Args:
            df: DataFrame with fiscal year and PBR column
            pbr_value: The PBR value to graft
            fy_datetime: Current fiscal year as datetime

        Returns:
            DataFrame with grafted PBR value
        """
        pbr_col = self.config.pbr_column

        if pbr_col not in df.columns:
            df[pbr_col] = np.nan

        fy_mask = df["Fiscal Year"] == fy_datetime
        if fy_mask.any():
            df.loc[fy_mask, pbr_col] = pbr_value
        else:
            new_row = pd.DataFrame({"Fiscal Year": [fy_datetime], pbr_col: [pbr_value]})
            df = pd.concat([df, new_row], ignore_index=True)
            df = df.sort_values("Fiscal Year").reset_index(drop=True)

        return df

    def _clear_future_appropriations(self, df: pd.DataFrame, fy_datetime: datetime) -> pd.DataFrame:
        """Set appropriation to NaN for current and future fiscal years.

        Args:
            df: DataFrame with fiscal year and appropriation column
            fy_datetime: Current fiscal year as datetime

        Returns:
            DataFrame with cleared future appropriations
        """
        appropriation_col = self.config.appropriation_column

        if appropriation_col not in df.columns:
            return df

        future_mask = df["Fiscal Year"] >= fy_datetime
        df.loc[future_mask, appropriation_col] = np.nan

        return df

    def _build_projection_series(
        self,
        df: pd.DataFrame,
        pbr_value: float,
        runout_dict: dict[int, float],
        fy_datetime: datetime,
    ) -> pd.DataFrame:
        """Build White House Budget Projection series.

        The projection series:
        1. Connects to FY-1 appropriation (creates visual continuity)
        2. Shows current FY PBR request
        3. Extends through runout years

        Args:
            df: DataFrame with fiscal year data
            pbr_value: Current FY PBR request value
            runout_dict: Mapping of future FY -> projected value
            fy_datetime: Current fiscal year as datetime

        Returns:
            DataFrame with White House Budget Projection column
        """
        fy = self.config.fiscal_year
        appropriation_col = self.config.appropriation_column

        # Initialize projection column
        df["White House Budget Projection"] = np.nan

        # Set FY-1 projection to its appropriation (connection point)
        prior_fy_datetime = datetime(fy - 1, 1, 1)
        prior_fy_mask = df["Fiscal Year"] == prior_fy_datetime
        if prior_fy_mask.any() and appropriation_col in df.columns:
            prior_appropriation = df.loc[prior_fy_mask, appropriation_col].values[0]
            df.loc[prior_fy_mask, "White House Budget Projection"] = prior_appropriation

        # Set current FY projection to PBR value
        fy_mask = df["Fiscal Year"] == fy_datetime
        if fy_mask.any():
            df.loc[fy_mask, "White House Budget Projection"] = pbr_value

        # Set future FYs to runout values
        for runout_fy, runout_value in runout_dict.items():
            runout_datetime = datetime(runout_fy, 1, 1)
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
        return df
