# nasa_budget_chart

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `NASABudgetChart`

Controller for top-line NASA budget charts.

| Method | YAML Source | Description |
|--------|------------|-------------|
| `nasa_budget_by_year()` | `nasa_budget_chart.nasa_budget_by_year` | Return comprehensive NASA budget data for YAML-driven chart generation. |
| `nasa_major_activites_donut_chart()` | `nasa_budget_chart.nasa_major_activites_donut_chart` | Generate donut chart breakdown of NASA directorate budgets for the last fiscal year. |
| `nasa_major_programs_by_year_inflation_adjusted()` | `nasa_budget_chart.nasa_major_programs_by_year_inflation_adjusted` | Line chart of NASA's directorate budgets from 2007 until the last fiscal year. |
| `nasa_spending_share_by_year()` | `nasa_budget_chart.nasa_spending_share_by_year` | Return cleaned spending-share series for dual-axis budget charts. |
| `workforce()` | `nasa_budget_chart.workforce` | Return NASA workforce headcount data with year-over-year changes. |

## `nasa_budget_chart.nasa_budget_by_year`

Return comprehensive NASA budget data for YAML-driven chart generation.

This method provides historical data without projections. For charts that
need White House Budget Projections, use the FY-specific controller's
pbr_historical_context() method instead.

Returns:
    dict with all DataFrame columns as keys (pass-through), plus:
        - data: full DataFrame
        - export_df: DataFrame for CSV export
        - metadata: dict with FY ranges, per-column stats, inflation year

## `nasa_budget_chart.nasa_major_activites_donut_chart`

Generate donut chart breakdown of NASA directorate budgets for the last fiscal year.

Returns columnar data for flexible YAML-driven chart generation, following
the patterns established in nasa_fy_charts_controller.py.

Returns:
    dict with keys:
        - Directorate: Series of directorate names (sorted by budget descending)
        - Budget: Series of budget values in dollars
        - fiscal_year: int - The fiscal year of the data
        - source: str - Source attribution text
        - total_budget: float - Total budget across displayed directorates
        - export_df: DataFrame for CSV export (includes STEM Education)

## `nasa_budget_chart.nasa_major_programs_by_year_inflation_adjusted`

Line chart of NASA's directorate budgets from 2007 until the last fiscal year.

Returns columnar data for flexible YAML-driven chart generation.

Returns:
    dict with all DataFrame columns as keys (pass-through), plus:
        - data: full DataFrame
        - export_df: DataFrame for CSV export
        - metadata: dict with max_fiscal_year, min_fiscal_year, source,
          inflation_adjusted_year

## `nasa_budget_chart.nasa_spending_share_by_year`

Return cleaned spending-share series for dual-axis budget charts.

Produces inflation-adjusted appropriation values and spending-share
percentages cleaned by the data source layer.

## `nasa_budget_chart.workforce`

Return NASA workforce headcount data with year-over-year changes.

Returns:
    dict with all DataFrame columns as keys (pass-through), plus:
        - data: full DataFrame
        - export_df: DataFrame for CSV export
        - metadata: dict with fiscal year ranges, per-column min/max/FY stats,
          and peak/trough fiscal years (which FY had the highest/lowest value)
