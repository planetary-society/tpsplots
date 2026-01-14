"""Tests for resolver behavior."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tpsplots.exceptions import ConfigurationError
from tpsplots.models.data_sources import ControllerMethodDataSource
from tpsplots.models.parameters import ParametersConfig
from tpsplots.processors.resolvers import DataResolver, ParameterResolver


def test_data_resolver_loads_controller_from_path():
    """Controller classes can be loaded from a local file path."""
    controller_code = (
        "class CustomController:\n"
        "    def build(self):\n"
        "        return {'value': [1, 2, 3]}\n"
    )

    with TemporaryDirectory() as tmpdir:
        controller_path = Path(tmpdir) / "custom_controller.py"
        controller_path.write_text(controller_code, encoding="utf-8")

        data_source = ControllerMethodDataSource.model_validate(
            {
                "type": "controller_method",
                "class": "CustomController",
                "method": "build",
                "path": str(controller_path),
            }
        )
        data = DataResolver.resolve(data_source)

        assert data["value"] == [1, 2, 3]


def test_parameter_resolver_strict_unresolved_reference():
    """Strict mode errors on unresolved parameter references."""
    params = ParametersConfig(x="missing_data", y="present_data")
    data = {"present_data": [1, 2, 3]}

    with pytest.raises(ConfigurationError):
        ParameterResolver.resolve(params, data, strict=True)
