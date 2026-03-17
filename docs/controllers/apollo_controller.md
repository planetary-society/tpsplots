# apollo_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `Apollo`

Controller for Project Apollo program spending charts.

| Method | YAML Source | Description |
|--------|------------|-------------|
| `facilities_construction_spending()` | `apollo_controller.facilities_construction_spending` | Return Apollo Facilities Construction spending with NNSI inflation adjustment. |
| `gemini_spending()` | `apollo_controller.gemini_spending` | Return Project Gemini spending with NNSI inflation adjustment. |
| `launch_vehicles_spending()` | `apollo_controller.launch_vehicles_spending` | Return Saturn-family launch vehicle development costs with NNSI adjustment. |
| `program_spending()` | `apollo_controller.program_spending` | Return Apollo program spending data with NNSI inflation adjustment. |
| `robotic_lunar_spending()` | `apollo_controller.robotic_lunar_spending` | Return Robotic Lunar Programs spending with NNSI inflation adjustment. |

## `apollo_controller.facilities_construction_spending`

Return Apollo Facilities Construction spending with NNSI inflation adjustment.

Returns:
    dict with keys:
        - data: Full DataFrame with all columns including adjusted
        - Year: Series of fiscal year datetimes
        - {col}: Nominal series for each monetary column
        - {col}_adjusted_nnsi: Adjusted series for each monetary column
        - {col}_sum: int sum of nominal values
        - {col}_adjusted_nnsi_sum: int sum of adjusted values
        - export_df: DataFrame for CSV export
        - metadata: dict with standard keys (min/max FY, inflation year, source)

## `apollo_controller.gemini_spending`

Return Project Gemini spending with NNSI inflation adjustment.

Returns:
    dict with keys:
        - data: Full DataFrame with all columns including adjusted
        - Fiscal Year: Series of fiscal year datetimes
        - {col}: Nominal series for each monetary column
        - {col}_adjusted_nnsi: Adjusted series for each monetary column
        - {col}_sum: int sum of nominal values
        - {col}_adjusted_nnsi_sum: int sum of adjusted values
        - export_df: DataFrame for CSV export
        - metadata: dict with standard keys (min/max FY, inflation year, source)

## `apollo_controller.launch_vehicles_spending`

Return Saturn-family launch vehicle development costs with NNSI adjustment.

Covers Saturn I, Saturn IB, and Saturn V development spending
extracted from the full Apollo program dataset.

Returns:
    dict with keys:
        - data: Full DataFrame with all columns including adjusted
        - Fiscal Year: Series of fiscal year datetimes
        - {col}: Nominal series for each monetary column
        - {col}_adjusted_nnsi: Adjusted series for each monetary column
        - {col}_sum: int sum of nominal values
        - {col}_adjusted_nnsi_sum: int sum of adjusted values
        - export_df: DataFrame for CSV export
        - metadata: dict with standard keys (min/max FY, inflation year, source)

## `apollo_controller.program_spending`

Return Apollo program spending data with NNSI inflation adjustment.

Provides the full dataset (FY 1960-1973) with nominal and
inflation-adjusted values for all 25 monetary columns, plus
column sums for both nominal and adjusted values.

Returns:
    dict with keys:
        - data: Full DataFrame with all columns including adjusted
        - Fiscal Year: Series of fiscal year datetimes
        - Lunar effort % of NASA: Percentage series
        - {col}: Nominal series for each monetary column (original name)
        - {col}_adjusted_nnsi: Adjusted series for each monetary column
        - {col}_sum: int sum of nominal values for each monetary column
        - {col}_adjusted_nnsi_sum: int sum of adjusted values
        - export_df: DataFrame for CSV export
        - metadata: dict with standard keys (min/max FY, inflation year, source)

## `apollo_controller.robotic_lunar_spending`

Return Robotic Lunar Programs spending with NNSI inflation adjustment.

Covers Ranger, Surveyor, and Lunar Orbiter programs.

Returns:
    dict with keys:
        - data: Full DataFrame with all columns including adjusted
        - Year: Series of fiscal year datetimes
        - {col}: Nominal series for each monetary column
        - {col}_adjusted_nnsi: Adjusted series for each monetary column
        - {col}_sum: int sum of nominal values
        - {col}_adjusted_nnsi_sum: int sum of adjusted values
        - export_df: DataFrame for CSV export
        - metadata: dict with standard keys (min/max FY, inflation year, source)
