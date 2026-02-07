"""Mixin providing shared grid and axis styling for chart views."""

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


class GridAxisMixin:
    """
    Mixin class providing shared grid and axis styling utilities.

    This mixin centralizes grid configuration, tick formatting, and axis styling
    that's duplicated across bar charts, stacked bar charts, lollipop charts,
    grouped bar charts, and line charts.

    Note: This mixin expects the including class to have access to:
    - self.COLORS: dict of base colors (from ChartView)
    """

    def _apply_grid(
        self,
        ax,
        *,
        grid=True,
        grid_axis="y",
        alpha=0.3,
        linestyle="--",
        linewidth=0.5,
    ):
        """
        Apply grid styling to axes.

        Args:
            ax: Matplotlib axes object
            grid: Whether to show grid (default: True)
            grid_axis: Which axis to show grid on ('x', 'y', 'both')
            alpha: Grid line transparency (default: 0.3)
            linestyle: Grid line style (default: '--')
            linewidth: Grid line width (default: 0.5)
        """
        if grid:
            ax.grid(axis=grid_axis, alpha=alpha, linestyle=linestyle, linewidth=linewidth)
        else:
            ax.grid(False)

    def _disable_minor_ticks(self, ax):
        """
        Disable minor ticks on both axes.

        This prevents unwanted tick marks from appearing between major ticks,
        which is common for categorical data and cleaner chart appearance.

        Args:
            ax: Matplotlib axes object
        """
        ax.xaxis.set_minor_locator(plt.NullLocator())
        ax.yaxis.set_minor_locator(plt.NullLocator())
        ax.tick_params(which="minor", left=False, right=False, top=False, bottom=False)

    def _apply_integer_locator(self, ax, orientation="vertical"):
        """
        Apply integer-only tick locator to the value axis.

        Prevents decimal values like 1.5 or 2.0 from appearing on count-based axes.

        Args:
            ax: Matplotlib axes object
            orientation: Chart orientation - 'vertical' applies to y-axis,
                        'horizontal' applies to x-axis
        """
        if orientation == "vertical":
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    def _hide_category_ticks(self, ax, orientation="vertical"):
        """
        Hide tick marks on the category axis while keeping labels.

        For bar charts, this hides the small tick lines but keeps category labels visible.

        Args:
            ax: Matplotlib axes object
            orientation: 'vertical' hides x-axis ticks, 'horizontal' hides y-axis ticks
        """
        if orientation == "vertical":
            ax.tick_params(axis="x", length=0, bottom=False, top=False)
        else:
            ax.tick_params(axis="y", length=0, left=False, right=False)

    def _apply_axis_limits(self, ax, xlim=None, ylim=None):
        """
        Apply axis limits handling both tuple and dict formats.

        Args:
            ax: Matplotlib axes object
            xlim: X-axis limits as tuple (min, max) or dict {'left': val, 'right': val}
            ylim: Y-axis limits as tuple (min, max) or dict {'bottom': val, 'top': val}
        """
        if xlim:
            if isinstance(xlim, dict):
                ax.set_xlim(**xlim)
            else:
                ax.set_xlim(xlim)

        if ylim:
            if isinstance(ylim, dict):
                ax.set_ylim(**ylim)
            else:
                ax.set_ylim(ylim)

    def _apply_axis_labels(
        self,
        ax,
        xlabel=None,
        ylabel=None,
        label_size=None,
        style_type="desktop",
        *,
        italic=True,
        loc="center",
        xlabel_pad=10,
        ylabel_pad=4,
    ):
        """
        Apply consistent axis label styling.

        Args:
            ax: Matplotlib axes object
            xlabel: X-axis label text
            ylabel: Y-axis label text
            label_size: Font size for labels (scaled for mobile if style_type is 'mobile')
            style_type: 'desktop' or 'mobile' for responsive sizing
            italic: Whether to use italic style (default: True)
            loc: Label location (default: 'center')
            xlabel_pad: Spacing in points between x-axis and label (default: 8)
            ylabel_pad: Spacing in points between y-axis and label (default: 4)
        """
        # Scale label size for mobile
        if style_type == "mobile" and label_size:
            label_size = label_size * 0.6

        font_style = "italic" if italic else "normal"

        if xlabel:
            ax.set_xlabel(
                xlabel, fontsize=label_size, loc=loc, style=font_style, labelpad=xlabel_pad
            )
        if ylabel:
            ax.set_ylabel(
                ylabel, fontsize=label_size, loc=loc, style=font_style, labelpad=ylabel_pad
            )

    def _scale_tick_size_for_mobile(self, tick_size: float | None, style_type: str) -> float | None:
        """
        Scale tick size for mobile display.

        This is a composable helper for charts that need to apply tick styling
        conditionally (e.g., bar charts with fiscal year detection).

        Args:
            tick_size: Base font size for tick labels
            style_type: 'desktop' or 'mobile'

        Returns:
            Scaled tick size (80% of original for mobile, unchanged for desktop)
        """
        if style_type == "mobile" and tick_size:
            return tick_size * 0.8
        return tick_size

    def _apply_tick_styling(
        self,
        ax,
        tick_size=None,
        tick_rotation=0,
        style_type="desktop",
    ):
        """
        Apply consistent tick label styling to both axes.

        For charts needing conditional axis handling (e.g., fiscal year detection),
        use _scale_tick_size_for_mobile() instead and apply tick_params manually.

        Args:
            ax: Matplotlib axes object
            tick_size: Font size for tick labels
            tick_rotation: Rotation angle for x-axis tick labels
            style_type: 'desktop' or 'mobile' for responsive sizing
        """
        tick_size = self._scale_tick_size_for_mobile(tick_size, style_type)

        ax.tick_params(axis="x", labelsize=tick_size, rotation=tick_rotation)
        ax.tick_params(axis="y", labelsize=tick_size)

    def _apply_common_axis_styling(
        self,
        ax,
        *,
        style,
        xlabel=None,
        ylabel=None,
        label_size=None,
        tick_size=None,
        tick_rotation=0,
        grid=True,
        grid_axis="y",
        grid_alpha=0.3,
        grid_linestyle="--",
        grid_linewidth=0.5,
        xlim=None,
        ylim=None,
        italic=True,
        loc="center",
        xlabel_pad=10,
        ylabel_pad=4,
        scale_ticks_for_mobile=True,
    ):
        """
        Compose common label/grid/tick/limit styling across chart views.

        Args:
            ax: Matplotlib axes object
            style: Style dictionary (DESKTOP or MOBILE)
            xlabel: X-axis label text
            ylabel: Y-axis label text
            label_size: Label font size (defaults from style)
            tick_size: Tick font size (defaults from style)
            tick_rotation: X-axis tick rotation
            grid: Whether to show grid
            grid_axis: Grid axis ('x', 'y', or 'both')
            grid_alpha: Grid line alpha
            grid_linestyle: Grid line style
            grid_linewidth: Grid line width
            xlim: X-axis limits
            ylim: Y-axis limits
            italic: Axis label font style flag
            loc: Axis label location
            xlabel_pad: X-axis label pad
            ylabel_pad: Y-axis label pad
            scale_ticks_for_mobile: Apply mobile tick downscaling when True

        Returns:
            float | None: Effective tick size after optional mobile scaling
        """
        if label_size is None:
            label_size = style.get("label_size")
        if tick_size is None:
            tick_size = style.get("tick_size")

        style_type = style.get("type", "desktop")

        self._apply_axis_labels(
            ax,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            style_type=style_type,
            italic=italic,
            loc=loc,
            xlabel_pad=xlabel_pad,
            ylabel_pad=ylabel_pad,
        )
        self._apply_grid(
            ax,
            grid=grid,
            grid_axis=grid_axis,
            alpha=grid_alpha,
            linestyle=grid_linestyle,
            linewidth=grid_linewidth,
        )

        tick_style_type = style_type if scale_ticks_for_mobile else "desktop"
        self._apply_tick_styling(
            ax,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            style_type=tick_style_type,
        )
        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)

        if scale_ticks_for_mobile:
            return self._scale_tick_size_for_mobile(tick_size, style_type)
        return tick_size
