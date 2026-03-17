# comparison_charts_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `ComparisonCharts`

Controller for comparison charts (waffle, etc.).

| Method | YAML Source | Description |
|--------|------------|-------------|
| `nasa_spending_as_part_of_annual_us_expenditures()` | `comparison_charts_controller.nasa_spending_as_part_of_annual_us_expenditures` | Generate NASA's portion of U.S. spending for waffle chart. |

## `comparison_charts_controller.nasa_spending_as_part_of_annual_us_expenditures`

Generate NASA's portion of U.S. spending for waffle chart.

Returns data for YAML-driven chart generation, following patterns
from nasa_fy_charts_controller.py. View-related config (colors,
layout, legend) should be defined in YAML.

Returns:
    dict with keys:
        - values: dict mapping category names to block counts
        - labels: list of formatted labels with percentages
        - fiscal_year: int - The fiscal year of the data
        - source: str - Source attribution text
        - block_value: int - Dollar value per block
        - export_df: DataFrame for CSV export
