"""Custom exception hierarchy for tpsplots.

This module defines a structured exception hierarchy that provides
clear error classification for debugging and error handling.

Exception Hierarchy:
    TPSPlotsError (base)
    ├── ConfigurationError - Invalid YAML configuration
    ├── DataSourceError - Error loading or processing data
    └── RenderingError - Error during chart rendering
"""


class TPSPlotsError(Exception):
    """Base exception for all tpsplots errors.

    All tpsplots-specific exceptions inherit from this class,
    allowing users to catch all package errors with a single
    except clause if desired.

    Example:
        >>> try:
        ...     tpsplots.generate("invalid.yaml")
        ... except TPSPlotsError as e:
        ...     print(f"Chart generation failed: {e}")
    """

    pass


class ConfigurationError(TPSPlotsError):
    """Invalid YAML configuration.

    Raised when:
    - YAML file has invalid syntax
    - Required fields are missing
    - Field values fail validation
    - Chart type is not recognized

    Example:
        >>> raise ConfigurationError("Missing required field 'chart.type' in config.yaml")
    """

    pass


class DataSourceError(TPSPlotsError):
    """Error loading or processing data source.

    Raised when:
    - CSV file cannot be read
    - Google Sheets URL is inaccessible
    - Controller method not found or fails
    - Data format is invalid or unexpected

    Example:
        >>> raise DataSourceError("Could not load data from 'data.csv': File not found")
    """

    pass


class RenderingError(TPSPlotsError):
    """Error during chart rendering.

    Raised when:
    - Matplotlib fails to render the chart
    - Output file cannot be written
    - Required chart parameters are invalid
    - View method execution fails

    Example:
        >>> raise RenderingError(
        ...     "Failed to generate line_plot: x and y arrays must have same length"
        ... )
    """

    pass
