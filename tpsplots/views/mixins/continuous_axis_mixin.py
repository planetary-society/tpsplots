"""Shared continuous-series axis formatting for line and area charts."""

import logging

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tpsplots.views.style import tokens

logger = logging.getLogger(__name__)


def is_integer_x_data(x_data) -> bool:
    """Return whether every x value is integer-valued."""
    if x_data is None or len(x_data) == 0:
        return False
    if isinstance(x_data, pd.Series):
        if pd.api.types.is_integer_dtype(x_data):
            return True
        if pd.api.types.is_float_dtype(x_data):
            return bool((x_data % 1 == 0).all())
        return False
    if isinstance(x_data, np.ndarray):
        if np.issubdtype(x_data.dtype, np.integer):
            return True
        if np.issubdtype(x_data.dtype, np.floating):
            return bool((x_data % 1 == 0).all())
        return False
    return all(
        isinstance(value, (int, np.integer))
        or (isinstance(value, (float, np.floating)) and float(value).is_integer())
        for value in x_data
    )


class ContinuousAxisMixin:
    """Format the common x/y axes of continuous-series charts.

    All public options are explicit arguments. Concrete views pop their own
    kwargs before invoking this mixin, preserving the repository's drift guard.
    """

    def _apply_continuous_grid_and_labels(
        self,
        ax,
        *,
        style,
        xlabel,
        ylabel,
        label_size,
        tick_size,
        tick_rotation,
        grid,
        grid_axis,
    ):
        if isinstance(grid, dict):
            self._apply_axis_labels(
                ax,
                xlabel=xlabel,
                ylabel=ylabel,
                label_size=label_size,
                style_type=style["type"],
            )
            ax.grid(**grid)
            self._apply_tick_styling(ax, tick_size=tick_size, tick_rotation=tick_rotation)
            return

        effective_grid = style.get("grid") if grid is None else bool(grid)
        effective_grid_axis = grid_axis or style.get("grid_axis")
        self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=effective_grid,
            grid_axis=effective_grid_axis,
            grid_linestyle=tokens.GRID_LINESTYLE,
            grid_linewidth=tokens.GRID_LINEWIDTH,
        )

    def _apply_continuous_tick_formatting(
        self,
        ax,
        *,
        style,
        x_data,
        tick_rotation,
        tick_size,
        max_xticks,
        integer_xticks,
        fiscal_year_ticks,
    ):
        if fiscal_year_ticks and x_data is not None and self._contains_dates(x_data):
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
            return

        if x_data is not None and self._contains_dates(x_data):
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)
            return

        plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
        plt.setp(ax.get_yticklabels(), fontsize=tick_size)

        is_categorical = (
            x_data is not None and len(x_data) > 0 and isinstance(next(iter(x_data)), str)
        )
        if max_xticks and not is_categorical:
            use_integer = (
                integer_xticks if integer_xticks is not None else is_integer_x_data(x_data)
            )
            ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks, integer=use_integer))
        elif is_categorical and max_xticks and len(x_data) > max_xticks:
            step = len(x_data) // max_xticks + 1
            current_xlim = ax.get_xlim()
            positions = [
                position
                for position in range(0, len(x_data), step)
                if current_xlim[0] <= position <= current_xlim[1]
            ]
            if not positions:
                positions = list(range(0, len(x_data), step))
            ax.set_xticks(positions)
            try:
                ax.set_xticklabels([list(x_data)[position] for position in positions])
            except Exception:
                logger.warning("Could not set categorical xticklabels.")
            ax.set_xlim(current_xlim)

    def _apply_continuous_scale_and_ticks(
        self,
        ax,
        *,
        scale,
        axis_scale,
        x_tick_format,
        y_tick_format,
        xticks,
        xticklabels,
    ):
        scaled_x = False
        scaled_y = False
        if scale:
            if axis_scale == "both":
                self._apply_scale_formatter(ax, scale, "x", tick_format=x_tick_format)
                self._apply_scale_formatter(ax, scale, "y", tick_format=y_tick_format)
                scaled_x = True
                scaled_y = True
            elif axis_scale == "x":
                self._apply_scale_formatter(ax, scale, "x", tick_format=x_tick_format)
                scaled_x = True
            else:
                self._apply_scale_formatter(ax, scale, "y", tick_format=y_tick_format)
                scaled_y = True

        if xticks is not None:
            ax.set_xticks(xticks)
            if xticklabels is not None:
                ax.set_xticklabels(xticklabels)
            elif is_integer_x_data(xticks):
                ax.set_xticklabels([f"{int(value)}" for value in xticks])

        self._apply_tick_format_specs(
            ax,
            x_tick_format=x_tick_format if not scaled_x else None,
            y_tick_format=y_tick_format if not scaled_y else None,
            has_explicit_xticklabels=xticklabels is not None,
        )

    def _apply_continuous_axis(
        self,
        ax,
        *,
        style,
        x_data,
        xlim,
        ylim,
        xticks,
        xticklabels,
        max_xticks,
        integer_xticks,
        x_tick_format,
        y_tick_format,
        grid,
        grid_axis,
        tick_rotation,
        tick_size,
        label_size,
        xlabel,
        ylabel,
        scale,
        axis_scale,
        fiscal_year_ticks,
    ):
        """Apply common axis behavior from explicit normalized options."""
        self._apply_continuous_grid_and_labels(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=grid,
            grid_axis=grid_axis,
        )
        if xlim:
            xlim = self._convert_xlim_to_datetime(xlim, x_data)
        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)
        self._apply_continuous_tick_formatting(
            ax,
            style=style,
            x_data=x_data,
            tick_rotation=tick_rotation,
            tick_size=tick_size,
            max_xticks=max_xticks,
            integer_xticks=integer_xticks,
            fiscal_year_ticks=fiscal_year_ticks,
        )
        self._apply_continuous_scale_and_ticks(
            ax,
            scale=scale,
            axis_scale=axis_scale,
            x_tick_format=x_tick_format,
            y_tick_format=y_tick_format,
            xticks=xticks,
            xticklabels=xticklabels,
        )
