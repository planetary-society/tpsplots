"""Shared helpers for line-like series plotting across views."""

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.extensions import ExtensionArray

from .param_utils import broadcast_param


class LineSeriesMixin:
    """Utilities for normalizing and plotting per-series line data."""

    @staticmethod
    def _coerce_series_list(y_data: Any) -> list[Any] | None:
        """
        Coerce y-data into a list-of-series shape.

        - Scalars/arrays become a single series list
        - List/tuple of arrays stays multi-series
        - List/tuple of scalars is treated as one series
        """
        if y_data is None:
            return None

        if isinstance(y_data, (pd.Series, np.ndarray, ExtensionArray)):
            return [y_data]

        if isinstance(y_data, (list, tuple)):
            if not y_data:
                return []
            first = y_data[0]
            if isinstance(first, (pd.Series, np.ndarray, ExtensionArray, list, tuple)):
                return list(y_data)
            return [list(y_data)]

        return [y_data]

    @staticmethod
    def _normalize_series_param(value: Any, num_series: int, *, default: Any = None) -> list[Any]:
        """Normalize scalar/list params to a list sized to ``num_series``."""
        return broadcast_param(value, num_series, default=default)

    def _clip_to_xlim(self, x_data, y_data, y_right_data, xlim):
        """Drop data points that fall outside the configured ``xlim``.

        Out-of-range points otherwise render as partially clipped markers at
        the axes edges, and their values inflate the y autoscale even though
        they are never visible. Bounds that cannot be compared with the x data
        (e.g. dates against categorical labels) leave the data untouched.

        Lives on this mixin so the line, scatter, and line-subplots views all
        share it, while value-axis charts (bar, lollipop) that use ``xlim``
        for padding semantics stay excluded.
        """
        if x_data is None or not xlim:
            return x_data, y_data, y_right_data

        xlim = self._convert_xlim_to_datetime(xlim, x_data)
        if isinstance(xlim, dict):
            lower, upper = xlim.get("left"), xlim.get("right")
        elif isinstance(xlim, (list, tuple)) and len(xlim) == 2:
            lower, upper = xlim
        else:
            return x_data, y_data, y_right_data

        try:
            x_series = pd.Series(x_data)
            if pd.api.types.is_datetime64_any_dtype(x_series):
                lower = pd.Timestamp(lower) if lower is not None else None
                upper = pd.Timestamp(upper) if upper is not None else None
            keep = pd.Series(True, index=x_series.index)
            if lower is not None:
                keep &= x_series >= lower
            if upper is not None:
                keep &= x_series <= upper
        except (TypeError, ValueError):
            return x_data, y_data, y_right_data

        if keep.all():
            return x_data, y_data, y_right_data
        keep = keep.to_numpy()

        def clip_one(series):
            if len(series) != len(keep):
                return series
            if isinstance(series, pd.Series):
                return series[keep]
            return np.asarray(series)[keep]

        def clip_list(series_list):
            if series_list is None:
                return None
            return [clip_one(s) for s in series_list]

        return clip_one(x_series), clip_list(y_data), clip_list(y_right_data)

    @staticmethod
    def _filter_valid_xy(x_values: Any, y_values: Any) -> tuple[np.ndarray, np.ndarray]:
        """
        Filter x/y pairs to finite, non-null points while preserving order.

        Returns:
            Tuple of (x_filtered, y_filtered) as numpy arrays.
        """
        x_array = np.array(x_values)
        y_array = np.array(y_values)

        valid_mask = ~pd.isna(y_array)
        valid_mask &= ~pd.isna(x_array)

        return x_array[valid_mask], y_array[valid_mask]
