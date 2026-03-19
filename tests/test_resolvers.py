"""Tests for resolver behavior (v2.0 spec)."""

import pytest

from tpsplots.exceptions import ConfigurationError
from tpsplots.processors.resolvers import ParameterResolver
from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver


class TestReferenceResolver:
    """Tests for the new {{...}} reference resolver."""

    def test_simple_reference(self):
        """Test simple {{column}} reference resolution."""
        data = {"column": [1, 2, 3]}
        result = ReferenceResolver.resolve("{{column}}", data)
        assert result == [1, 2, 3]

    def test_literal_string(self):
        """Test that strings without {{...}} are literal."""
        data = {"column": [1, 2, 3]}
        result = ReferenceResolver.resolve("literal_string", data)
        assert result == "literal_string"

    def test_nested_dot_notation(self):
        """Test nested {{data.series.values}} reference."""
        data = {"data": {"series": {"values": [1, 2, 3]}}}
        result = ReferenceResolver.resolve("{{data.series.values}}", data)
        assert result == [1, 2, 3]

    def test_format_string(self):
        """Test {{value:.2f}} format string."""
        data = {"value": 3.14159}
        result = ReferenceResolver.resolve("{{value:.2f}}", data)
        assert result == "3.14"

    def test_template_substitution(self):
        """Test embedded references in string: 'Total: {{value}}'."""
        data = {"value": 42}
        result = ReferenceResolver.resolve("Total: {{value}} items", data)
        assert result == "Total: 42 items"

    def test_unresolved_reference_raises_error(self):
        """Test that unresolved references raise ConfigurationError."""
        data = {"existing": 1}
        with pytest.raises(ConfigurationError):
            ReferenceResolver.resolve("{{missing}}", data)

    def test_list_resolution(self):
        """Test that lists are recursively resolved."""
        data = {"a": 1, "b": 2}
        result = ReferenceResolver.resolve(["{{a}}", "{{b}}"], data)
        assert result == [1, 2]

    def test_dict_resolution(self):
        """Test that dicts are recursively resolved."""
        data = {"value": 42}
        result = ReferenceResolver.resolve({"key": "{{value}}"}, data)
        assert result == {"key": 42}

    def test_is_reference(self):
        """Test is_reference detection."""
        assert ReferenceResolver.is_reference("{{column}}")
        assert ReferenceResolver.is_reference("  {{column}}  ")
        assert not ReferenceResolver.is_reference("column")
        assert not ReferenceResolver.is_reference("{{column}} extra")

    def test_is_reference_rejects_mixed_template_string(self):
        """Mixed template strings are not single complete references."""
        value = "{{metadata.last_fte}} FTEs in {{metadata.max_fiscal_year}}"
        assert not ReferenceResolver.is_reference(value)

    # ── Monetary format specs ──────────────────────────────────────

    def test_monetary_billions(self):
        """{{amount:$B}} formats as dollar billions."""
        data = {"amount": 6_417_000_000}
        assert ReferenceResolver.resolve("{{amount:$B}}", data) == "$6.4 billion"

    def test_monetary_billions_large(self):
        """Amounts >= $10B use 0 decimal places."""
        data = {"amount": 12_500_000_000}
        assert ReferenceResolver.resolve("{{amount:$B}}", data) == "$12 billion"

    def test_monetary_millions(self):
        """{{amount:$M}} formats as dollar millions."""
        data = {"amount": 342_600_000}
        assert ReferenceResolver.resolve("{{amount:$M}}", data) == "$343 million"

    def test_monetary_millions_small(self):
        """Amounts < $10M use 1 decimal place."""
        data = {"amount": 3_400_000}
        assert ReferenceResolver.resolve("{{amount:$M}}", data) == "$3.4 million"

    def test_monetary_thousands(self):
        """{{amount:$K}} formats as dollar thousands."""
        data = {"amount": 52_300}
        assert ReferenceResolver.resolve("{{amount:$K}}", data) == "$52 thousand"

    def test_monetary_auto_billions(self):
        """{{amount:$}} auto-selects billions for large values."""
        data = {"amount": 6_417_000_000}
        assert ReferenceResolver.resolve("{{amount:$}}", data) == "$6.4 billion"

    def test_monetary_auto_millions(self):
        """{{amount:$}} auto-selects millions for mid-range values."""
        data = {"amount": 342_600_000}
        assert ReferenceResolver.resolve("{{amount:$}}", data) == "$343 million"

    def test_monetary_auto_thousands(self):
        """{{amount:$}} auto-selects thousands for smaller values."""
        data = {"amount": 52_300}
        assert ReferenceResolver.resolve("{{amount:$}}", data) == "$52 thousand"

    def test_monetary_auto_plain(self):
        """{{amount:$}} formats small values as plain dollars."""
        data = {"amount": 750}
        assert ReferenceResolver.resolve("{{amount:$}}", data) == "$750"

    def test_monetary_negative(self):
        """Negative amounts get a leading minus sign."""
        data = {"amount": -1_500_000_000}
        assert ReferenceResolver.resolve("{{amount:$B}}", data) == "-$1.5 billion"

    def test_monetary_in_template(self):
        """Monetary format works in embedded templates."""
        data = {"cost": 6_417_000_000}
        result = ReferenceResolver.resolve("NASA spent {{cost:$B}} on Saturn V", data)
        assert result == "NASA spent $6.4 billion on Saturn V"

    def test_monetary_zero(self):
        """Zero formats cleanly."""
        data = {"amount": 0}
        assert ReferenceResolver.resolve("{{amount:$B}}", data) == "$0.0 billion"

    def test_monetary_integer_input(self):
        """Integer values are accepted."""
        data = {"amount": 1_000_000_000}
        assert ReferenceResolver.resolve("{{amount:$B}}", data) == "$1.0 billion"

    def test_monetary_non_numeric_raises(self):
        """Non-numeric values raise ConfigurationError."""
        data = {"amount": "not a number"}
        with pytest.raises(ConfigurationError, match="monetary format"):
            ReferenceResolver.resolve("{{amount:$B}}", data)

    def test_comma_separated_refs_resolved_as_list(self):
        """Comma-separated {{...}} refs are split and resolved as a list."""
        data = {"col1": [1, 2], "col2": [3, 4]}
        result = ReferenceResolver.resolve("{{col1}},{{col2}}", data)
        assert result == [[1, 2], [3, 4]]

    def test_comma_separated_refs_with_spaces(self):
        """Comma-separated refs with whitespace are handled identically."""
        data = {"col1": [1], "col2": [2]}
        result = ReferenceResolver.resolve("{{col1}}, {{col2}}", data)
        assert result == [[1], [2]]

    def test_single_ref_not_treated_as_multi(self):
        """A single {{...}} ref still resolves normally (no regression)."""
        data = {"col": [1, 2, 3]}
        result = ReferenceResolver.resolve("{{col}}", data)
        assert result == [1, 2, 3]

    def test_template_string_not_treated_as_multi_ref(self):
        """Embedded refs like 'Total: {{val}}' stay as template substitution."""
        data = {"val": 42}
        result = ReferenceResolver.resolve("Total: {{val}}", data)
        assert result == "Total: 42"

    def test_mixed_template_starting_with_reference_resolves_as_template(self):
        """Mixed templates that start and end with refs should not be parsed as one ref."""
        data = {"metadata": {"last_fte": 12345, "max_fiscal_year": 2025}}
        value = "{{metadata.last_fte}} FTEs in {{metadata.max_fiscal_year}}"
        result = ReferenceResolver.resolve(value, data)
        assert result == "12345 FTEs in 2025"

    def test_format_string_with_thousands_separator_and_precision(self):
        """Valid Python specs like :,.0f should be accepted."""
        data = {"metadata": {"last_fte": 12345.0}}
        result = ReferenceResolver.resolve("{{metadata.last_fte:,.0f}}", data)
        assert result == "12,345"

    def test_format_string_with_alignment_thousands_separator_and_precision(self):
        """More complex Python format specs should pass through to format()."""
        data = {"metadata": {"last_fte": 12345.0}}
        result = ReferenceResolver.resolve("{{metadata.last_fte:>10,.0f}}", data)
        assert result == "    12,345"


class TestParameterResolver:
    """Tests for parameter resolution."""

    def test_resolve_dict_params(self):
        """Test resolving parameters from a dict."""
        params = {"x": "{{x_data}}", "y": "{{y_data}}", "grid": True}
        data = {"x_data": [1, 2, 3], "y_data": [4, 5, 6]}

        result = ParameterResolver.resolve(params, data)

        assert result["x"] == [1, 2, 3]
        assert result["y"] == [4, 5, 6]
        assert result["grid"] is True

    def test_resolve_preserves_non_references(self):
        """Test that non-reference values are preserved."""
        params = {"color": "NeptuneBlue", "linewidth": 3}
        data = {}

        result = ParameterResolver.resolve(params, data)

        assert result["color"] == "NeptuneBlue"
        assert result["linewidth"] == 3

    def test_resolve_nested_params(self):
        """Test resolving nested parameter structures."""
        params = {
            "direct_line_labels": {
                "fontsize": "{{label_size}}",
                "position": "right",
            }
        }
        data = {"label_size": 12}

        result = ParameterResolver.resolve(params, data)

        assert result["direct_line_labels"]["fontsize"] == 12
        assert result["direct_line_labels"]["position"] == "right"
