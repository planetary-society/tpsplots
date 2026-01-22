"""Processor for adding calculated columns to DataFrames.

This processor computes derived values by comparing columns across fiscal years.
It uses a registry pattern for extensibility - new calculations can be added
via the @register_calculation decorator without modifying the processor class.

Example usage:
    config = CalculatedColumnConfig()
    config.add("YoY Change %", "percent_delta_from_prior", "PBR", "Appropriation")
    df = CalculatedColumnProcessor(config).process(df)
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Registry maps calculation name -> function
CALCULATION_REGISTRY: dict[str, Callable[[pd.Series, pd.Series], pd.Series]] = {}


def register_calculation(name: str):
    """Decorator to register a calculation function.

    Registered functions must accept two Series arguments:
    - current_values: Values from the current FY column
    - prior_values: Values from the prior FY column (already shifted)

    Args:
        name: Unique identifier for this calculation type

    Returns:
        Decorator function that registers the calculation
    """

    def decorator(func: Callable[[pd.Series, pd.Series], pd.Series]):
        CALCULATION_REGISTRY[name] = func
        return func

    return decorator


# Built-in calculation functions


@register_calculation("delta_from_prior")
def calc_delta_from_prior(current_values: pd.Series, prior_values: pd.Series) -> pd.Series:
    """Calculate absolute change: current_col[FY] - prior_col[FY-1].

    Args:
        current_values: Values for current fiscal year
        prior_values: Values for prior fiscal year (already shifted)

    Returns:
        Series with the difference
    """
    return current_values - prior_values


@register_calculation("percent_delta_from_prior")
def calc_percent_delta_from_prior(current_values: pd.Series, prior_values: pd.Series) -> pd.Series:
    """Calculate percentage change: (current - prior) / prior * 100.

    Handles division by zero and NaN values safely.

    Args:
        current_values: Values for current fiscal year
        prior_values: Values for prior fiscal year (already shifted)

    Returns:
        Series with percentage change (e.g., 25.0 for 25% increase)
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            (prior_values != 0) & pd.notna(prior_values) & pd.notna(current_values),
            ((current_values - prior_values) / prior_values) * 100,
            np.nan,
        )
    return pd.Series(result, index=current_values.index)


@dataclass
class ColumnCalculation:
    """Specification for a single calculated column.

    Attributes:
        output_column: Name of the new column to create
        calculation: Registry key (e.g., "delta_from_prior", "percent_delta_from_prior")
        current_fy_column: Column name for current FY value
        prior_fy_column: Column name for prior FY value (will be shifted by 1 row)
    """

    output_column: str
    calculation: str
    current_fy_column: str
    prior_fy_column: str


@dataclass
class CalculatedColumnConfig:
    """Configuration for CalculatedColumnProcessor.

    Attributes:
        fiscal_year_column: Name of the column containing fiscal year values
        calculations: List of ColumnCalculation specifications

    Example:
        config = CalculatedColumnConfig()
        config.add("Change %", "percent_delta_from_prior", "PBR", "Appropriation")
        config.add("Change $", "delta_from_prior", "PBR", "Appropriation")
    """

    fiscal_year_column: str = "Fiscal Year"
    calculations: list[ColumnCalculation] = field(default_factory=list)

    def add(
        self,
        output_column: str,
        calculation: str,
        current_fy_column: str,
        prior_fy_column: str,
    ) -> "CalculatedColumnConfig":
        """Add a calculation specification (fluent API).

        Args:
            output_column: Name of the new column to create
            calculation: Registry key for the calculation function
            current_fy_column: Column to use for current FY value
            prior_fy_column: Column to use for prior FY value (shifted)

        Returns:
            self for method chaining
        """
        self.calculations.append(
            ColumnCalculation(
                output_column=output_column,
                calculation=calculation,
                current_fy_column=current_fy_column,
                prior_fy_column=prior_fy_column,
            )
        )
        return self


class CalculatedColumnProcessor:
    """Adds calculated columns comparing values across fiscal years.

    This processor computes derived values by comparing column values
    between consecutive fiscal years (e.g., PBR[FY] vs Appropriation[FY-1]).

    Returns a DataFrame (not dict) to enable pipeline chaining:
        df = BudgetProjectionProcessor(config).process(historical, budget)
        df = CalculatedColumnProcessor(calc_config).process(df)
        result = DataFrameToYAMLProcessor().process(df)

    Example:
        config = CalculatedColumnConfig()
        config.add("YoY Change %", "percent_delta_from_prior", "PBR", "Appropriation")
        df = CalculatedColumnProcessor(config).process(df)
    """

    def __init__(self, config: CalculatedColumnConfig):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying which calculations to apply
        """
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all configured calculations to the DataFrame.

        Args:
            df: DataFrame with fiscal year column and source columns

        Returns:
            DataFrame with new calculated columns added
        """
        df = df.copy()
        df = df.sort_values(self.config.fiscal_year_column).reset_index(drop=True)

        for calc in self.config.calculations:
            df = self._apply_calculation(df, calc)

        return df

    def _apply_calculation(self, df: pd.DataFrame, calc: ColumnCalculation) -> pd.DataFrame:
        """Apply a single calculation.

        Args:
            df: DataFrame to modify
            calc: Calculation specification

        Returns:
            DataFrame with new column added

        Raises:
            ValueError: If calculation type is not registered
            KeyError: If source columns don't exist in DataFrame
        """
        if calc.calculation not in CALCULATION_REGISTRY:
            available = ", ".join(sorted(CALCULATION_REGISTRY.keys()))
            raise ValueError(
                f"Unknown calculation: '{calc.calculation}'. Available calculations: {available}"
            )

        if calc.current_fy_column not in df.columns:
            raise KeyError(
                f"Column '{calc.current_fy_column}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

        if calc.prior_fy_column not in df.columns:
            raise KeyError(
                f"Column '{calc.prior_fy_column}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

        calc_func = CALCULATION_REGISTRY[calc.calculation]

        current_values = df[calc.current_fy_column]
        prior_values = df[calc.prior_fy_column].shift(1)  # Align FY-1 with FY

        df[calc.output_column] = calc_func(current_values, prior_values)
        return df
