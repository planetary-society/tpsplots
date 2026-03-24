# nasa_fy2025_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `NASAFY2025Controller`

Controller for FY 2025 NASA budget charts and analysis.

| Method | YAML Source | Description |
|--------|------------|-------------|
| `congressional_vs_white_house_nasa_budgets()` | `nasa_fy2025_controller.congressional_vs_white_house_nasa_budgets` | Return request vs HAC-CJS vs SAC-CJS comparison for each account. |
| `directorates_comparison()` | `nasa_fy2025_controller.directorates_comparison` | Return directorate comparison data (grouped bar format by default). |
| `directorates_comparison_grouped()` | `nasa_fy2025_controller.directorates_comparison_grouped` | Return directorate data formatted for grouped bar charts. |
| `directorates_comparison_raw()` | `nasa_fy2025_controller.directorates_comparison_raw` | Return directorate data as raw table for flexible charting/export. |
| `directorates_context()` | `nasa_fy2025_controller.directorates_context` | Return historical budget data for each NASA directorate with WH projections. |
| `major_accounts_context()` | `nasa_fy2025_controller.major_accounts_context` | Return NASA major accounts data from 2006 to the controller's fiscal year. |
| `new_contract_awards_comparison_to_prior_years()` | `nasa_fy2025_controller.new_contract_awards_comparison_to_prior_years` | Return new NASA contract award data compared to prior fiscal years. |
| `new_grants_awards_comparison_to_prior_year()` | `nasa_fy2025_controller.new_grants_awards_comparison_to_prior_year` | Return new NASA grant award data compared to prior fiscal years. |
| `pbr_historical_context()` | `nasa_fy2025_controller.pbr_historical_context` | Return historical budget data with current FY PBR and runout projections. |
| `science_context()` | `nasa_fy2025_controller.science_context` | Return historical budget data for NASA Science Mission Directorate (SMD). |
| `science_division_context()` | `nasa_fy2025_controller.science_division_context` | Return historical budget data for each NASA science division. |
| `workforce_projections()` | `nasa_fy2025_controller.workforce_projections` | Return historical workforce data with optional FY projection. |

## `nasa_fy2025_controller.congressional_vs_white_house_nasa_budgets`

Return request vs HAC-CJS vs SAC-CJS comparison for each account.

Returns a ``categories`` dict keyed by display name (e.g. "NASA",
"Exploration"), where each value is a dict with ``values`` suitable
for a simple bar chart.  Access via bracket notation in YAML::

    categories: '{{categories["NASA"].values}}'

## `nasa_fy2025_controller.directorates_comparison`

Return directorate comparison data (grouped bar format by default).

This method delegates to directorates_comparison_grouped() for
backwards compatibility with existing YAML files.

For raw table data, use directorates_comparison_raw() instead.

## `nasa_fy2025_controller.directorates_comparison_grouped`

Return directorate data formatted for grouped bar charts.

Creates pre-configured group sets for different chart variants:
- groups_pbr: Prior year enacted vs current year request
- groups_enacted_vs_approp: Prior year enacted vs current appropriation
- groups_all: All three columns

Returns:
    dict with categories, groups, and group sets ready for YAML templates.

## `nasa_fy2025_controller.directorates_comparison_raw`

Return directorate data as raw table for flexible charting/export.

Use for: tables, heatmaps, custom chart types, data export.

Returns:
    dict with columns as keys, including Account and all FY columns.

## `nasa_fy2025_controller.directorates_context`

Return historical budget data for each NASA directorate with WH projections.

Uses ACCOUNTS from the subclass to determine which directorates to include.
Mirrors science_division_context() but for top-level directorates.

Each matched directorate includes:
- Multi-year enacted history from the Directorates Google Sheet
- Current FY PBR request and runout projections via BudgetProjectionProcessor

Returns:
    dict with columns for each matched directorate:
    - {display_name} - enacted historical values
    - {display_name}_adjusted_nnsi - inflation-adjusted enacted values
    - {display_name} White House Budget Projection - PBR + runouts

## `nasa_fy2025_controller.major_accounts_context`

Return NASA major accounts data from 2006 to the controller's fiscal year.

Filters budget detail rows to the accounts defined in the subclass's
ACCOUNTS class variable, applies aliases, and renames the first column
to "Account".

Returns:
    DataFrame with one row per major account and columns for each
    fiscal year's enacted/requested values.

## `nasa_fy2025_controller.new_contract_awards_comparison_to_prior_years`

Return new NASA contract award data compared to prior fiscal years.

Compares cumulative monthly contract award values for the current
fiscal year against the five prior years.

Returns:
    dict with chart-ready series and metadata for YAML variable references.

## `nasa_fy2025_controller.new_grants_awards_comparison_to_prior_year`

Return new NASA grant award data compared to prior fiscal years.

Compares cumulative monthly grant award values for the current
fiscal year against the five prior years.

Returns:
    dict with chart-ready series and metadata for YAML variable references.

## `nasa_fy2025_controller.pbr_historical_context`

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

## `nasa_fy2025_controller.science_context`

Return historical budget data for NASA Science Mission Directorate (SMD).

Uses a pipeline of processors:
1. BudgetProjectionProcessor: Merge historical data with PBR and runout
2. InflationAdjustmentProcessor: Apply NNSI adjustment to monetary columns
3. CalculatedColumnProcessor: Add YoY change calculations
4. DataFrameToYAMLProcessor: Convert to YAML-ready dict

Inflation adjustment uses FISCAL_YEAR - 1 as target year.

Returns:
    dict with chart-ready series and metadata for YAML variable references

## `nasa_fy2025_controller.science_division_context`

Return historical budget data for each NASA science division.

Includes FY PBR division requests and runout projections.
Returns raw columnar data for flexible chart use - YAML defines presentation.

Returns:
    dict with columns for each division:
    - {Division} - raw historical values
    - {Division}_adjusted_nnsi - inflation-adjusted values
    - {Division} White House Budget Projection - PBR + runouts

## `nasa_fy2025_controller.workforce_projections`

Return historical workforce data with optional FY projection.

If WORKFORCE_PROJECTION is defined in the subclass, creates a projection
series that overrides the actual FY value. Otherwise, returns workforce
data as-is through the current fiscal year.

Uses a pipeline of processors:
1. WorkforceProjectionProcessor: Filter data and optionally add projection

Returns:
    dict with chart-ready series and metadata for YAML variable references
