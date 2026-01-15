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
