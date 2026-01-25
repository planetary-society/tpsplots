"""Processor for converting DataFrames to YAML-ready dictionaries.

This is the final processor in a pipeline - it takes a DataFrame and
converts it to a dict that can be consumed by YAML chart templates.

Example usage:
    df = BudgetProjectionProcessor(config).process(historical, budget)
    df = CalculatedColumnProcessor(calc_config).process(df)
    result = DataFrameToYAMLProcessor().process(df)
    # result is now a dict with snake_case keys for {{variable}} references
"""

import re
from dataclasses import dataclass

import pandas as pd


def to_snake_case(name: str) -> str:
    """Convert column name to snake_case key.

    Handles:
    - Spaces → underscores
    - CamelCase → snake_case
    - Acronyms preserved as single words (PBR → pbr, not p_b_r)
    - Special characters (%, $) → words

    Args:
        name: Column name to convert

    Returns:
        Snake case string suitable for YAML variable reference

    Examples:
        "Fiscal Year" → "fiscal_year"
        "White House Budget Projection" → "white_house_budget_projection"
        "PBR_adjusted_nnsi" → "pbr_adjusted_nnsi"
        "YoY Change %" → "yoy_change_percent"
        "Delta $" → "delta_dollars"
        "PBR" → "pbr"
    """
    # Replace common symbols with words
    result = name.replace("%", " percent").replace("$", " dollars")

    # Replace spaces with underscores
    result = result.replace(" ", "_")

    # Handle CamelCase: insert underscore before uppercase letters that follow lowercase
    # This preserves acronyms like "PBR" but handles "camelCase" → "camel_case"
    result = re.sub(r"([a-z])([A-Z])", r"\1_\2", result)

    # Handle acronyms followed by lowercase: "XMLParser" → "XML_Parser"
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)

    # Convert to lowercase and clean up multiple underscores
    result = result.lower()
    result = re.sub(r"_+", "_", result)
    result = result.strip("_")

    return result


@dataclass
class DataFrameToYAMLConfig:
    """Configuration for converting DataFrame to YAML-ready dict.

    Attributes:
        fiscal_year_column: Name of the fiscal year column
        columns_to_export: List of columns to include (None = all columns)
        export_df_key: Key name for the full DataFrame in output
        include_attrs: Whether to include DataFrame.attrs in output
        export_note_template: Template for export note (uses attrs values)
    """

    fiscal_year_column: str = "Fiscal Year"
    columns_to_export: list[str] | None = None
    export_df_key: str = "export_df"
    include_attrs: bool = True
    export_note_template: str | None = None
    clear_projection_before_fy: bool = True  # Clear projection for FY <= current FY


@dataclass
class ExportConfig:
    """Configuration for building export DataFrame.

    Attributes:
        columns: Columns to include in export (None = use parent config)
        clear_projection_column: Column to clear for FY <= current
        fiscal_year_column: Column containing fiscal year
    """

    columns: list[str] | None = None
    clear_projection_column: str = "White House Budget Projection"
    fiscal_year_column: str = "Fiscal Year"


