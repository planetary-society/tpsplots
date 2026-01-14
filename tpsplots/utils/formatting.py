"""Value formatting utilities for tpsplots.

Provides standalone formatting functions that can be used both
within chart views and externally for data processing.
"""

import math


def format_monetary(value: float) -> str:
    """
    Format monetary values with appropriate suffixes (B, M, K).

    Args:
        value: The numeric value to format

    Returns:
        Formatted string with currency symbol and magnitude suffix

    Examples:
        >>> format_monetary(1_500_000_000)
        '$1.5B'
        >>> format_monetary(25_000_000)
        '$25M'
        >>> format_monetary(750_000)
        '$750K'
        >>> format_monetary(500)
        '$500'
        >>> format_monetary(-1_000_000)
        '-$1M'
    """
    if math.isnan(value):
        return ""

    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{sign}${abs_value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}${abs_value / 1_000_000:.0f}M"
    elif abs_value >= 1_000:
        return f"{sign}${abs_value / 1_000:.0f}K"
    else:
        return f"{sign}${abs_value:.0f}"


def format_value(value: float, format_type: str) -> str:
    """
    Format values according to the specified format type.

    Args:
        value: The numeric value to format
        format_type: Format preset ('monetary', 'percentage', 'integer', 'float')
                    or a Python format spec (e.g., '.1f', '.2f', ',.0f')

    Returns:
        Formatted string representation of the value

    Raises:
        ValueError: If format_type is not recognized

    Examples:
        >>> format_value(1234567, "monetary")
        '$1M'
        >>> format_value(0.456, "percentage")
        '0.5%'
        >>> format_value(1234, "integer")
        '1,234'
        >>> format_value(3.14159, ".2f")
        '3.14'
    """
    if math.isnan(value):
        return ""

    if format_type == "monetary":
        return format_monetary(value)
    elif format_type == "percentage":
        return f"{value:.1f}%"
    elif format_type == "integer":
        return f"{int(value):,}"
    elif format_type == "float":
        return f"{value:.1f}"
    else:
        # Try as custom Python format specification
        try:
            return f"{value:{format_type}}"
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"Invalid value_format: '{format_type}'. "
                f"Must be one of 'monetary', 'percentage', 'integer', 'float' "
                f"or a valid Python format spec (e.g., '.1f', '.2f', ',.0f'). "
                f"Error formatting value {value}: {e}"
            ) from e
