"""Parameter resolution for YAML chart processing."""

from typing import Any

from tpsplots.models.parameters import ParametersConfig


class ParameterResolver:
    """Resolves chart parameters by substituting data references."""

    @staticmethod
    def resolve(parameters: ParametersConfig, data: dict[str, Any]) -> dict[str, Any]:
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
            resolved[key] = ParameterResolver._resolve_value(value, data)

        return resolved

    @staticmethod
    def _resolve_value(value: Any, data: dict[str, Any]) -> Any:
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
            else:
                return value
        elif isinstance(value, list):
            return [ParameterResolver._resolve_value(item, data) for item in value]
        elif isinstance(value, dict):
            return {k: ParameterResolver._resolve_value(v, data) for k, v in value.items()}
        else:
            return value
