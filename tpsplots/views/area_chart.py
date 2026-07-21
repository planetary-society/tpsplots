"""Ordinary and stacked area chart rendering."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tpsplots.colors import resolve_color
from tpsplots.models.charts.area import AreaChartConfig, raise_for_geometry_overrides

from .anim_tags import Roles, tag_artist
from .chart_view import ChartView
from .mixins import (
    ContinuousAxisMixin,
    GridAxisMixin,
    LineSeriesMixin,
    legend_config_kwargs,
)
from .style import tokens


@dataclass(frozen=True, slots=True)
class _AreaRenderSpec:
    """Validated, normalized state required to render one area chart."""

    x: Any
    y: tuple[np.ndarray, ...]
    stacked: bool
    colors: tuple[Any, ...]
    labels: tuple[str | None, ...]
    alphas: tuple[float, ...]
    edgecolors: tuple[Any, ...]
    linewidths: tuple[float, ...]
    linestyles: tuple[str, ...]
    collection_kwargs: Mapping[str, Any]


class AreaChartView(ContinuousAxisMixin, LineSeriesMixin, GridAxisMixin, ChartView):
    """Render independent or cumulatively stacked areas from a zero baseline."""

    CONFIG_CLASS: ClassVar[type] = AreaChartConfig

    def area_plot(self, metadata, stem, **kwargs):
        """Generate desktop, mobile, and social area chart outputs."""
        return self.generate_chart(metadata, stem, **kwargs)

    @staticmethod
    def _replace_sparse_defaults(values, defaults):
        return [
            default if value is None else value
            for value, default in zip(values, defaults, strict=True)
        ]

    def _normalize_labels(self, labels, count: int) -> list[str | None]:
        defaults = [f"Series {index + 1}" for index in range(count)]
        if isinstance(labels, str):
            return [labels, *([None] * (count - 1))]
        normalized = self._normalize_series_param(labels, count)
        return self._replace_sparse_defaults(normalized, defaults)

    @staticmethod
    def _is_categorical_x(x_values) -> bool:
        return bool(x_values) and all(isinstance(value, str) for value in x_values)

    def _normalize_area_data(self, x_data, y_data, *, stacked: bool):
        if x_data is None or y_data is None:
            raise ValueError("Area charts require non-empty x and y data")

        try:
            x_values = list(x_data)
        except TypeError as exc:
            raise ValueError("Area charts require non-empty x data") from exc
        if not x_values or not y_data:
            raise ValueError("Area charts require non-empty x and y data")
        if any(pd.isna(value) for value in x_values):
            raise ValueError("Area chart x data cannot contain missing values")

        numeric_y: list[np.ndarray] = []
        for index, series in enumerate(y_data):
            try:
                series_length = len(series)
            except TypeError as exc:
                raise ValueError("Every area y series must have the same length as x") from exc
            if series_length != len(x_values):
                raise ValueError("Every area y series must have the same length as x")
            values = np.asarray(
                self._coerce_numeric_values(series, f"y series {index + 1}"), dtype=float
            )
            if np.isinf(values).any():
                raise ValueError("Area y data cannot contain infinite values")
            if not np.isfinite(values).any():
                raise ValueError("Every area y series must contain at least one finite value")
            if stacked and np.any(values[np.isfinite(values)] < 0):
                raise ValueError("Stacked area charts do not support negative values")
            numeric_y.append(values)

        categorical = self._is_categorical_x(x_values)
        if not categorical:
            try:
                numeric_x = np.asarray(x_values, dtype=float)
            except (TypeError, ValueError):
                numeric_x = None
            if numeric_x is not None and np.isinf(numeric_x).any():
                raise ValueError("Area x data cannot contain infinite values")
            x_series = pd.Series(x_values)
            increasing = x_series.is_monotonic_increasing
            if not increasing and not x_series.is_monotonic_decreasing:
                raise ValueError("Continuous area x data must be monotonic")
            if not increasing:
                x_values.reverse()
                numeric_y = [values[::-1].copy() for values in numeric_y]

        if stacked:
            matrix = np.vstack(numeric_y)
            common_gap = np.isnan(matrix).any(axis=0)
            matrix[:, common_gap] = np.nan
            numeric_y = [row for row in matrix]

        return x_values, numeric_y

    def _build_render_spec(
        self,
        *,
        data,
        x,
        y,
        stacked,
        color,
        labels,
        alpha,
        edgecolor,
        linewidth,
        linestyle,
        xlim,
        collection_kwargs,
    ) -> _AreaRenderSpec:
        x_data, y_data = self._resolve_xy_series_data(data, x, y)
        x_data, y_data = self._normalize_area_data(x_data, y_data, stacked=stacked)
        x_data, y_data, _ = self._clip_to_xlim(x_data, y_data, None, xlim)
        if len(x_data) == 0:
            raise ValueError("Area chart x limits leave no non-empty data to render")
        if any(not np.isfinite(values).any() for values in y_data):
            raise ValueError("Every area y series must contain a finite value within x limits")

        count = len(y_data)
        alpha_default = tokens.STACKED_AREA_ALPHA if stacked else tokens.AREA_ALPHA
        colors = self._normalize_series_param(color, count)
        default_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["#1f77b4"])
        colors = [
            default_cycle[index % len(default_cycle)] if value is None else value
            for index, value in enumerate(colors)
        ]
        normalized_labels = self._normalize_labels(labels, count)
        alphas = self._replace_sparse_defaults(
            self._normalize_series_param(alpha, count), [alpha_default] * count
        )
        edgecolors = self._replace_sparse_defaults(
            self._normalize_series_param(edgecolor, count), [tokens.AREA_EDGECOLOR] * count
        )
        linewidths = self._replace_sparse_defaults(
            self._normalize_series_param(linewidth, count), [tokens.AREA_LINEWIDTH] * count
        )
        linestyles = self._replace_sparse_defaults(
            self._normalize_series_param(linestyle, count), ["-"] * count
        )

        def apply_alias(base, *names):
            override = next(
                (collection_kwargs[name] for name in names if name in collection_kwargs), None
            )
            if override is None:
                return base
            normalized = self._normalize_series_param(override, count)
            return self._replace_sparse_defaults(normalized, base)

        colors = apply_alias(colors, "facecolors", "facecolor", "fc")
        edgecolors = apply_alias(edgecolors, "edgecolors", "ec")
        linewidths = apply_alias(linewidths, "linewidths", "lw")
        linestyles = apply_alias(linestyles, "linestyles", "ls")
        if "label" in collection_kwargs:
            normalized_labels = self._normalize_labels(collection_kwargs["label"], count)
        style_aliases = {
            "ec",
            "edgecolors",
            "facecolor",
            "facecolors",
            "fc",
            "label",
            "linestyles",
            "linewidths",
            "ls",
            "lw",
        }
        artist_kwargs = {
            key: value for key, value in collection_kwargs.items() if key not in style_aliases
        }

        frozen_y = []
        for values in y_data:
            frozen_values = np.array(values, copy=True)
            frozen_values.setflags(write=False)
            frozen_y.append(frozen_values)

        return _AreaRenderSpec(
            x=tuple(x_data),
            y=tuple(frozen_y),
            stacked=stacked,
            colors=tuple(colors),
            labels=tuple(normalized_labels),
            alphas=tuple(float(value) for value in alphas),
            edgecolors=tuple(edgecolors),
            linewidths=tuple(float(value) for value in linewidths),
            linestyles=tuple(str(value) for value in linestyles),
            collection_kwargs=MappingProxyType(artist_kwargs),
        )

    @staticmethod
    def _draw_ordinary_areas(ax, spec: _AreaRenderSpec):
        return [ax.fill_between(spec.x, 0, values, **spec.collection_kwargs) for values in spec.y]

    @staticmethod
    def _draw_stacked_areas(ax, spec: _AreaRenderSpec):
        return list(ax.stackplot(spec.x, *spec.y, baseline="zero", **spec.collection_kwargs))

    @staticmethod
    def _style_collections(ax, collections, spec: _AreaRenderSpec):
        for index, collection in enumerate(collections):
            collection.set_facecolor(resolve_color(spec.colors[index]))
            collection.set_alpha(spec.alphas[index])
            collection.set_edgecolor(resolve_color(spec.edgecolors[index]))
            collection.set_linewidth(spec.linewidths[index])
            collection.set_linestyle(spec.linestyles[index])
            collection.set_label(spec.labels[index])
            collection.sticky_edges.y.append(0)
            tag_artist(collection, Roles.SERIES, index)

    def _create_chart(self, metadata, style, **kwargs):
        """Validate first, then allocate and render the area figure."""
        data = kwargs.pop("data", None)
        x = kwargs.pop("x", None)
        y = kwargs.pop("y", None)
        stacked = kwargs.pop("stacked", False)
        color = kwargs.pop("color", None)
        labels = kwargs.pop("labels", None)
        alpha = kwargs.pop("alpha", None)
        edgecolor = kwargs.pop("edgecolor", None)
        linewidth = kwargs.pop("linewidth", None)
        linestyle = kwargs.pop("linestyle", None)

        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        xticks = kwargs.pop("xticks", None)
        xticklabels = kwargs.pop("xticklabels", None)
        max_xticks = kwargs.pop("max_xticks", style.get("max_ticks"))
        integer_xticks = kwargs.pop("integer_xticks", None)
        x_tick_format = kwargs.pop("x_tick_format", None)
        y_tick_format = kwargs.pop("y_tick_format", None)
        grid = kwargs.pop("grid", None)
        grid_axis = kwargs.pop("grid_axis", None)
        tick_rotation = kwargs.pop("tick_rotation", style["tick_rotation"])
        tick_size = kwargs.pop("tick_size", style["tick_size"])
        label_size = kwargs.pop("label_size", style["label_size"])
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        scale = kwargs.pop("scale", None)
        axis_scale = kwargs.pop("axis_scale", "y")
        fiscal_year_ticks = kwargs.pop("fiscal_year_ticks", True)
        legend = kwargs.pop("legend", True)
        # Popped up front so they never reach ``collection_kwargs``; the figure
        # itself is only allocated once validation has passed.
        figure_kwargs = {key: kwargs.pop(key) for key in ("figsize", "dpi") if key in kwargs}

        self._extract_metadata_from_kwargs(metadata, kwargs)
        raise_for_geometry_overrides(kwargs)

        spec = self._build_render_spec(
            data=data,
            x=x,
            y=y,
            stacked=stacked,
            color=color,
            labels=labels,
            alpha=alpha,
            edgecolor=edgecolor,
            linewidth=linewidth,
            linestyle=linestyle,
            xlim=xlim,
            collection_kwargs=dict(kwargs),
        )

        fig = None
        try:
            fig, ax = self._setup_figure(style, figure_kwargs)
            collections = (
                self._draw_stacked_areas(ax, spec)
                if spec.stacked
                else self._draw_ordinary_areas(ax, spec)
            )
            self._style_collections(ax, collections, spec)
            self._apply_continuous_axis(
                ax,
                style=style,
                x_data=spec.x,
                xlim=xlim,
                ylim=ylim,
                xticks=xticks,
                xticklabels=xticklabels,
                max_xticks=max_xticks,
                integer_xticks=integer_xticks,
                x_tick_format=x_tick_format,
                y_tick_format=y_tick_format,
                grid=grid,
                grid_axis=grid_axis,
                tick_rotation=tick_rotation,
                tick_size=tick_size,
                label_size=label_size,
                xlabel=xlabel,
                ylabel=ylabel,
                scale=scale,
                axis_scale=axis_scale,
                fiscal_year_ticks=fiscal_year_ticks,
            )
            if legend:
                handles, legend_labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(
                        handles,
                        legend_labels,
                        **legend_config_kwargs(legend, fontsize=style["legend_size"]),
                    )
            self._adjust_layout_for_header_footer(fig, metadata, style)
            return fig
        except Exception:
            if fig is not None:
                plt.close(fig)
            raise
