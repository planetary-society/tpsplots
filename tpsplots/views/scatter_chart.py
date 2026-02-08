"""Scatter chart view built on top of the line chart rendering pipeline."""

from tpsplots.models.charts.scatter import ScatterChartConfig

from .line_chart import LineChartView


class ScatterChartView(LineChartView):
    """Specialized view for scatter charts with line-chart-compatible API."""

    CONFIG_CLASS = ScatterChartConfig

    def _create_chart(self, metadata, style, **kwargs):
        """Ensure scatter defaults apply to both preview and file-generation paths."""
        scatter_kwargs = kwargs.copy()
        scatter_kwargs.setdefault("marker", "o")
        if "linestyle" not in scatter_kwargs:
            scatter_kwargs["linestyle"] = "None"
        return super()._create_chart(metadata, style, **scatter_kwargs)

    def scatter_plot(self, metadata, stem, **kwargs):
        """
        Generate scatter charts for desktop and mobile versions.

        Reuses LineChartView internals for data handling, styling, labels, axis formatting,
        and exports. Scatter defaults are:
        - marker='o'
        - linestyle='None' (no connecting lines)
        """
        scatter_kwargs = kwargs.copy()
        scatter_kwargs.setdefault("marker", "o")
        if "linestyle" not in scatter_kwargs:
            scatter_kwargs["linestyle"] = "None"
        return self.generate_chart(metadata, stem, **scatter_kwargs)

    # Alias for backward compatibility with older naming conventions
    scatter_chart = scatter_plot
