"""Small, dependency-free helpers shared across chart-view code.

These are plain module-level functions (not mixins) so any view or mixin can
import them without inheritance coupling.
"""

from typing import Any


def broadcast_param(value: Any, num_series: int, default: Any = None) -> list[Any]:
    """Normalize a scalar-or-list per-series param to exactly ``num_series`` items.

    Rules:
        - ``num_series <= 0`` -> ``[]``
        - ``None`` -> ``[default] * num_series``
        - list/tuple:
            - length ``>= num_series`` -> sliced to ``num_series``
            - empty -> ``[default] * num_series``
            - shorter -> padded with its last element
        - any other scalar -> ``[value] * num_series``
    """
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


def legend_config_kwargs(legend: Any, **defaults: Any) -> dict | None:
    """Turn a ``bool | str | dict`` legend config into ``ax.legend`` kwargs.

    Rules:
        - ``None`` / ``False`` -> ``None`` (caller should skip drawing)
        - ``dict`` -> ``{**defaults, **legend}``
        - ``str`` -> ``{**defaults, "loc": legend}``
        - anything else truthy (e.g. ``True``) -> a copy of ``defaults``
    """
    if legend is None or legend is False:
        return None
    if isinstance(legend, dict):
        return {**defaults, **legend}
    if isinstance(legend, str):
        return {**defaults, "loc": legend}
    return dict(defaults)
