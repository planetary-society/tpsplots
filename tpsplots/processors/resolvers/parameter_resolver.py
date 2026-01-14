"""Parameter resolution for YAML chart processing."""

from typing import Any

from tpsplots.exceptions import ConfigurationError
from tpsplots.models.parameters import ParametersConfig


class ParameterResolver:
    """Resolves chart parameters by substituting data references."""

    @staticmethod
    def resolve(
        parameters: ParametersConfig, data: dict[str, Any], *, strict: bool = False
    ) -> dict[str, Any]:
        """
        Resolve parameters by substituting data references.

        Args:
            parameters: The parameters configuration from YAML
            data: The resolved data context

        Returns:
            Dictionary of resolved parameter values
        """
        # Convert Pydantic model to dict, excluding None values
        params_dict = parameters.model_dump(exclude_none=True)
        resolved = {}

        for key, value in params_dict.items():
            resolved[key] = ParameterResolver._resolve_value(key, value, data, strict=strict)

        return resolved

    @staticmethod
    def _resolve_value(
        key: str, value: Any, data: dict[str, Any], *, strict: bool
    ) -> Any:
        """
        Recursively resolve a parameter value against the data context.

        Args:
            value: The value to resolve (may be a data reference string)
            data: The data context for lookups

        Returns:
            The resolved value
        """
        if isinstance(value, str):
            # Check if it's a data reference (simple key lookup)
            if value in data:
                return data[value]

            if strict:
                if key in ParameterResolver._STRICT_REFERENCE_KEYS:
                    raise ConfigurationError(
                        f"Unresolved data reference for '{key}': {value}"
                    )

                if key in ParameterResolver._STRICT_ENUM_KEYS:
                    allowed = ParameterResolver._STRICT_ENUM_KEYS[key]
                    if value in allowed:
                        return value
                    allowed_list = sorted(allowed)
                    raise ConfigurationError(
                        f"Invalid value for '{key}': {value}. Allowed values: {allowed_list}"
                    )

            return value

        if isinstance(value, list):
            return [
                ParameterResolver._resolve_value(key, item, data, strict=strict) for item in value
            ]

        if isinstance(value, dict):
            return {
                k: ParameterResolver._resolve_value(key, v, data, strict=strict)
                for k, v in value.items()
            }

        return value

    _STRICT_REFERENCE_KEYS = {
        "data",
        "df",
        "x",
        "y",
        "xlim",
        "ylim",
        "export_data",
    }

    _STRICT_ENUM_KEYS = {
        "scale": {"billions", "millions", "thousands", "percentage"},
        "axis_scale": {"x", "y", "both"},
    }
