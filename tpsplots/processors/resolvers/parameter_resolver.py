"""Parameter resolution for YAML chart processing (v2.0 spec)."""

from typing import Any

from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver


class ParameterResolver:
    """Resolves chart parameters by substituting {{...}} data references."""

    @staticmethod
    def resolve(
        parameters: Any,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve parameters by substituting {{...}} data references.

        Args:
            parameters: The parameters configuration (Pydantic model or dict)
            data: The resolved data context

        Returns:
            Dictionary of resolved parameter values
        """
        # Convert Pydantic model to dict if needed
        if hasattr(parameters, "model_dump"):
            params_dict = parameters.model_dump(exclude_none=True)
        elif isinstance(parameters, dict):
            params_dict = {k: v for k, v in parameters.items() if v is not None}
        else:
            params_dict = dict(parameters) if parameters else {}

        # Resolve all {{...}} references in the parameters
        return ReferenceResolver.resolve(params_dict, data)
