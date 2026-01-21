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
        """
        # Scale label size for mobile
        if style_type == "mobile" and label_size:
            label_size = label_size * 0.6

        font_style = "italic" if italic else "normal"

        if xlabel:
            ax.set_xlabel(xlabel, fontsize=label_size, loc=loc, style=font_style)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=label_size, loc=loc, style=font_style)

    def _apply_tick_styling(
        self,
        ax,
        tick_size=None,
        tick_rotation=0,
        style_type="desktop",
    ):
        """
        Apply consistent tick label styling.

        Args:
            ax: Matplotlib axes object
            tick_size: Font size for tick labels
            tick_rotation: Rotation angle for x-axis tick labels
            style_type: 'desktop' or 'mobile' for responsive sizing
        """
        # Scale tick size for mobile
        if style_type == "mobile" and tick_size:
            tick_size = tick_size * 0.8

        ax.tick_params(axis="x", labelsize=tick_size, rotation=tick_rotation)
        ax.tick_params(axis="y", labelsize=tick_size)
