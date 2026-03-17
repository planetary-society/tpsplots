# china_comparisons_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `ChinaComparisonCharts`

Controller for China vs U.S. space science mission comparison charts.

| Method                                                 | YAML Source                                                                       | Description                                                                         |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `china_space_science_mission_count_bar_chart()`        | `china_comparisons_controller.china_space_science_mission_count_bar_chart`        | Return grouped bar chart data comparing China vs U.S. space science mission counts. |
| `china_space_science_mission_mass_growth_line_chart()` | `china_comparisons_controller.china_space_science_mission_mass_growth_line_chart` | Return line chart data comparing average launch mass growth for China vs U.S.       |

## `china_comparisons_controller.china_space_science_mission_count_bar_chart`

Return grouped bar chart data comparing China vs U.S. space science mission counts.

Counts missions per decade (2000s, 2010s, 2020s) for both nations,
splitting each decade into launched and planned categories. Stacked
values show planned missions in the 2020s decade.

Returns:
dict with keys: - data: DataFrame with combined mission listings - categories: list of decade labels - groups: list of GroupConfig dicts (China, U.S.) - export_df: DataFrame for CSV export - metadata: dict with standard keys

## `china_comparisons_controller.china_space_science_mission_mass_growth_line_chart`

Return line chart data comparing average launch mass growth for China vs U.S.

Calculates mean spacecraft launch mass per decade (2000s, 2010s,
2020s) for both nations, showing how China's missions are increasing
in mass and complexity.

Returns:
dict with keys: - data: DataFrame with combined mission listings - x: list of decade labels - y: list of [china_values, us_values] - labels: list of nation names - export_df: DataFrame for CSV export - metadata: dict with standard keys
