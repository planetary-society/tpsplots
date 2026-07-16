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
  # color: [Neptune Blue, Rocket Flame]
  # linestyle: [solid, dashed]
  # labels: ["Series 1", "Series 2"]

  # === Colors ===
  # color: Neptune Blue               # Single color or list for multi-series
  # Colors: Neptune Blue, Rocket Flame, Plasma Purple, Medium Neptune,
  #         Light Neptune, Medium Plasma, Light Plasma, Crater Shadow,
  #         Lunar Soil, Comet Dust, Slushy Brine

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
  # tick_size: 12
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
  # labels: ["Series 1", "Series 2"]
  # color: [Neptune Blue, Rocket Flame]

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
  #   - Neptune Blue
  #   - Rocket Flame

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
  # tick_size: 12
  # label_size: 14

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
  #   - Neptune Blue
  #   - Rocket Flame
  #   - Plasma Purple

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
  #   - Neptune Blue
  #   - Rocket Flame
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
  # colors: [Neptune Blue, Rocket Flame]

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
  # label_size: 14

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "grouped_bar": """# Grouped Bar Chart Template (v2.0)
# Generate with: tpsplots --new grouped_bar

data:
  source: data/your_data.csv

chart:
  type: grouped_bar
  output: my_grouped_bar_chart
  title: "Your Grouped Bar Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  categories: "{{category_column}}"  # Category labels (x-axis groups)

  # === Groups (required) ===
  # Each group draws one bar per category; add more groups as needed.
  groups:
    - label: "Series 1"
      values: "{{series1_column}}"
      # color: Neptune Blue
    - label: "Series 2"
      values: "{{series2_column}}"
      # color: Rocket Flame

  # === Colors / Labels ===
  # colors: [Neptune Blue, Rocket Flame]   # Override group colors
  # labels: ["Series 1", "Series 2"]     # Override group labels (legend)

  # === Bar Styling ===
  # width: 0.8                       # Total width of each category's bar group
  # alpha: 1.0
  # edgecolor: none
  # linewidth: 0

  # === Value Labels ===
  # show_values: true
  # value_format: ".1f"              # Python format spec
  # value_prefix: "$"
  # value_suffix: " units"
  # value_fontsize: 10

  # === Axis Configuration ===
  # xlabel: "X-Axis Label"
  # ylabel: "Y-Axis Label"
  # xlim: [0, 100]
  # ylim: [0, 100]
  # scale: billions

  # === Typography ===
  # tick_size: 12
  # label_size: 14
  # tick_rotation: 0

  # === Display Options ===
  # grid: true
  # grid_axis: y                     # x, y, or both
  # legend: true

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
  #   - Neptune Blue
  #   - Rocket Flame

  # === Data Export ===
  # export_data: "{{data}}"
""",
    "treemap": """# Treemap Chart Template (v2.0)
# Generate with: tpsplots --new treemap

data:
  source: data/your_data.csv

chart:
  type: treemap
  output: my_treemap_chart
  title: "Your Treemap Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Data References (required) ===
  labels: "{{category_column}}"
  values: "{{value_column}}"

  # === Tile Styling ===
  # colors: ["Neptune Blue", "Plasma Purple", "Rocket Flame"]
  # edgecolor: "Polar White"
  # linewidth: 2
  # alpha: 1

  # === Labels ===
  # show_labels: true
  # show_values: false
  # show_percentages: true
  # value_format: monetary
  # label_min_area_pct: 1
""",
    "us_map_pie": """# US Map Pie Chart Template (v2.0)
# Generate with: tpsplots --new us_map_pie
#
# Provide EITHER pie_data (Pathway 1, below) OR the CSV columns (Pathway 2) - not both.

data:
  source: controller:your_controller.get_state_data
  # source: data/your_data.csv       # for the column-oriented pathway below

chart:
  type: us_map_pie
  output: my_us_map_pie_chart
  title: "Your US Map Pie Chart Title"
  # subtitle: "Optional subtitle"
  # source: "Data source"

  # === Pathway 1: Controller-built pie_data (required) ===
  # Dict mapping location names to {values, labels, colors} pie dicts,
  # typically emitted by a controller method.
  pie_data: "{{pie_data}}"

  # === Pathway 2: CSV columns (use instead of pie_data) ===
  # Build pies from a DataFrame; all four fields are required together.
  # data: "{{data}}"                       # DataFrame template ref
  # location_column: State                 # column matching state names/abbrevs
  # value_columns: [Segment1, Segment2]    # one column per pie segment
  # labels: ["Segment 1", "Segment 2"]     # legend label per segment
  # colors: [Neptune Blue, Rocket Flame]   # color per segment

  # === Pie Sizing ===
  # pie_size_column: total           # key in pie_data for proportional sizing
  # base_pie_size: 800
  # min_pie_size: 400
  # max_pie_size: 1500

  # === Map Options ===
  # show_state_boundaries: true

  # === Display Options ===
  # show_pie_labels: true
  # show_percentages: true
  # legend_location: "lower left"
  # pie_edge_color: white
  # pie_edge_width: 0.5

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
      color: Neptune Blue
    - x: "{{x_column}}"
      y: "{{y2_column}}"
      title: "Panel 2"
      color: Rocket Flame

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
