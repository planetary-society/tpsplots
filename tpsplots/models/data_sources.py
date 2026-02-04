"""Data source configuration models (v2.0 spec)."""

from typing import Literal

from pydantic import BaseModel, Field


class CurrencyCleaningConfig(BaseModel):
    """Configuration for auto-cleaning currency columns.

    Extends the simple boolean auto_clean_currency to support a multiplier.
    """

    enabled: bool = Field(default=True, description="Enable currency cleaning")
    multiplier: float = Field(
        default=1.0,
        description="Scale factor to apply after cleaning (e.g., 1000000 to convert millions to dollars)",
    )


class DataSourceParams(BaseModel):
    """Parameters for URL/CSV data sources.

    These parameters are passed to the underlying data controller
    (GoogleSheetsController or CSVController) to customize data loading.
    """

    columns: list[str] | None = Field(
        default=None, description="Columns to keep from the data source"
    )
    cast: dict[str, str] | None = Field(
        default=None,
        description="Column type overrides (e.g., {'Date': 'datetime', 'ID': 'str'})",
    )
    renames: dict[str, str] | None = Field(
        default=None, description="Column renames (e.g., {'Old Name': 'New Name'})"
    )
    auto_clean_currency: bool | CurrencyCleaningConfig | None = Field(
        default=None,
        description="Auto-detect and clean currency columns. Can be bool or config with multiplier.",
    )
    fiscal_year_column: str | bool | None = Field(
        default=None,
        description=(
            "Column to convert to datetime. None=auto-detect (Fiscal Year, FY, Year), "
            "str=column name, False=disable"
        ),
    )


class InflationConfig(BaseModel):
    """Configuration for inflation adjustment.

    Applies inflation adjustment to specified columns after data loading.
    Creates new columns named {column}_adjusted_{type} (e.g., Apollo_adjusted_nnsi).
    """

    columns: list[str] = Field(..., description="Columns to adjust for inflation")
    type: Literal["nnsi", "gdp"] = Field(
        default="nnsi", description="Inflation adjustment type (nnsi or gdp)"
    )
    fiscal_year_column: str = Field(
        default="Fiscal Year", description="Column containing fiscal year for each row"
    )
    target_year: int | None = Field(
        default=None, description="FY to adjust to (default: auto-calculate prior FY)"
    )


class DataSourceConfig(BaseModel):
    """Data source configuration using a single source string.

    Supports optional params for customizing data loading and
    calculate_inflation for applying inflation adjustments.

    Example YAML:
        data:
          source: https://docs.google.com/spreadsheets/d/.../export?format=csv
          params:
            columns:
              - "Fiscal Year"
              - "Apollo"
            cast:
              Fiscal Year: int
          calculate_inflation:
            columns:
              - "Apollo"
            type: nnsi
    """

    source: str = Field(..., description="Data source string")
    params: DataSourceParams | None = Field(
        default=None, description="Parameters for URL/CSV sources"
    )
    calculate_inflation: InflationConfig | None = Field(
        default=None, description="Inflation adjustment configuration"
    )


# Alias for backward compatibility with internal imports
DataSource = DataSourceConfig
