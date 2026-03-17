"""Shared helpers for categorical bar-family charts."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import ClassVar

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class CategoricalBarMixin:
    """Helper methods shared by categorical bar-family charts."""

    _ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

    def _normalize_categories(self, categories):
        """Normalize bar categories without coercing date-like values to raw strings."""
        if categories is None:
            return categories

        if isinstance(categories, list):
            categories_list = categories
        elif hasattr(categories, "tolist"):
            categories_list = categories.tolist()
        else:
            categories_list = list(categories)

        normalized = []
        for category in categories_list:
            if isinstance(category, str):
                normalized.append(category.replace("\\n", "\n"))
            else:
                normalized.append(category)

        return np.asarray(normalized, dtype=object)

    @staticmethod
    def _build_category_positions(categories) -> np.ndarray:
        """Return canonical category positions for categorical bar charts."""
        return np.arange(len(categories))

    def _apply_category_axis(
        self,
        ax,
        categories,
        positions,
        *,
        orientation: str,
        category_label_format: str | None = None,
    ) -> None:
        """Apply category tick positions and formatted labels."""
        labels = self._format_category_labels(categories, category_label_format)

        if orientation == "vertical":
            ax.set_xticks(positions)
            ax.set_xticklabels(labels)
        else:
            ax.set_yticks(positions)
            ax.set_yticklabels(labels)

    def _apply_category_axis_alignment(self, ax, orientation: str, tick_rotation: float) -> None:
        """Apply category label alignment using the existing bar mixin helpers."""
        if orientation == "vertical":
            self._apply_vertical_category_alignment(ax, tick_rotation)
        else:
            self._apply_horizontal_category_alignment(ax)

    def _resolve_value_axis_visibility(
        self,
        *,
        orientation: str,
        show_xticks: bool | None = None,
        show_yticks: bool | None = None,
    ) -> bool:
        """Return whether the numeric value axis should be visibly rendered."""
        if orientation == "vertical":
            if show_xticks is not None:
                raise ValueError("show_xticks is only supported for horizontal bar charts")
            return True if show_yticks is None else show_yticks

        if show_yticks is not None:
            raise ValueError("show_yticks is only supported for vertical bar charts")
        return True if show_xticks is None else show_xticks

    def _resolve_category_tick_rotation(
        self,
        ax,
        *,
        orientation: str,
        tick_size: float,
        explicit_rotation: float | None = None,
    ) -> float:
        """Return the rotation to use for category labels on bar-family charts."""
        if explicit_rotation is not None:
            return explicit_rotation

        if orientation != "vertical":
            return 0

        categories = [label.get_text() for label in ax.get_xticklabels()]
        if not categories:
            return 0

        xlim_current = ax.get_xlim()
        chart_width = xlim_current[1] - xlim_current[0]
        if chart_width <= 0:
            return 0

        available_width_per_bar = chart_width / len(categories)
        return (
            90
            if self._should_rotate_labels(ax, categories, tick_size, available_width_per_bar)
            else 0
        )

    def _apply_shared_value_axis_styling(
        self,
        ax,
        *,
        style,
        orientation: str,
        xlabel=None,
        ylabel=None,
        label_size=None,
        tick_size=None,
        tick_rotation: float = 0,
        grid=True,
        grid_axis="y",
        xlim=None,
        ylim=None,
        scale=None,
        value_format=None,
        x_tick_format=None,
        y_tick_format=None,
        show_category_ticks: bool = False,
        show_value_axis: bool = True,
    ):
        """Apply the common post-plot axis styling shared by bar-like charts."""
        tick_size = self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=grid,
            grid_axis=grid_axis,
            xlim=None,
            ylim=None,
        )

        self._disable_minor_ticks(ax)

        scaled_x = False
        scaled_y = False

        if show_value_axis:
            if value_format == "percentage":
                self._apply_percentage_tick_formatter(ax, orientation)
                scaled_y = orientation == "vertical"
                scaled_x = orientation == "horizontal"
            elif scale:
                axis_to_scale = "y" if orientation == "vertical" else "x"
                tick_format = y_tick_format if axis_to_scale == "y" else x_tick_format
                self._apply_scale_formatter(ax, scale, axis=axis_to_scale, tick_format=tick_format)
                scaled_y = axis_to_scale == "y"
                scaled_x = axis_to_scale == "x"

        self._apply_tick_format_specs(
            ax,
            x_tick_format=x_tick_format if not scaled_x else None,
            y_tick_format=y_tick_format if not scaled_y else None,
            has_explicit_xticklabels=orientation == "vertical",
            has_explicit_yticklabels=orientation == "horizontal",
        )

        self._apply_integer_locator(ax, orientation=orientation)

        if not show_category_ticks:
            self._hide_category_ticks(ax, orientation=orientation)

        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)
        self._apply_category_axis_alignment(ax, orientation, tick_rotation)

        if show_value_axis:
            self._restore_default_value_axis_style(ax, orientation=orientation, tick_size=tick_size)
        else:
            self._hide_value_axis_style(ax, orientation=orientation)

        return tick_size

    _VALUE_AXIS_CONFIG: ClassVar[dict] = {
        "vertical": {
            "spine": "left",
            "axis": "y",
            "spine_visible_param": "axes.spines.left",
            "size_param": "ytick.major.size",
            "width_param": "ytick.major.width",
            "color_param": "ytick.color",
            "label_color_param": "ytick.labelcolor",
            "visible": {"left": True, "labelleft": True},
            "hidden": {"left": False, "labelleft": False},
        },
        "horizontal": {
            "spine": "bottom",
            "axis": "x",
            "spine_visible_param": "axes.spines.bottom",
            "size_param": "xtick.major.size",
            "width_param": "xtick.major.width",
            "color_param": "xtick.color",
            "label_color_param": "xtick.labelcolor",
            "visible": {"bottom": True, "labelbottom": True},
            "hidden": {"bottom": False, "labelbottom": False},
        },
    }

    def _restore_default_value_axis_style(self, ax, *, orientation: str, tick_size=None) -> None:
        """Restore visible rcParam-driven styling for the active value axis."""
        cfg = self._VALUE_AXIS_CONFIG[orientation]
        spine_color = plt.rcParams.get("axes.edgecolor", "black")
        spine_width = plt.rcParams.get("axes.linewidth", 0.8)
        tick_color = plt.rcParams.get(cfg["color_param"], spine_color)
        label_color = plt.rcParams.get(cfg["label_color_param"], "inherit")
        if label_color == "inherit":
            label_color = plt.rcParams.get("axes.labelcolor", tick_color)

        ax.spines[cfg["spine"]].set_visible(plt.rcParams.get(cfg["spine_visible_param"], True))
        ax.spines[cfg["spine"]].set_linewidth(spine_width)
        ax.spines[cfg["spine"]].set_edgecolor(spine_color)
        ax.tick_params(
            axis=cfg["axis"],
            labelsize=tick_size,
            length=plt.rcParams.get(cfg["size_param"], 3.5),
            width=plt.rcParams.get(cfg["width_param"], 0.8),
            color=tick_color,
            labelcolor=label_color,
            **cfg["visible"],
        )

    def _hide_value_axis_style(self, ax, *, orientation: str) -> None:
        """Hide the visible presentation of the active value axis while keeping tick locations."""
        cfg = self._VALUE_AXIS_CONFIG[orientation]
        ax.tick_params(axis=cfg["axis"], **cfg["hidden"])
        ax.spines[cfg["spine"]].set_visible(False)

    def _format_category_labels(
        self, categories, category_label_format: str | None = None
    ) -> list[str]:
        """Format category labels with readable defaults for date-like inputs."""
        return [
            self._format_single_category_label(category, category_label_format)
            for category in categories
        ]

    def _format_single_category_label(self, value, category_label_format: str | None = None) -> str:
        """Format one category label."""
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return ""

        timestamp = self._coerce_category_timestamp(value)
        if category_label_format:
            if category_label_format == "year":
                if timestamp is not None:
                    return str(timestamp.year)
                year_value = self._coerce_year_like_value(value)
                return str(year_value) if year_value is not None else str(value)

            if timestamp is not None:
                return timestamp.strftime(category_label_format)

            year_value = self._coerce_year_like_value(value)
            if year_value is not None and "%" in category_label_format:
                return datetime(year_value, 1, 1).strftime(category_label_format)

            return str(value)

        if timestamp is not None:
            if self._is_year_boundary(timestamp):
                return str(timestamp.year)
            return timestamp.strftime("%Y-%m-%d")

        year_value = self._coerce_year_like_value(value)
        if year_value is not None:
            return str(year_value)

        return str(value)

    def _coerce_category_timestamp(self, value):
        """Return a pandas Timestamp for supported date-like category inputs."""
        if isinstance(value, pd.Timestamp):
            return value
        if isinstance(value, np.datetime64):
            return pd.Timestamp(value)
        if isinstance(value, datetime):
            return pd.Timestamp(value)
        if isinstance(value, date):
            return pd.Timestamp(value)
        if isinstance(value, str) and self._ISO_DATE_RE.match(value):
            parsed = pd.to_datetime(value, errors="coerce")
            if pd.notna(parsed):
                return pd.Timestamp(parsed)
        return None

    @staticmethod
    def _coerce_year_like_value(value) -> int | None:
        """Return an integer year when the category looks like a year."""
        if isinstance(value, (int, np.integer)) and 1900 <= int(value) <= 2100:
            return int(value)
        if isinstance(value, str) and value.isdigit():
            year = int(value)
            if 1900 <= year <= 2100:
                return year
        return None

    @staticmethod
    def _is_year_boundary(timestamp: pd.Timestamp) -> bool:
        """True when a date-like category is semantically just a year marker."""
        return (
            timestamp.month == 1
            and timestamp.day == 1
            and timestamp.hour == 0
            and timestamp.minute == 0
            and timestamp.second == 0
            and timestamp.microsecond == 0
            and timestamp.nanosecond == 0
        )

    def _measure_text_width(self, ax, text, fontsize):
        """Measure the rendered width of text in data coordinates."""
        temp_text = ax.text(0, 0, text, fontsize=fontsize, transform=ax.transData)
        try:
            bbox = temp_text.get_window_extent(renderer=ax.figure.canvas.get_renderer())
            bbox_data = bbox.transformed(ax.transData.inverted())
            return bbox_data.width
        finally:
            temp_text.remove()

    def _should_rotate_labels(self, ax, categories, tick_size, available_width_per_bar):
        """Determine if category labels should rotate based on rendered width."""
        width_threshold = available_width_per_bar * 0.8

        for category in categories:
            text_width = self._measure_text_width(ax, str(category), tick_size)
            if text_width > width_threshold:
                return True

        return False
