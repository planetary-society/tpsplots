# Controllers

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Controllers provide data to charts via the `data.source` field in YAML:

```yaml
data:
  source: nasa_budget_chart.nasa_budget_by_year
```

## CSV and Google Sheets

CSV files and Google Sheets URLs are loaded automatically when used
as the `data.source` value — no controller prefix is needed.

```yaml
# Local CSV file
data:
  source: data/budget.csv

# Google Sheets (public, exported as CSV)
data:
  source: https://docs.google.com/spreadsheets/d/.../export?format=csv
```

Both produce a result dict containing:

- One key per column in the dataset, mapped to its Series
  (e.g. `{{Fiscal Year}}`, `{{Budget}}`)
- `data` — the full DataFrame
- `export_df` — DataFrame for CSV export
- `metadata` — standard metadata (see below)

Use `data.params` to customize loading. See [Data Configuration](data.md) for the full params reference.

## Standard Metadata

Every controller returns a `metadata` dict with context values
available for `{{...}}` template references in `title`, `subtitle`,
and `source` fields. The standard keys are:

| Key | Type | Description |
|-----|------|-------------|
| `max_fiscal_year` | int | Latest fiscal year in the dataset |
| `min_fiscal_year` | int | Earliest fiscal year in the dataset |
| `inflation_adjusted_year` | int | Target year for inflation adjustment (when applicable) |
| `source` | str | Source attribution string |
| `column_sums` | dict | Column totals (when ColumnSumProcessor runs) |

CSV and Google Sheets controllers auto-produce per-column keys for numeric columns, and custom controllers can opt in explicitly by passing `value_columns` to `_build_metadata`:

| Key pattern | Description |
|-------------|-------------|
| `max_{name}_fiscal_year` | Latest FY with non-null data for that column |
| `min_{name}_fiscal_year` | Earliest FY with non-null data for that column |
| `max_{name}` | Maximum value for that column |
| `min_{name}` | Minimum value for that column |

Individual controllers may add extra keys (e.g. `total_budget`, `total_projects`). See each method's Returns section below.

## Controllers

- [`apollo_controller`](controllers/apollo_controller.md) — Controller for Project Apollo program spending charts.
- [`china_comparisons_controller`](controllers/china_comparisons_controller.md) — Controller for China vs U.S. space science mission comparison charts.
- [`comparison_charts_controller`](controllers/comparison_charts_controller.md) — Controller for comparison charts (waffle, etc.).
- [`mission_spending_controller`](controllers/mission_spending_controller.md) — Prepares mission outlay and obligations data for charting.
- [`nasa_budget_chart`](controllers/nasa_budget_chart.md) — Controller for top-line NASA budget charts.
- [`nasa_fy2024_controller`](controllers/nasa_fy2024_controller.md)
- [`nasa_fy2025_controller`](controllers/nasa_fy2025_controller.md) — Controller for FY 2025 NASA budget charts and analysis.
- [`nasa_fy2026_controller`](controllers/nasa_fy2026_controller.md) — Controller for FY 2026 NASA budget charts and analysis.
- [`nasa_fy2027_controller`](controllers/nasa_fy2027_controller.md) — Controller for FY 2027 NASA budget charts and analysis.
- [`planetary_mission_budget`](controllers/planetary_mission_budget.md) — Controller with dynamically generated methods for each planetary budget tab.
