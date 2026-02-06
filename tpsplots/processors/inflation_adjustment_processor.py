"""Processor for applying inflation adjustments to monetary columns."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from tpsplots.data_sources.inflation import GDP, NNSI


def _calculate_prior_fy() -> int:
    """Calculate the prior fiscal year based on current date.

    Federal fiscal years run Oct 1 - Sep 30.
    If we're in Oct-Dec, current FY = current_year + 1.
    Otherwise, current FY = current_year.
    Prior FY = current FY - 1.

    Returns:
        The prior fiscal year as an integer.
    """
    today = datetime.now()
    current_fy = today.year + 1 if today.month >= 10 else today.year
    return current_fy - 1


@dataclass
class InflationAdjustmentConfig:
    """Configuration for inflation adjustment processing.

    Supports independent NNSI and GDP adjustments. You can specify columns
    for either or both adjustment types.

    Attributes:
        target_year: FY to adjust to (e.g., 2025). If None, defaults to prior FY.
        nnsi_columns: Columns to adjust using NNSI (creates {col}_adjusted_nnsi)
        gdp_columns: Columns to adjust using GDP deflator (creates {col}_adjusted_gdp)
        fiscal_year_column: Column containing fiscal year for each row
    """

    target_year: int | None = None  # None = auto-calculate prior FY
    nnsi_columns: list[str] | None = None  # Columns for NNSI adjustment
    gdp_columns: list[str] | None = None  # Columns for GDP adjustment
    fiscal_year_column: str = "Fiscal Year"  # Column containing fiscal year

    def __post_init__(self):
        """Resolve target_year if not specified."""
        if self.target_year is None:
            self.target_year = _calculate_prior_fy()
        # Convert None lists to empty lists for easier iteration
        if self.nnsi_columns is None:
            self.nnsi_columns = []
        if self.gdp_columns is None:
            self.gdp_columns = []


class InflationAdjustmentProcessor:
    """Applies inflation adjustment to specified monetary columns.

    Creates new columns with adjusted values using NNSI and/or GDP deflator.
    Returns DataFrame (not dict) to enable pipeline chaining.

    Supports applying NNSI and GDP adjustments independently to different
    columns in a single pass.

    Example - NNSI only:
        config = InflationAdjustmentConfig(
            nnsi_columns=["PBR", "Appropriation"]
        )
        df = InflationAdjustmentProcessor(config).process(df)
        # Creates: PBR_adjusted_nnsi, Appropriation_adjusted_nnsi
        # target_year auto-calculated from current date

    Example - Both NNSI and GDP:
        config = InflationAdjustmentConfig(
            target_year=2025,
            nnsi_columns=["PBR", "Appropriation"],
            gdp_columns=["PBR", "Appropriation"]
        )
        df = InflationAdjustmentProcessor(config).process(df)
        # Creates: PBR_adjusted_nnsi, Appropriation_adjusted_nnsi,
        #          PBR_adjusted_gdp, Appropriation_adjusted_gdp
    """

    def __init__(self, config: InflationAdjustmentConfig | None = None):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying target year and columns to adjust.
                   If None, creates default config (no columns, auto target year).
        """
        self.config = config or InflationAdjustmentConfig()
        self._nnsi: NNSI | None = None
        self._gdp: GDP | None = None

        # Lazy-load inflation adjusters only when needed
        if self.config.nnsi_columns:
            self._nnsi = NNSI(year=str(self.config.target_year))
        if self.config.gdp_columns:
            self._gdp = GDP(year=str(self.config.target_year))

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply inflation adjustment to configured columns.

        Creates new columns named {col}_adjusted_nnsi and/or {col}_adjusted_gdp
        for each column specified in the config.

        Columns not found in the DataFrame are silently skipped (no error).
        NaN values in the original column produce NaN in the adjusted column.

        Args:
            df: DataFrame with fiscal year and monetary columns

        Returns:
            DataFrame with added inflation-adjusted columns and
            inflation_target_year stored in attrs
        """
        df = df.copy()
        fy_col = self.config.fiscal_year_column

        # Apply NNSI adjustments
        if self._nnsi and self.config.nnsi_columns:
            for col in self.config.nnsi_columns:
                if col not in df.columns:
                    continue
                output_col = f"{col}_adjusted_nnsi"
                df[output_col] = df.apply(
                    lambda row, c=col: (
                        self._nnsi.calc(row[fy_col], row[c]) if pd.notna(row[c]) else np.nan
                    ),
                    axis=1,
                )

        # Apply GDP adjustments
        if self._gdp and self.config.gdp_columns:
            for col in self.config.gdp_columns:
                if col not in df.columns:
                    continue
                output_col = f"{col}_adjusted_gdp"
                df[output_col] = df.apply(
                    lambda row, c=col: (
                        self._gdp.calc(row[fy_col], row[c]) if pd.notna(row[c]) else np.nan
                    ),
                    axis=1,
                )

        # Store metadata in attrs for downstream processors
        df.attrs["inflation_target_year"] = self.config.target_year

        return df
