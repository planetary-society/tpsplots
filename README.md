# TPS Plots

A data visualization framework for The Planetary Society that creates consistent, branded charts for web and presentations.

## Motivation

TPS Plots was developed to address several key challenges and goals:

- **Replace outdated visualization technology**: Remove deprecated ChartJS 2.x implementation from planetary.org with a more modern, maintainable solution
- **Improve website performance**: Reduce load times and overhead by using pre-generated static charts instead of client-side JavaScript libraries
- **Strengthen brand identity**: Ensure all data visualizations consistently follow TPS branding guidelines
- **Simplify data maintenance**: Make inflation adjustments and data updates easier and more consistent
- **Enable custom visualizations**: Provide a platform for creating one-off, unique charts that still maintain TPS brand styling
- **Enhance shareability**: Enable easy download and sharing of charts by users, journalists, academics, and staff

## Overview

TPS Plots is a Python package designed to generate high-quality, branded data visualizations for The Planetary Society. The project follows an MVC (Model-View-Controller) architecture to separate data handling, visualization styling, and chart generation logic:

- **Models** (`data_sources`): Handle loading, cleaning, and processing data
- **Views** (`views`): Define chart styling and visualization types
- **Controllers** (`controllers`): Coordinate data and views to generate specific chart types

Charts are generated in multiple formats (SVG, PNG, PPTX) and optimized for both desktop (16x9) and mobile (1x1) display.

## Key Features

- **Static chart generation**: Pre-rendered charts reduce page load times and client-side processing
- **Consistent branding** with TPS style guidelines across all visualizations
- **Responsive design**: Automatic generation of both mobile and desktop versions of each chart
- **Economic analysis tools**: Built-in inflation adjustment using NNSI (NASA New-Start Index) and GDP deflators
- **Multi-format export**: Generate SVG (web), PNG (social media), and PPTX (presentations) formats
- **Automated publishing**: S3 syncing to publish charts to the planetary.org website
- **Extensible chart types**: Support for various visualization formats (line charts, waffle charts, etc.)
- **Share-friendly**: Easy download options for users, journalists, and researchers

## Usage

### Generating Charts

To generate a specific chart, import the appropriate controller and call its methods:

```python
from tpsplots.controllers.nasa_budget_chart import NASABudgetChart

chart = NASABudgetChart()
chart.nasa_budget_by_year_inflation_adjusted()
```

To generate all available NASA budget charts:

```python
chart = NASABudgetChart()
chart.generate_charts()
```

Charts will be saved to the `charts/` directory by default in multiple formats:
- `.svg` for web use (scalable, smaller file size)
- `.png` for social media sharing and general use
- `.pptx` for presentations (desktop version only)
- `.csv` for easy sharing of source data

### Syncing Charts to S3

Charts are synced to the Planetary Society website using the provided S3 sync script and appropriate access keys:

```bash
python scripts/s3_sync.py
```

This will upload charts to the `assets/charts/` directory in the specified S3 bucket, where they can be referenced from the Planetary website. This allows website developers to easily embed the charts using simple image tags, eliminating the need for complex JavaScript libraries and improving page load times.

Options:
- `--local-dir`: Local directory to sync (default: `charts`)
- `--bucket`: S3 bucket name (default: `planetary`)
- `--prefix`: S3 prefix (default: `assets/charts/`)
- `--delete`: Delete files in the bucket that don't exist locally
- `--dry-run`: Preview changes without uploading

By default, a GitHub Action refreshes and syncs charts every few months. 

## Adding New Charts

### 1. Create a Data Source

If your chart requires a new data source, create a class in `tpsplots/data_sources/` that inherits from an appropriate base class.

