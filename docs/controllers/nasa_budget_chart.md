# nasa_budget_chart

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `NASABudgetChart`

Controller for top-line NASA budget charts.

| Method                                             | YAML Source                                                        | Description                                                                          |
| -------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `nasa_budget_by_year()`                            | `nasa_budget_chart.nasa_budget_by_year`                            | Return comprehensive NASA budget data for YAML-driven chart generation.              |
| `nasa_major_activites_donut_chart()`               | `nasa_budget_chart.nasa_major_activites_donut_chart`               | Generate donut chart breakdown of NASA directorate budgets for the last fiscal year. |
| `nasa_major_programs_by_year_inflation_adjusted()` | `nasa_budget_chart.nasa_major_programs_by_year_inflation_adjusted` | Line chart of NASA's directorate budgets from 2007 until the last fiscal year.       |
| `nasa_spending_share_by_year()`                    | `nasa_budget_chart.nasa_spending_share_by_year`                    | Return cleaned spending-share series for dual-axis budget charts.                    |
| `workforce()`                                      | `nasa_budget_chart.workforce`                                      | Return NASA workforce headcount data with year-over-year changes.                    |

## `nasa_budget_chart.nasa_budget_by_year`

Return comprehensive NASA budget data for YAML-driven chart generation.

This method provides historical data without projections. For charts that
need White House Budget Projections, use the FY-specific controller's
pbr_historical_context() method instead.

Returns:
dict with keys: - fiscal_year: Series of fiscal years as datetime - presidential_administration: Series of president names - pbr: Nominal Presidential Budget Request values - appropriation: Nominal Congressional Appropriation values - pbr_adjusted: Inflation-adjusted PBR (NNSI) - appropriation_adjusted: Inflation-adjusted appropriation (NNSI) - export_df: DataFrame for CSV export - max_fiscal_year: Maximum fiscal year (for source attribution) - metadata: dict with helpful context values: - max_fiscal_year, min_fiscal_year: Overall FY range - max_pbr_fiscal_year, min_pbr_fiscal_year: FY range for PBR data - max_appropriation_fiscal_year, min_appropriation_fiscal_year: FY range for appropriation data - inflation_adjusted_year: Target FY for inflation adjustment (e.g., 2024)

## `nasa_budget_chart.nasa_major_activites_donut_chart`

Generate donut chart breakdown of NASA directorate budgets for the last fiscal year.

Returns columnar data for flexible YAML-driven chart generation, following
the patterns established in nasa_fy_charts_controller.py.

Returns:
dict with keys: - Directorate: Series of directorate names (sorted by budget descending) - Budget: Series of budget values in dollars - fiscal_year: int - The fiscal year of the data - source: str - Source attribution text - total_budget: float - Total budget across displayed directorates - export_df: DataFrame for CSV export (includes STEM Education)

## `nasa_budget_chart.nasa_major_programs_by_year_inflation_adjusted`

Line chart of NASA's directorate budgets from 2007 until the last fiscal year.

Returns columnar data for flexible YAML-driven chart generation.

Returns:
dict with keys: - fiscal_year: Series of fiscal year dates - deep_space_exploration_systems: Series of adjusted budget values - science: Series of adjusted budget values - aeronautics: Series of adjusted budget values - space_technology: Series of adjusted budget values - stem_education: Series of adjusted budget values - space_operations: Series of adjusted budget values - overhead: Series of adjusted budget values (Facilities, IT, & Salaries) - export_df: DataFrame for CSV export - metadata: dict with max_fiscal_year, min_fiscal_year, source,
inflation_adjusted_year

## `nasa_budget_chart.nasa_spending_share_by_year`

Return cleaned spending-share series for dual-axis budget charts.

Produces inflation-adjusted appropriation values and spending-share
percentages cleaned by the data source layer.

## `nasa_budget_chart.workforce`

Return NASA workforce headcount data with year-over-year changes.

Returns:
dict with keys: - fiscal_year: Series of fiscal years as datetime - fte: Series of Full-time Equivalent counts - ftp: Series of Full-time Permanent counts - yoy_fte_change: Series of year-over-year FTE change (absolute) - yoy_pct_fte_change: Series of year-over-year FTE change (decimal fraction) - export_df: DataFrame for CSV export - metadata: dict with fiscal year ranges, per-column min/max/FY stats,
and peak/trough fiscal years (which FY had the highest/lowest value)
