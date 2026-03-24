"""Reference resolver for {{...}} syntax in YAML v2.0 specification.

Supports:
- Simple references: {{column_name}}
- Nested dot notation: {{data.series.values}}
- Bracket notation: {{accounts["NASA Total"].values}}
- Format strings: {{value:.2f}}, {{date:%Y}}
- Monetary format specs: {{amount:$B}}, {{amount:$M}}, {{amount:$K}}, {{amount:$}}
"""

import re
from typing import Any

from tpsplots.exceptions import ConfigurationError

# Pattern to match {{...}} references
# Captures the content inside the braces
REFERENCE_PATTERN = re.compile(r"^\{\{([^{}]+)\}\}$")

# Pattern to find all {{...}} references in a string (for template substitution)
TEMPLATE_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")

# Pattern to match comma-separated {{...}} references (defensive guard for
# accidentally stringified arrays, e.g. "{{col1}},{{col2}}")
MULTI_REFERENCE_PATTERN = re.compile(r"^\s*\{\{[^{}]+\}\}\s*(,\s*\{\{[^{}]+\}\}\s*)+$")


# Monetary format specs: $B (billions), $M (millions), $K (thousands), $ (auto-scale)
_MONETARY_SCALES = {
    "$B": (1e9, "billion"),
    "$M": (1e6, "million"),
    "$K": (1e3, "thousand"),
}


def _format_monetary(value: float, spec: str) -> str:
    """Format a numeric value as a dollar amount.

    Specs:
        $B — divide by 1e9, label "billion"
        $M — divide by 1e6, label "million"
        $K — divide by 1e3, label "thousand"
        $  — auto-select scale based on magnitude
    """
    amount = float(value)
    is_neg = amount < 0
    amount = abs(amount)

    if spec == "$":
        # Auto-scale: pick the largest unit that yields >= 1
        for s, (factor, _label) in _MONETARY_SCALES.items():
            if amount >= factor:
                spec = s
                break
        else:
            # Under 1,000 — format as plain dollars
            formatted = f"${amount:,.0f}" if amount == int(amount) else f"${amount:,.2f}"
            return f"-{formatted}" if is_neg else formatted

    factor, label = _MONETARY_SCALES[spec]
    scaled = amount / factor

    # Use 1 decimal when < 10, 0 decimals when >= 10 (e.g., $6.4 billion, $12 billion)
    formatted = f"${scaled:,.1f} {label}" if scaled < 10 else f"${scaled:,.0f} {label}"

    return f"-{formatted}" if is_neg else formatted


class ReferenceResolver:
    """Resolves {{...}} data references against a data context."""

    @staticmethod
    def is_reference(value: str) -> bool:
        """Check if a string is a data reference (wrapped in {{...}})."""
        if not isinstance(value, str):
            return False
        return bool(REFERENCE_PATTERN.match(value.strip()))

    @staticmethod
    def contains_references(value: Any) -> bool:
        """Check recursively whether a value tree contains any {{...}} references."""
        if isinstance(value, str):
            return bool(TEMPLATE_PATTERN.search(value))
        if isinstance(value, dict):
            return any(ReferenceResolver.contains_references(v) for v in value.values())
        if isinstance(value, list):
            return any(ReferenceResolver.contains_references(item) for item in value)
        return False

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

        # Check for comma-separated complete references: "{{col1}},{{col2}}"
        # Must come before the single-ref check because REFERENCE_PATTERN's
        # ^\{\{(.+?)\}\}$ also matches multi-ref strings (anchored to outer braces).
        if MULTI_REFERENCE_PATTERN.match(value):
            individual_refs = re.findall(r"\{\{([^{}]+)\}\}", value)
            return [
                ReferenceResolver._resolve_reference(ref.strip(), data) for ref in individual_refs
            ]

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
        format_spec = None
        resolved = None

        if ":" in ref_expr:
            # Treat the first split whose path resolves as the format boundary.
            # This accepts full Python format specs like ",.0f" and "%H:%M",
            # while still falling back to literal colon-containing keys if no
            # candidate path resolves.
            for i, char in enumerate(ref_expr):
                if char != ":":
                    continue
                potential_path = ref_expr[:i].strip()
                potential_format = ref_expr[i + 1 :].strip()
                if not potential_path or not potential_format:
                    continue
                try:
                    resolved = ReferenceResolver._resolve_path(potential_path, data)
                except ConfigurationError:
                    continue
                ref_expr = potential_path
                format_spec = potential_format
                break

        # Resolve the path
        if resolved is None:
            resolved = ReferenceResolver._resolve_path(ref_expr, data)

        # Apply format specification if present
        if format_spec:
            # Check for monetary format specs ($B, $M, $K, $)
            if format_spec in _MONETARY_SCALES or format_spec == "$":
                try:
                    return _format_monetary(resolved, format_spec)
                except (ValueError, TypeError) as e:
                    raise ConfigurationError(
                        f"Cannot apply monetary format '{format_spec}' to value: {resolved}"
                    ) from e
            try:
                return format(resolved, format_spec)
            except (ValueError, TypeError) as e:
                raise ConfigurationError(
                    f"Cannot apply format '{format_spec}' to value: {resolved}"
                ) from e

        return resolved

    @staticmethod
    def _parse_path(path: str) -> list[str]:
        """Parse a path with dot and bracket notation into segments.

        Examples:
        - ``"column"`` → ``["column"]``
        - ``"data.series.values"`` → ``["data", "series", "values"]``
        - ``'accounts["NASA Total"].values'`` → ``["accounts", "NASA Total", "values"]``
        """
        segments: list[str] = []
        i = 0
        while i < len(path):
            if path[i] == "[":
                # Bracket notation: extract quoted key
                quote_start = path.find('"', i)
                if quote_start == -1:
                    quote_start = path.find("'", i)
                if quote_start == -1:
                    break
                quote_char = path[quote_start]
                quote_end = path.find(quote_char, quote_start + 1)
                if quote_end == -1:
                    break
                segments.append(path[quote_start + 1 : quote_end])
                # Skip past closing bracket
                i = path.find("]", quote_end)
                i = i + 1 if i != -1 else len(path)
                # Skip trailing dot
                if i < len(path) and path[i] == ".":
                    i += 1
            elif path[i] == ".":
                i += 1
            else:
                # Dot-notation segment: read until next dot or bracket
                end = i
                while end < len(path) and path[end] not in (".", "["):
                    end += 1
                segment = path[i:end].strip()
                if segment:
                    segments.append(segment)
                i = end
        return segments

    @staticmethod
    def _resolve_path(path: str, data: dict[str, Any]) -> Any:
        """
        Resolve a path against the data context.

        Examples:
        - "column" → data["column"]
        - "data.series.values" → data["data"]["series"]["values"]
        - 'accounts["NASA Total"].values' → data["accounts"]["NASA Total"]["values"]
        """
        parts = ReferenceResolver._parse_path(path)
        current = data

        for i, part in enumerate(parts):
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
