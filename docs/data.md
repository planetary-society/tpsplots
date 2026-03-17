# Data Configuration

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Chart Types](index.md)

Fields under the `data:` key in YAML.

## Example

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/.../export?format=csv
  params:
    columns:
      - "Fiscal Year"
      - "Budget"
    cast:
      Fiscal Year: int
    auto_clean_currency: true
  calculate_inflation:
    columns:
      - "Budget"
    type: nnsi
```

## DataSourceConfig

Data source configuration using a single source string.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | str | **required** | Data source string |
| `params` | [DataSourceParams](#datasourceparams) | — | Parameters for URL/CSV sources |
| `calculate_inflation` | [InflationConfig](#inflationconfig) | — | Inflation adjustment configuration |

## DataSourceParams

Parameters for URL/CSV data sources.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `columns` | list[str] | — | Columns to keep from the data source |
| `cast` | dict[str, str] | — | Column type overrides (e.g., {'Date': 'datetime', 'ID': 'str'}) |
| `renames` | dict[str, str] | — | Column renames (e.g., {'Old Name': 'New Name'}) |
| `auto_clean_currency` | bool or [CurrencyCleaningConfig](#currencycleaningconfig) | — | Auto-detect and clean currency columns. Can be bool or config with multiplier. |
| `fiscal_year_column` | str or bool | — | Column to convert to datetime. None=auto-detect (Fiscal Year, FY, Year), str=column name, False=disable |
| `truncate_at` | bool or str | — | Truncate rows at the first first-column value that exactly matches the marker. None=use source default, True=force source default, False=disable, str=custom exact match marker. |

## InflationConfig

Configuration for inflation adjustment.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `columns` | list[str] | **required** | Columns to adjust for inflation |
| `type` | `"nnsi"`, `"gdp"` | `"nnsi"` | Inflation adjustment type (nnsi or gdp) |
| `fiscal_year_column` | str | `"Fiscal Year"` | Column containing fiscal year for each row |
| `target_year` | int | — | FY to adjust to (default: auto-calculate prior FY) |

## CurrencyCleaningConfig

Configuration for auto-cleaning currency columns.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable currency cleaning |
| `multiplier` | float | `1.0` | Scale factor to apply after cleaning (e.g., 1000000 to convert millions to dollars) |