Example:
```python
# tpsplots/data_sources/my_new_data_source.py
from .nasa_budget_data_source import NASABudget

class MyNewDataSource(NASABudget):
    CSV_URL = "https://docs.google.com/spreadsheets/d/..."
    COLUMNS = ["Year", "Value1", "Value2"]
    MONETARY_COLUMNS = ["Value1", "Value2"]
    
    def __init__(self, *, cache_dir=None):
        super().__init__(self.CSV_URL, cache_dir=cache_dir)
```

### 2. Add a Chart Method to an Existing Controller (or Create a New One)

```python
# tpsplots/controllers/nasa_budget_chart.py
def my_new_chart(self):
    """Generate my new chart."""
    # Switch to the new data source if needed
    self.data_source = MyNewDataSource()
    df = self.data_source.data()
    
    # Prepare metadata
    metadata = {
        "title": "My New Chart",
        "source": "Source information",
    }
    
    # Get the appropriate view
    line_view = self.get_view('Line')
    
    # Generate the chart
    line_view.line_plot(
        metadata=metadata,
        stem="my_new_chart",
        x=df["Year"],
        y=[df["Value1"], df["Value2"]],
        color=["#037CC2", "#FF5D47"],
        label=["Value 1", "Value 2"],
        scale="millions"
    )
```

### 3. Create a New View Type (if needed)

If you need a new chart type not covered by existing views, create a new class in `tpsplots/views/`:

```python
# tpsplots/views/my_new_chart_view.py
from .chart_view import ChartView

class MyNewChartView(ChartView):
    """Specialized view for my new chart type."""
    
    def my_chart(self, metadata, stem, **kwargs):
        """Generate my chart type for both desktop and mobile."""
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _create_chart(self, metadata, style, **kwargs):
        """Implementation of chart creation."""
        # Chart creation logic here
        # ...
        return fig
```

Don't forget to update `tpsplots/views/__init__.py` to export your new view.

### 4. Use the New Chart

Update the controller's `generate_charts` method to include your new chart:

```python
def generate_charts(self):
    """Generate all NASA budget charts."""
    self.nasa_budget_by_year_inflation_adjusted()
    self.nasa_directorate_budget_waffle_chart()
    # Add your new chart
    self.my_new_chart()
```

Or generate it directly:

```python
from tpsplots.controllers.nasa_budget_chart import NASABudgetChart

chart = NASABudgetChart()
chart.my_new_chart()
```

## Project Structure

```
tpsplots/
├── __init__.py              # Package initialization
├── controllers/             # Chart generation logic
├── data_sources/            # Data loading and processing
├── views/                   # Chart visualization (subclasses for every major chart type)
└── style/                   # TPS "House Style" definitions for matplotlib
```

## Integrating with CraftCMS

Here's how to integrate charts into the website:

### CMS Setup

1. **Add Chart URL Reference**: Once charts are synced to S3, use the base URL format in the CraftCMS "Chart" content type:
   ```
   https://planetary.s3.amazonaws.com/assets/charts/nasa-budget-by-year
   ```
   Add this to the "SVG Charts" input field in the CMS.

2. **File Naming Convention**: The CMS expects the following files to exist for each chart:
   - `_desktop.svg` - Desktop vector version
   - `_mobile.svg` - Mobile vector version
   - `_desktop.png` - Desktop raster version
   - `_mobile.png` - Mobile raster version
   - `.pptx` - PowerPoint version
   - `.csv` - Source data

The CMS will load the appropriate chart file and provide links for download of PPTX, CSV, and PNG.

3. **Automatic Updates**: A GitHub Action runs every few months to refresh all charts with the latest inflation adjustments:
   - This ensures economic data stays current without manual intervention
   - The action can also be triggered manually when needed
   - No further CMS action is required after initial setup

4. **Data Source Updates**: For charts to remain accurate, ensure that:
   - Source Google Sheets are maintained with current data
   - Any local CSV data sources are updated regularly
   - API keys for economic data (if used) remain valid

The CMS will automatically use the appropriate mobile or desktop version based on the user's device, and will always display the most recent version of the chart after each automatic update.

## Author

Casey Dreier
