"""Processor for workforce data with projection values."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class WorkforceProjectionConfig:
    """Configuration for workforce projection processing.

    Attributes:
        fiscal_year: Target fiscal year for the projection
        projection_value: The projected workforce value for the target FY.
            If None, no projection is applied and source data is shown as-is.
        source_column: Column name containing historical workforce data
        projection_column: Column name for the projection series
    """

    fiscal_year: int
    projection_value: int | None = None
    source_column: str = "Full-time Equivalent (FTE)"
    projection_column: str = "Workforce Projection"


class WorkforceProjectionProcessor:
    """Processes workforce data with optional projection values.

    When projection_value is provided, this processor:
    1. Filters data to include only years through the target fiscal year
    2. Clears the source column at target FY (overrides with projection)
    3. Creates a projection series connecting FY-1 actual to FY projection
    4. Stores metadata in DataFrame.attrs for downstream use

    When projection_value is None:
    1. Filters data through target FY
    2. Returns data as-is (no projection column added)
    """

    def __init__(self, config: WorkforceProjectionConfig):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying fiscal year and optional projection value.
        """
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process workforce data to add optional projection series.

        Args:
            df: DataFrame with Fiscal Year and workforce columns

        Returns:
            DataFrame with projection column added (if projection_value set)
            and metadata in attrs
        """
        df = df.copy()
        fy = self.config.fiscal_year
        fy_datetime = datetime(fy, 1, 1)
        prior_fy_datetime = datetime(fy - 1, 1, 1)
        source_col = self.config.source_column

        # Step 1: Filter to fiscal years through target FY
        df = df[df["Fiscal Year"] <= fy_datetime].copy()

        # Store base metadata
        df.attrs["fiscal_year"] = fy
        df.attrs["xlim"] = (datetime(1958, 1, 1), datetime(fy + 1, 1, 1))
        df.attrs["ylim"] = {"bottom": 0, "top": 40_000}

        # If no projection value, return data as-is
        if self.config.projection_value is None:
            return df

        # Step 2: Clear source column at target FY (projection overrides actual)
        fy_mask = df["Fiscal Year"] == fy_datetime
        if fy_mask.any() and source_col in df.columns:
            df.loc[fy_mask, source_col] = np.nan

        # Step 3: Initialize projection column with NaN
        projection_col = self.config.projection_column
        df[projection_col] = np.nan

        # Step 4: Set projection value at target FY
        if fy_mask.any():
            df.loc[fy_mask, projection_col] = self.config.projection_value

        # Step 5: Connect to FY-1 actual (for clean line plotting)
        prior_fy_mask = df["Fiscal Year"] == prior_fy_datetime
        if prior_fy_mask.any() and source_col in df.columns:
            prior_value = df.loc[prior_fy_mask, source_col].values[0]
            df.loc[prior_fy_mask, projection_col] = prior_value

        # Store projection metadata
        df.attrs["projection_value"] = self.config.projection_value

        return df
