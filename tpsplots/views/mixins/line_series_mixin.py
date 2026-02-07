"""Shared helpers for line-like series plotting across views."""

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.extensions import ExtensionArray


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
        if num_series <= 0:
            return []

        if value is None:
            return [default] * num_series

        if isinstance(value, (list, tuple)):
            if len(value) >= num_series:
                return list(value[:num_series])
            if len(value) == 0:
                return [default] * num_series
            return list(value) + [value[-1]] * (num_series - len(value))

        return [value] * num_series

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
        if hasattr(x_array, "dtype") and np.issubdtype(x_array.dtype, np.datetime64):
            valid_mask &= ~pd.isna(x_array)
        else:
            valid_mask &= ~pd.isna(x_array)

        return x_array[valid_mask], y_array[valid_mask]
