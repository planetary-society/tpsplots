"""Metadata resolution for YAML chart processing."""

import logging
from typing import Any

from tpsplots.exceptions import ConfigurationError
from tpsplots.models.chart_config import MetadataConfig

logger = logging.getLogger(__name__)


class MetadataResolver:
    """Resolves chart metadata by substituting data references and templates."""

    @staticmethod
    def resolve(
        metadata: MetadataConfig, data: dict[str, Any], *, strict: bool = False
    ) -> dict[str, Any]:
        """
        Resolve metadata by substituting data references and template variables.

        Args:
            metadata: The metadata configuration from YAML
            data: The resolved data context

        Returns:
            Dictionary of resolved metadata values
        """
        # Convert Pydantic model to dict, excluding None values
        metadata_dict = metadata.model_dump(exclude_none=True)
        resolved = {}

        for key, value in metadata_dict.items():
            if isinstance(value, str):
                # First check if it's a direct data reference
                if value in data:
                    resolved[key] = data[value]
                    continue

                # Then check if it contains template syntax
                if "{" in value and "}" in value:
                    try:
                        # Create format context for template substitution
                        format_context = data.copy()
                        format_context["data"] = data
                        resolved[key] = value.format(**format_context)
                        continue
                    except (KeyError, ValueError) as e:
                        if strict:
                            raise ConfigurationError(
                                f"Unresolved template in metadata.{key}: {e}"
                            ) from e
                        logger.warning(f"Could not resolve template in metadata.{key}: {e}")
                        resolved[key] = value
                        continue

                # Use literal value
                resolved[key] = value
            else:
                # For non-string values, use existing _resolve_value logic
                resolved[key] = MetadataResolver._resolve_value(value, data)

        return resolved

    @staticmethod
    def _resolve_value(value: Any, data: dict[str, Any]) -> Any:
        """
        Recursively resolve a value against the data context.

        Args:
            value: The value to resolve
            data: The data context for lookups

        Returns:
            The resolved value
        """
        if isinstance(value, str):
            if value in data:
                return data[value]
            else:
                return value
        elif isinstance(value, list):
            return [MetadataResolver._resolve_value(item, data) for item in value]
        elif isinstance(value, dict):
            return {k: MetadataResolver._resolve_value(v, data) for k, v in value.items()}
        else:
            return value
