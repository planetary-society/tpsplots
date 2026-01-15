"""Metadata resolution for YAML chart processing (v2.0 spec)."""

from typing import Any

from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver


class MetadataResolver:
    """Resolves chart metadata by substituting {{...}} data references."""

    @staticmethod
    def resolve(
        metadata: Any,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve metadata by substituting {{...}} data references and templates.

        Args:
            metadata: The metadata configuration (Pydantic model or dict)
            data: The resolved data context

        Returns:
            Dictionary of resolved metadata values
        """
        # Convert Pydantic model to dict if needed
        if hasattr(metadata, "model_dump"):
            metadata_dict = metadata.model_dump(exclude_none=True)
        elif isinstance(metadata, dict):
            metadata_dict = {k: v for k, v in metadata.items() if v is not None}
        else:
            metadata_dict = dict(metadata) if metadata else {}

        # Resolve all {{...}} references in the metadata
        return ReferenceResolver.resolve(metadata_dict, data)
