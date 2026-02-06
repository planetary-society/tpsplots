"""YAML templates for chart generation (v2.0 spec)."""

from tpsplots.models.chart_config import CHART_TYPES

# Templates for each chart type with all parameters commented out
TEMPLATES = {
    "line": """# Line Chart Template (v2.0)
# Generate with: tpsplots --new line

data:
  source: data/your_data.csv         # local CSV, URL, or controller.method
  # source: https://...              # URL CSV
  # source: nasa_budget_chart.method # controller method
  # source: /path/to/controller.py:method
  # source: controller:nasa_budget_chart.method
  # source: csv:data/your_data.csv
  # source: url:https://...

chart:
  type: line
  output: my_line_chart              # Output filename stem
  title: "Your Chart Title"
  # subtitle: "Optional subtitle with {{variable}} templates"
  # source: "Data source attribution"

  # === Data References ===
  x: "{{x_column}}"                  # X-axis data (required)
  y: "{{y_column}}"                  # Y-axis data (required)

  # === Multi-Series (use lists for multiple lines) ===
  # y: ["{{series1}}", "{{series2}}"]
  # color: [NeptuneBlue, RocketFlame]
  # linestyle: [solid, dashed]
  # label: ["Series 1", "Series 2"]

  # === Colors ===
  # color: NeptuneBlue               # Single color or list for multi-series
  # Colors: NeptuneBlue, RocketFlame, PlasmaPurple, MediumNeptune,
  #         LightNeptune, MediumPlasma, LightPlasma, CraterShadow,
  #         LunarSoil, CometDust, SlushyBrine

  # === Line Styling ===
  # linestyle: solid                 # solid, dashed, dotted, dashdot
  # linewidth: 3                     # Line width in points
  # marker: o                        # o, s, ^, D, v, <, >, p, h, +, x

  # === Axis Configuration ===
  # xlabel: "X-Axis Label"
  # ylabel: "Y-Axis Label"
  # xlim: [0, 100]                   # X-axis limits [min, max]
  # ylim: [0, 100]                   # Y-axis limits [min, max]
  # scale: billions                  # billions, millions, thousands, percentage
  # axis_scale: y                    # x, y, or both

  # === Typography ===
  # xlabel_size: 14
  # ylabel_size: 14
  # tick_size: 12
  # legend_size: 12
  # label_size: 14

  # === Display Options ===
  # grid: true
  # legend: false

  # === Direct Line Labels (instead of legend) ===
  # direct_line_labels: true
  # direct_line_labels:
  #   fontsize: 10
  #   position: right                # right, left, auto
  #   bbox: true                     # Background box

  # === Data Export ===
  # export_data: "{{export_df}}"     # Reference to export data
    """,
    "scatter": """# Scatter Chart Template (v2.0)
# Generate with: tpsplots --new scatter

data:
  source: data/your_data.csv

chart:
  type: scatter
  output: my_scatter_chart
  title: "Your Scatter Chart Title"
  # subtitle: "Optional subtitle with {{variable}} templates"
  # source: "Data source attribution"

  # === Data References ===
  x: "{{x_column}}"                  # X-axis data (required)
  y: "{{y_column}}"                  # Y-axis data (required)

  # === Multi-Series ===
  # y: ["{{series1}}", "{{series2}}"]
  # label: ["Series 1", "Series 2"]
  # color: [NeptuneBlue, RocketFlame]

  # === Scatter Styling ===
  # marker: o                        # o, s, ^, D, v, <, >, p, h, +, x
  # markersize: 6
  # alpha: 0.9

  # Optional: connect points (disabled by default)
  # linestyle: solid                 # solid, dashed, dotted, dashdot
  # linewidth: 2

  # === Axis Configuration ===
  # xlabel: "X-Axis Label"
  # ylabel: "Y-Axis Label"
  # xlim: [0, 100]
  # ylim: [0, 100]
  # scale: billions                  # billions, millions, thousands, percentage
  # axis_scale: y                    # x, y, or both

  # === Display Options ===
  # grid: true
  # legend: true

  # === Data Export ===
  # export_data: "{{export_df}}"
""",
    "bar": """# Bar Chart Template (v2.0)
# Generate with: tpsplots --new bar

data:
  source: data/your_data.csv

chart:
  type: bar
  output: my_bar_chart
  title: "Your Bar Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  categories: "{{category_column}}"  # Category labels
  values: "{{value_column}}"         # Bar values

  # === Orientation ===
  # orientation: vertical            # vertical or horizontal

  # === Sorting ===
  # sort_by: value                   # value, category, or none
  # sort_ascending: false

  # === Bar Styling ===
  # height: 0.8                      # Bar height (horizontal) or width (vertical)
  # colors:                          # Per-bar colors
  #   - NeptuneBlue
  #   - RocketFlame

  # === Value Labels ===
  # show_values: true
  # value_format: ".1f"              # Python format spec
  # value_suffix: " units"
  # value_fontsize: 10

  # === Axis Configuration ===
  # xlabel: "X-Axis Label"
  # ylabel: "Y-Axis Label"
  # xlim: [0, 100]
  # ylim: [0, 100]
  # scale: billions

  # === Typography ===
  # xlabel_size: 14
  # ylabel_size: 14
  # tick_size: 12

  # === Display Options ===
  # grid: true

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "donut": """# Donut Chart Template (v2.0)
# Generate with: tpsplots --new donut

data:
  source: data/your_data.csv

chart:
  type: donut
  output: my_donut_chart
  title: "Your Donut Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  labels: "{{category_column}}"      # Slice labels
  values: "{{value_column}}"         # Slice values

  # === Donut Styling ===
  # hole_size: 0.4                   # Inner hole size (0-1)
  # show_percentages: true           # Show percentage labels
  # center_text: "Total"             # Text in center hole

  # === Colors ===
  # colors:
  #   - NeptuneBlue
  #   - RocketFlame
  #   - PlasmaPurple

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "lollipop": """# Lollipop Chart Template (v2.0)
# Generate with: tpsplots --new lollipop

data:
  source: data/your_data.csv

chart:
  type: lollipop
  output: my_lollipop_chart
  title: "Your Lollipop Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  categories: "{{category_column}}"  # Category labels
  start_values: "{{start_column}}"   # Range start values
  end_values: "{{end_column}}"       # Range end values

  # === Axis Position ===
  # y_axis_position: left            # left or right
  # hide_y_spine: false

  # === Styling ===
  # marker_size: 5
  # line_width: 5
  # colors:
  #   - NeptuneBlue
  #   - RocketFlame
  # linestyle:
  #   - solid
  #   - dashed

  # === Labels ===
  # start_value_labels: false
  # end_value_labels: false
  # range_labels: true
  # range_suffix: " yrs"
  # category_wrap_length: 30

  # === Axis Configuration ===
  # xlim: [1960, 2030]
  # scale: billions

  # === Display Options ===
  # grid: true
  # grid_axis: x                     # x, y, or both

  # === Typography ===
  # tick_size: 12

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "stacked_bar": """# Stacked Bar Chart Template (v2.0)
# Generate with: tpsplots --new stacked_bar

data:
  source: data/your_data.csv

chart:
  type: stacked_bar
  output: my_stacked_bar_chart
  title: "Your Stacked Bar Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  categories: "{{category_column}}"  # Category labels (x-axis)

  # === Stack Values (required) ===
  values:
    "Series 1": "{{series1_column}}"
    "Series 2": "{{series2_column}}"
  # labels: ["Series 1", "Series 2"]
  # colors: [NeptuneBlue, RocketFlame]

  # === Orientation ===
  # orientation: vertical            # vertical or horizontal

  # === Axis Configuration ===
  # xlabel: "Categories"
  # ylabel: "Values"
  # scale: billions

  # === Display Options ===
  # grid: true
  # legend: true

  # === Typography ===
  # tick_size: 12
  # legend_size: 10

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "waffle": """# Waffle Chart Template (v2.0)
# Generate with: tpsplots --new waffle

data:
  source: data/your_data.csv

chart:
  type: waffle
  output: my_waffle_chart
  title: "Your Waffle Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  values:
    "Category 1": "{{count_column}}"
    "Category 2": "{{other_count_column}}"

  # === Grid Configuration ===
  # rows: 10
  # columns: 10

  # === Colors ===
  # colors:
  #   - NeptuneBlue
  #   - RocketFlame

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "us_map_pie": """# US Map Pie Chart Template (v2.0)
# Generate with: tpsplots --new us_map_pie

data:
  source: your_controller.get_state_data

chart:
  type: us_map_pie
  output: my_us_map_pie_chart
  title: "Your US Map Pie Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  state_data: "{{state_df}}"         # DataFrame with state data
  pie_values: "{{category_values}}"  # Pie chart category values

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "line_subplots": """# Line Subplots Template (v2.0)
# Generate with: tpsplots --new line_subplots

data:
  source: data/your_data.csv

chart:
  type: line_subplots
  output: my_line_subplots_chart
  title: "Your Multi-Panel Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Subplots Configuration (required) ===
  subplot_data:
    - x: "{{x_column}}"
      y: "{{y1_column}}"
      title: "Panel 1"
      color: NeptuneBlue
    - x: "{{x_column}}"
      y: "{{y2_column}}"
      title: "Panel 2"
      color: RocketFlame

  # === Shared Axis Options ===
  # shared_x: true
  # shared_y: false

  # === Data Export ===
  # export_data: "{{data}}"
""",
}


def get_template(chart_type: str) -> str:
    """Get the YAML template for a chart type.

    Args:
        chart_type: The chart type (e.g., 'line', 'bar')

    Returns:
        The template string

    Raises:
        ValueError: If the chart type is not recognized
    """
    if chart_type not in TEMPLATES:
        available = list(TEMPLATES.keys())
        raise ValueError(f"Unknown chart type: {chart_type}. Available: {available}")
    return TEMPLATES[chart_type]


def get_available_templates() -> list[str]:
    """Get list of available template types."""
    return list(TEMPLATES.keys())
