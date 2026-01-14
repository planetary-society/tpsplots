"""Waffle chart visualization specialized view."""

import math

import matplotlib.pyplot as plt
from pywaffle import Waffle

from .chart_view import ChartView


class WaffleChartView(ChartView):
    """Specialized view for waffle charts with a focus on exposing the Waffle API."""

    def waffle_chart(self, metadata, stem, **kwargs):
        """
        Generate waffle charts for both desktop and mobile.

        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments passed directly to pywaffle's Waffle class.
            Required parameters:
            - values: dict - Dictionary with labels as keys and values as values

            Common parameters:
            - rows: int - Number of rows in the waffle chart
            - columns: int - Number of columns in the waffle chart
            - colors: list - List of colors to use for different categories
            - labels: list - Custom labels for the legend
            - legend: dict - Legend parameters

        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a waffle chart with appropriate styling.

        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Parameters passed directly to pywaffle's Waffle class

        Returns:
            matplotlib.figure.Figure: The created figure

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate required parameters
        values = kwargs.get("values")
        if not values:
            raise ValueError("The 'values' parameter is required for waffle_chart")

        if "legend" in kwargs and isinstance(kwargs["legend"], dict):
            kwargs["legend"]["fontsize"] = int(style.get("legend_size", 15))

        # Handle rows and columns calculation if not provided
        if "rows" not in kwargs and "columns" not in kwargs:
            total_blocks = sum(values.values())
            rows, columns = self._calculate_waffle_dimensions(total_blocks, style["figsize"])
            kwargs["rows"] = rows
            kwargs["columns"] = columns

        # Set default figsize from style
        if "figsize" not in kwargs:
            kwargs["figsize"] = style["figsize"]

        # Special handling for mobile legend
        if style == self.MOBILE and "legend" in kwargs and isinstance(kwargs["legend"], dict):
            legend = kwargs["legend"]
            # Reduce number of columns for mobile
            if "ncol" in legend:
                legend["ncol"] = math.ceil(legend["ncol"] / 2) + 1

            # Adjust position if using bbox_to_anchor
            if "bbox_to_anchor" in legend:
                bbox = legend["bbox_to_anchor"]
                legend["bbox_to_anchor"] = (bbox[0], bbox[1] + 0.02)
                legend["borderpad"] = 0
            kwargs["legend"] = legend

        # Create the waffle chart
        fig = plt.figure(FigureClass=Waffle, **kwargs)

        self._adjust_layout_for_header_footer(fig, metadata, style)
        return fig

    def _calculate_waffle_dimensions(self, total_blocks, figsize):
        """
        Calculate optimal rows and columns for a waffle chart.

        Args:
            total_blocks: Total number of blocks in the waffle chart
            figsize: (width, height) dimensions of the figure

        Returns:
            tuple: (rows, columns) optimized for the aspect ratio
        """
        # Extract width and height from figsize
        width, height = figsize

        # Reserve some portion of the image height for footer and legend
        # This effectively reduces the available height for the waffle chart
        available_height = height * 0.75

        # Calculate the effective aspect ratio of the available space
        effective_aspect_ratio = width / available_height

        # Calculate columns optimized for the effective aspect ratio
        columns = round(math.sqrt(total_blocks * effective_aspect_ratio))

        # Calculate rows to accommodate all blocks
        rows = math.ceil(total_blocks / columns)

        # Ensure we have enough rows and columns
        rows = max(rows, 1)
        columns = max(columns, 1)

        return rows, columns
