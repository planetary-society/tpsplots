"""Processor for transforming columnar data into grouped bar chart format.

This processor takes a DataFrame with value columns and transforms it into a
structure suitable for grouped bar charts. It handles only data structure
transformation - presentation concerns (colors, scaling) belong in the view.

Example usage:
    config = GroupedBarTransformConfig(
        category_column="Account",
        value_columns=["FY 2025 Enacted", "FY 2026 Request", "Appropriated"],
        group_labels=["Prior Year", "PBR", "Appropriated"],
    )
    df = GroupedBarTransformProcessor(config).process(df)
    # df.attrs now contains 'categories', 'groups', 'groups_all', etc.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class GroupedBarTransformConfig:
    """Configuration for GroupedBarTransformProcessor.

    Attributes:
        category_column: Column to use for categories (e.g., "Account").
        value_columns: Columns to become groups (e.g., ["FY 2025 Enacted", "FY 2026 Request"]).
        group_labels: Optional custom labels for each group (defaults to column names).
        sort_by: Optional column name to sort categories by (default: None, preserves order).
        sort_descending: If True, sort in descending order (default: True).
        group_sets: Dict mapping set name → list of column indices to include in that set.
            Default creates 'groups_all' with all columns.
    """

    category_column: str = "Account"
    value_columns: list[str] = field(default_factory=list)
    group_labels: list[str] | None = None
    sort_by: str | None = None
    sort_descending: bool = True
    group_sets: dict[str, list[int]] | None = None


class GroupedBarTransformProcessor:
    """Transforms columnar data into grouped bar chart format.

    This processor stores grouped bar configuration in DataFrame.attrs for
    downstream consumption by views or YAML templates.

    The output includes:
    - categories: list of category values
    - groups: full group configuration for all value columns
    - groups_all: same as groups (for explicit naming)
    - Additional group sets based on configuration (e.g., groups_pbr, groups_enacted)

    Returns a DataFrame with attrs populated for use with DataFrameToYAMLProcessor:
        df = GroupedBarTransformProcessor(config).process(df)
        result = DataFrameToYAMLProcessor().process(df)
        # result['categories'], result['groups'], etc. are available

    Example:
        config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=["FY 2025 Enacted", "FY 2026 Request"],
            group_labels=["Prior Year", "Request"],
            group_colors=["Neptune Blue", "Rocket Flame"],
        )
        df = GroupedBarTransformProcessor(config).process(budget_df)
    """

    def __init__(self, config: GroupedBarTransformConfig):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying columns and styling for grouped bars.
        """
        self.config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform DataFrame into grouped bar format.

        Args:
            df: DataFrame with category and value columns.

        Returns:
            DataFrame with grouped bar configuration stored in attrs.

        Raises:
            KeyError: If required columns don't exist in the DataFrame.
        """
        self._validate_columns(df)

        df = df.copy()

        # Sort if configured
        if self.config.sort_by and self.config.sort_by in df.columns:
            df = df.sort_values(self.config.sort_by, ascending=not self.config.sort_descending)

        # Extract categories
        categories = df[self.config.category_column].tolist()

        # Build groups configuration
        groups = self._build_groups(df)

        # Store in attrs for downstream consumption
        df.attrs["categories"] = categories
        df.attrs["groups"] = groups
        df.attrs["groups_all"] = groups

        # Build additional group sets
        if self.config.group_sets:
            for set_name, indices in self.config.group_sets.items():
                df.attrs[f"groups_{set_name}"] = [groups[i] for i in indices if i < len(groups)]

        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate that required columns exist.

        Args:
            df: DataFrame to validate.

        Raises:
            KeyError: If required columns are missing.
        """
        if self.config.category_column not in df.columns:
            raise KeyError(
                f"Category column '{self.config.category_column}' not found. "
                f"Available columns: {list(df.columns)}"
            )

        for col in self.config.value_columns:
            if col not in df.columns:
                raise KeyError(
                    f"Value column '{col}' not found. Available columns: {list(df.columns)}"
                )

    def _build_groups(self, df: pd.DataFrame) -> list[dict]:
        """Build group configurations for the grouped bar chart.

        Args:
            df: DataFrame with value columns.

        Returns:
            List of group dicts with label and values only.
            Colors are a presentation concern handled by the view.
        """
        groups = []

        for i, col in enumerate(self.config.value_columns):
            # Get values (raw, unscaled - let the view handle scaling)
            values = df[col].tolist()

            # Determine label
            label = col
            if self.config.group_labels and i < len(self.config.group_labels):
                label = self.config.group_labels[i]

            groups.append(
                {
                    "label": label,
                    "values": values,
                }
            )

        return groups
