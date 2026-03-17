# mission_spending_controller

> Auto-generated from controller docstrings. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)

**Class:** `MissionSpendingController`

Prepares mission outlay and obligations data for charting.

| Method | YAML Source | Description |
|--------|------------|-------------|
| `process_mission_spending_data()` | `mission_spending_controller.process_mission_spending_data` | Process and generate spending charts for all configured NASA missions. |

## `mission_spending_controller.process_mission_spending_data`

Process and generate spending charts for all configured NASA missions.

Iterates through a predefined list of missions, loading outlay and
obligation CSV files for each, and generating line charts comparing
current vs prior fiscal year cumulative spending.

Note: This is a batch generator, not a YAML data source method.
It calls the view layer directly to produce chart files.

Args:
    outdir: Output directory for generated chart files.
