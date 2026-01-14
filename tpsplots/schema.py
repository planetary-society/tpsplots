"""JSON Schema generation for YAML chart configurations."""

import json
from typing import Any


def get_json_schema() -> dict[str, Any]:
    """
    Generate JSON Schema for YAML chart configuration.

    This schema can be used with IDE extensions to provide autocomplete
    and validation for YAML configuration files.

    Returns:
        dict: JSON Schema as a dictionary

    Example:
        >>> schema = get_json_schema()
        >>> with open("schema.json", "w") as f:
        ...     json.dump(schema, f, indent=2)
    """
    from tpsplots.models import YAMLChartConfig

    schema = YAMLChartConfig.model_json_schema()

    # Add JSON Schema metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "TPS Charts YAML Configuration"
    schema["description"] = (
        "Configuration schema for tpsplots YAML chart definitions. "
        "Use this schema to get autocomplete and validation in your IDE."
    )

    return schema


def get_json_schema_string(indent: int = 2) -> str:
    """
    Generate JSON Schema as a formatted string.

    Args:
        indent: Number of spaces for indentation (default: 2)

    Returns:
        str: JSON Schema as a formatted JSON string
    """
    return json.dumps(get_json_schema(), indent=indent)


def get_chart_types() -> list[str]:
    """
    Get list of available chart types.

    Returns:
        list[str]: Sorted list of chart type identifiers
    """
    from tpsplots.views import VIEW_REGISTRY

    return sorted(VIEW_REGISTRY.keys())


def get_data_source_types() -> list[str]:
    """
    Get list of supported data source types.

    Returns:
        list[str]: List of data source type identifiers
    """
    return ["csv_file", "google_sheets", "controller_method"]
