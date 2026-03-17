# nasa_fy2026_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `NASAFY2026Controller`

Controller for FY 2026 NASA budget charts and analysis.

| Method                                            | YAML Source                                                            | Description                                                                    |
| ------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `cancelled_missions_lollipop_chart()`             | `nasa_fy2026_controller.cancelled_missions_lollipop_chart`             | Return lollipop chart data for NASA missions proposed as cancelled in FY 2026. |
| `directorates_comparison()`                       | `nasa_fy2026_controller.directorates_comparison`                       | Return directorate comparison data (grouped bar format by default).            |
| `directorates_comparison_grouped()`               | `nasa_fy2026_controller.directorates_comparison_grouped`               | Return directorate data formatted for grouped bar charts.                      |
| `directorates_comparison_raw()`                   | `nasa_fy2026_controller.directorates_comparison_raw`                   | Return directorate data as raw table for flexible charting/export.             |
| `major_accounts_context()`                        | `nasa_fy2026_controller.major_accounts_context`                        | Return NASA major accounts data from 2006 to the controller's fiscal year.     |
| `nasa_center_workforce_map()`                     | `nasa_fy2026_controller.nasa_center_workforce_map`                     | Return workforce data for each NASA center as a US map pie chart.              |
| `new_contract_awards_comparison_to_prior_years()` | `nasa_fy2026_controller.new_contract_awards_comparison_to_prior_years` | Return new NASA contract award data compared to prior fiscal years.            |
| `new_grants_awards_comparison_to_prior_year()`    | `nasa_fy2026_controller.new_grants_awards_comparison_to_prior_year`    | Return new NASA grant award data compared to prior fiscal years.               |
| `pbr_historical_context()`                        | `nasa_fy2026_controller.pbr_historical_context`                        | Return historical budget data with current FY PBR and runout projections.      |
| `science_context()`                               | `nasa_fy2026_controller.science_context`                               | Return historical budget data for NASA Science Mission Directorate (SMD).      |
| `science_division_context()`                      | `nasa_fy2026_controller.science_division_context`                      | Return historical budget data for each NASA science division.                  |
| `workforce_projections()`                         | `nasa_fy2026_controller.workforce_projections`                         | Return historical workforce data with optional FY projection.                  |

## `nasa_fy2026_controller.cancelled_missions_lollipop_chart`

Return lollipop chart data for NASA missions proposed as cancelled in FY 2026.

Shows the launch date to cancellation date range for each active
NASA-led mission proposed for cancellation in the FY 2026 budget.

Returns:
dict with keys: - data: DataFrame with mission details - categories: Series of mission names - start_values: Series of launch years - end_values: Series of end years (2026) - xlim: tuple of x-axis limits - total_projects: int count of affected missions - total_value: str formatted total lifecycle cost - total_development_time: int total development years - export_df: DataFrame for CSV export - metadata: dict with standard keys

## `nasa_fy2026_controller.directorates_comparison`

Return directorate comparison data (grouped bar format by default).

This method delegates to directorates_comparison_grouped() for
backwards compatibility with existing YAML files.

For raw table data, use directorates_comparison_raw() instead.

## `nasa_fy2026_controller.directorates_comparison_grouped`

Return directorate data formatted for grouped bar charts.

Creates pre-configured group sets for different chart variants:

- groups_pbr: Prior year enacted vs current year request
- groups_enacted_vs_approp: Prior year enacted vs current appropriation
- groups_all: All three columns

Returns:
dict with categories, groups, and group sets ready for YAML templates.

## `nasa_fy2026_controller.directorates_comparison_raw`

Return directorate data as raw table for flexible charting/export.

Use for: tables, heatmaps, custom chart types, data export.

Returns:
dict with columns as keys, including Account and all FY columns.

## `nasa_fy2026_controller.major_accounts_context`

Return NASA major accounts data from 2006 to the controller's fiscal year.

Filters budget detail rows to the accounts defined in the subclass's
ACCOUNTS class variable, applies aliases, and renames the first column
to "Account".

Returns:
DataFrame with one row per major account and columns for each
fiscal year's enacted/requested values.

## `nasa_fy2026_controller.nasa_center_workforce_map`

Return workforce data for each NASA center as a US map pie chart.

Provides per-center pie data showing proposed FY 2026 staffing cuts
vs remaining workforce, suitable for the us_map_pie chart type.

Returns:
dict with keys: - data: DataFrame with per-center staffing totals - pie_data: dict mapping center abbreviations to pie configs
(values, labels, colors) - export_df: DataFrame for CSV export - metadata: dict with standard keys

## `nasa_fy2026_controller.new_contract_awards_comparison_to_prior_years`

Return new NASA contract award data compared to prior fiscal years.

Compares cumulative monthly contract award values for the current
fiscal year against the five prior years.

Returns:
dict with chart-ready series and metadata for YAML variable references.

## `nasa_fy2026_controller.new_grants_awards_comparison_to_prior_year`

Return new NASA grant award data compared to prior fiscal years.

Compares cumulative monthly grant award values for the current
fiscal year against the five prior years.

Returns:
dict with chart-ready series and metadata for YAML variable references.

## `nasa_fy2026_controller.pbr_historical_context`

Return historical budget data with current FY PBR and runout projections.

Uses a pipeline of processors:

1. BudgetProjectionProcessor: Merge historical data with PBR and runout
2. InflationAdjustmentProcessor: Apply NNSI adjustment to monetary columns
3. CalculatedColumnProcessor: Add YoY change calculations
4. DataFrameToYAMLProcessor: Convert to YAML-ready dict

Inflation adjustment uses FISCAL_YEAR - 1 as target year.

Returns:
dict with keys: fiscal_year, presidential_administration, pbr,
appropriation, white_house_projection, pbr_adjusted_nnsi,
appropriation_adjusted_nnsi, export_df, max_fiscal_year,
prior_appropriation_to_pbr_change_dollars,
prior_appropriation_to_pbr_change_percent, etc.

## `nasa_fy2026_controller.science_context`

Return historical budget data for NASA Science Mission Directorate (SMD).

Uses a pipeline of processors:

1. BudgetProjectionProcessor: Merge historical data with PBR and runout
2. InflationAdjustmentProcessor: Apply NNSI adjustment to monetary columns
3. CalculatedColumnProcessor: Add YoY change calculations
4. DataFrameToYAMLProcessor: Convert to YAML-ready dict

Inflation adjustment uses FISCAL_YEAR - 1 as target year.

Returns:
dict with chart-ready series and metadata for YAML variable references

## `nasa_fy2026_controller.science_division_context`

Return historical budget data for each NASA science division.

Includes FY PBR division requests and runout projections.
Returns raw columnar data for flexible chart use - YAML defines presentation.

Returns:
dict with columns for each division: - {Division} - raw historical values - {Division}\_adjusted_nnsi - inflation-adjusted values - {Division} White House Budget Projection - PBR + runouts

## `nasa_fy2026_controller.workforce_projections`

Return historical workforce data with optional FY projection.

If WORKFORCE_PROJECTION is defined in the subclass, creates a projection
series that overrides the actual FY value. Otherwise, returns workforce
data as-is through the current fiscal year.

Uses a pipeline of processors:

1. WorkforceProjectionProcessor: Filter data and optionally add projection

Returns:
dict with chart-ready series and metadata for YAML variable references