class DataFrameToYAMLProcessor:
    """Converts DataFrame to dict for YAML template consumption.

    Final processor in the pipeline chain - takes DataFrame, returns dict.

    The output dict contains:
    - Each column as a snake_case key → Series
    - export_df → the DataFrame (for export_data in YAML)
    - Metadata from DataFrame.attrs (fiscal_year, inflation_target_year, etc.)

    Example:
        df = CalculatedColumnProcessor(calc_config).process(df)
        result = DataFrameToYAMLProcessor().process(df)
        # Access in YAML: {{fiscal_year}}, {{white_house_projection}}
    """

    def __init__(self, config: DataFrameToYAMLConfig | None = None):
        """Initialize the processor with configuration.

        Args:
            config: Configuration for the conversion. Defaults to standard settings.
        """
        self.config = config or DataFrameToYAMLConfig()

    def process(self, df: pd.DataFrame) -> dict:
        """Convert DataFrame to YAML-ready dict.

        Args:
            df: DataFrame with columns to convert to dict keys

        Returns:
            dict with:
                - Each column by its original name → Series
                - export_df → the full DataFrame
                - Metadata from DataFrame.attrs
        """
        result = {}

        # Determine which columns to export
        columns = self.config.columns_to_export or list(df.columns)

        # Convert each column to a dict entry (retain original column names)
        for col in columns:
            if col in df.columns:
                result[col] = df[col]

        # Build export DataFrame
        export_df = self._build_export_df(df)
        result[self.config.export_df_key] = export_df

        # Include DataFrame.attrs if configured
        if self.config.include_attrs:
            for key, value in df.attrs.items():
                # Don't overwrite column data with attrs
                if key not in result:
                    result[key] = value

        # Add computed metadata
        if self.config.fiscal_year_column in df.columns:
            max_fy = df[self.config.fiscal_year_column].max()
            if pd.notna(max_fy):
                if hasattr(max_fy, "strftime"):
                    result["max_fiscal_year"] = int(max_fy.strftime("%Y"))
                else:
                    result["max_fiscal_year"] = int(max_fy)

        return result

    def _build_export_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build DataFrame suitable for CSV export.

        Args:
            df: Source DataFrame

        Returns:
            DataFrame prepared for export with projection values cleared
            for historical years
        """
        # Select columns to export
        columns = self.config.columns_to_export or list(df.columns)
        export_df = df[[c for c in columns if c in df.columns]].copy()

        # Get fiscal year from attrs if available
        fy = df.attrs.get("fiscal_year")

        # Clear projection column for historical years (FY < current FY)
        if (
            self.config.clear_projection_before_fy
            and fy is not None
            and "White House Budget Projection" in export_df.columns
            and self.config.fiscal_year_column in export_df.columns
        ):
            fiscal_years = export_df[self.config.fiscal_year_column].apply(
                lambda x: x.year if hasattr(x, "year") else (int(x) if pd.notna(x) else pd.NA)
            )
            export_df.loc[fiscal_years < fy, "White House Budget Projection"] = pd.NA

        # Build export note
        export_note = self._build_export_note(df)
        if export_note:
            export_df.attrs["export_note"] = export_note

        return export_df

    def _build_export_note(self, df: pd.DataFrame) -> str | None:
        """Build export note from template and DataFrame attrs.

        Args:
            df: DataFrame with attrs

        Returns:
            Formatted export note string or None
        """
        if self.config.export_note_template:
            try:
                # Convert attrs to dict with str keys for format()
                attrs_dict = {str(k): v for k, v in df.attrs.items()}
                return self.config.export_note_template.format(**attrs_dict)
            except KeyError:
                # If template references missing keys, return partial note
                return self.config.export_note_template

        # Default export note if attrs have inflation info
        inflation_year = df.attrs.get("inflation_target_year")
        fy = df.attrs.get("fiscal_year")

        if inflation_year:
            note = f"Inflation adjusted to FY {inflation_year} dollars (NNSI)."

            # Add YoY change info if we can compute it
            # (This is a fallback - ideally the caller computes this)
            if fy and "current_pbr_request" in df.attrs:
                pbr = df.attrs.get("current_pbr_request")
                approx_col = df.attrs.get("appropriation_column", "Appropriation")

                # Try to find prior year appropriation
                if approx_col in df.columns and self.config.fiscal_year_column in df.columns:
                    from datetime import datetime

                    prior_fy_dt = datetime(fy - 1, 1, 1)
                    prior_mask = df[self.config.fiscal_year_column] == prior_fy_dt
                    if prior_mask.any():
                        prior_approp = df.loc[prior_mask, approx_col].values[0]
                        if pd.notna(prior_approp) and prior_approp != 0:
                            change_pct = ((pbr - prior_approp) / prior_approp) * 100
                            direction = "increase" if change_pct > 0 else "decrease"
                            note += (
                                f" FY {fy} PBR represents a {abs(change_pct):.1f}% "
                                f"{direction} from FY {fy - 1} appropriation."
                            )

            return note

        return None
