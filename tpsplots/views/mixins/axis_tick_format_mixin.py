"""Mixin providing reusable axis tick-format helpers for numeric axes."""

from typing import Any

import numpy as np
from matplotlib.ticker import FuncFormatter


class AxisTickFormatMixin:
    """Shared helpers for f-string-style axis tick label formatting."""

    @staticmethod
    def _pop_axis_tick_format_kwargs(kwargs: dict[str, Any]) -> tuple[str | None, str | None]:
        """
        Pop x/y tick format options from kwargs, including legacy aliases.

        Supported aliases:
        - x_tick_format or x_axis_format
        - y_tick_format or y_axis_format
        """
        x_tick_format = kwargs.pop("x_tick_format", kwargs.pop("x_axis_format", None))
        y_tick_format = kwargs.pop("y_tick_format", kwargs.pop("y_axis_format", None))
        return x_tick_format, y_tick_format

    @staticmethod
    def _build_fstring_tick_formatter(format_spec: str) -> FuncFormatter:
        """Build a FuncFormatter that applies a Python format spec to numeric ticks."""

        def formatter(value, _pos):
            try:
                if not np.isfinite(value):
                    return ""
                return format(value, format_spec)
            except Exception:
                return str(value)

        return FuncFormatter(formatter)

    def _apply_tick_format_specs(
        self,
        ax,
        *,
        x_tick_format: str | None = None,
        y_tick_format: str | None = None,
        has_explicit_xticklabels: bool = False,
        has_explicit_yticklabels: bool = False,
    ) -> None:
        """Apply optional f-string style format specs to axis tick labels."""
        if x_tick_format and not has_explicit_xticklabels:
            ax.xaxis.set_major_formatter(self._build_fstring_tick_formatter(x_tick_format))
        if y_tick_format and not has_explicit_yticklabels:
            ax.yaxis.set_major_formatter(self._build_fstring_tick_formatter(y_tick_format))
