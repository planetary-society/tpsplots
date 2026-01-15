"""Reference resolver for {{...}} syntax in YAML v2.0 specification.

Supports:
- Simple references: {{column_name}}
- Nested dot notation: {{data.series.values}}
- Format strings: {{value:.2f}}, {{date:%Y}}
"""

import re
from typing import Any

from tpsplots.exceptions import ConfigurationError

# Pattern to match {{...}} references
# Captures the content inside the braces
REFERENCE_PATTERN = re.compile(r"^\{\{(.+?)\}\}$")

# Pattern to find all {{...}} references in a string (for template substitution)
TEMPLATE_PATTERN = re.compile(r"\{\{(.+?)\}\}")


class ReferenceResolver:
    """Resolves {{...}} data references against a data context."""

    @staticmethod
    def is_reference(value: str) -> bool:
        """Check if a string is a data reference (wrapped in {{...}})."""
        if not isinstance(value, str):
            return False
        return bool(REFERENCE_PATTERN.match(value.strip()))

    @staticmethod
    def resolve(value: Any, data: dict[str, Any]) -> Any:
        """
        Resolve a value, substituting any {{...}} references.

        Args:
            value: The value to resolve (may contain {{...}} references)
            data: The data context for lookups

        Returns:
            The resolved value

        Raises:
            ConfigurationError: If a reference cannot be resolved
        """
        if isinstance(value, str):
            return ReferenceResolver._resolve_string(value, data)

        if isinstance(value, list):
            return [ReferenceResolver.resolve(item, data) for item in value]

        if isinstance(value, dict):
            return {k: ReferenceResolver.resolve(v, data) for k, v in value.items()}

        # Non-string, non-collection values pass through unchanged
        return value

    @staticmethod
    def _resolve_string(value: str, data: dict[str, Any]) -> Any:
        """
        Resolve a string value.

        If the entire string is a single reference ({{...}}), return the resolved value.
        If the string contains embedded references, perform template substitution.
        Otherwise, return the literal string.
        """
        value = value.strip()

        # Check for single complete reference: "{{column}}"
        match = REFERENCE_PATTERN.match(value)
        if match:
            ref_expr = match.group(1).strip()
            return ReferenceResolver._resolve_reference(ref_expr, data)

        # Check for embedded references: "Total: {{value}} items"
        if TEMPLATE_PATTERN.search(value):
            return ReferenceResolver._resolve_template(value, data)

        # Literal string - no references
        return value

    @staticmethod
    def _resolve_reference(ref_expr: str, data: dict[str, Any]) -> Any:
        """
        Resolve a single reference expression.

        Handles:
        - Simple: "column_name"
        - Nested: "data.series.values"
        - Formatted: "value:.2f"
        """
        # Check for format specification
        format_spec = None
        if ":" in ref_expr:
            # Split on last colon to handle nested paths with colons
            # But be careful: format specs are typically short (e.g., .2f, %Y)
            # Use heuristic: if part after colon looks like format spec, treat as such
            parts = ref_expr.rsplit(":", 1)
            if len(parts) == 2:
                potential_path, potential_format = parts
                # Format specs are typically short and don't contain dots
                if len(potential_format) <= 10 and "." not in potential_format.lstrip("."):
                    ref_expr = potential_path.strip()
                    format_spec = potential_format.strip()

        # Resolve the path
        resolved = ReferenceResolver._resolve_path(ref_expr, data)

        # Apply format specification if present
        if format_spec:
            try:
                return format(resolved, format_spec)
            except (ValueError, TypeError) as e:
                raise ConfigurationError(
                    f"Cannot apply format '{format_spec}' to value: {resolved}"
                ) from e

        return resolved

    @staticmethod
    def _resolve_path(path: str, data: dict[str, Any]) -> Any:
        """
        Resolve a dot-notation path against the data context.

        Examples:
        - "column" → data["column"]
        - "data.series.values" → data["data"]["series"]["values"]
        """
        parts = path.split(".")
        current = data

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            if isinstance(current, dict):
                if part not in current:
                    traversed = ".".join(parts[:i]) if i > 0 else "(root)"
                    raise ConfigurationError(
                        f"Reference '{{{{path}}}}' not found: key '{part}' does not exist. "
                        f"Traversed: {traversed}. Available keys: {list(current.keys())}"
                    )
                current = current[part]
            elif hasattr(current, part):
                # Support attribute access for objects
                current = getattr(current, part)
            else:
                traversed = ".".join(parts[:i]) if i > 0 else "(root)"
                raise ConfigurationError(
                    f"Reference '{{{{path}}}}' not found: cannot access '{part}' "
                    f"on {type(current).__name__}. Traversed: {traversed}"
                )

        return current

    @staticmethod
    def _resolve_template(template: str, data: dict[str, Any]) -> str:
        """
        Resolve a template string with embedded references.

        Example: "Total: {{value:.2f}} items" → "Total: 123.45 items"
        """

        def replace_match(match: re.Match) -> str:
            ref_expr = match.group(1).strip()
            resolved = ReferenceResolver._resolve_reference(ref_expr, data)
            return str(resolved)

        return TEMPLATE_PATTERN.sub(replace_match, template)


# Convenience function for external use
def resolve_references(value: Any, data: dict[str, Any]) -> Any:
    """Resolve all {{...}} references in a value against the data context."""
    return ReferenceResolver.resolve(value, data)
