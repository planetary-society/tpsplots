"""Shared render pipeline used by both CLI and editor preview paths.

Extracts the common resolve-and-prepare sequence so that
``YAMLChartProcessor.generate_chart`` and ``EditorSession.render_preview``
produce identical ``RenderContext`` objects for the same validated config.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.resolvers import (
    ColorResolver,
    MetadataResolver,
    ParameterResolver,
)

logger = logging.getLogger(__name__)

METADATA_FIELDS = frozenset({"title", "subtitle", "source"})


@dataclass
class RenderContext:
    """Everything needed to dispatch a chart render."""

    chart_type_v1: str
    output_name: str
    resolved_metadata: dict[str, Any]
    resolved_params: dict[str, Any]


def build_render_context(
    validated: YAMLChartConfig,
    data: dict[str, Any],
    *,
    log_conflicts: bool = True,
) -> RenderContext:
    """Build a render context from a validated config and resolved data.

    This encapsulates the pipeline steps shared by CLI generation and
    editor preview: model_dump → metadata extraction → v2→v1 type
    mapping → escape-hatch separation → reference resolution → color
    resolution → series-override expansion → escape-hatch flattening.

    Args:
        validated: A fully validated ``YAMLChartConfig``.
        data: Resolved data dict (from ``DataResolver.resolve``).
        log_conflicts: If True, log warnings when escape-hatch keys
            overlap with typed params (CLI behaviour). If False,
            silently overwrite (editor behaviour).
    """
    chart_dict = validated.chart.model_dump(exclude_none=True)

    # Extract metadata fields
    metadata = {k: chart_dict.pop(k) for k in METADATA_FIELDS if k in chart_dict}

    # Extract control fields
    chart_type_v2 = chart_dict.pop("type")
    output_name = chart_dict.pop("output")
    chart_type_v1 = CHART_TYPES.get(chart_type_v2, f"{chart_type_v2}_plot")

    parameters = chart_dict

    # Pop escape-hatch dicts before reference resolution — they get
    # flattened back in *after* resolution so that raw matplotlib /
    # pywaffle kwargs pass through untouched.
    matplotlib_config = parameters.pop("matplotlib_config", None)
    pywaffle_config = parameters.pop("pywaffle_config", None)

    # Resolve {{...}} references in parameters and metadata
    resolved_params = ParameterResolver.resolve(parameters, data)
    resolved_metadata = MetadataResolver.resolve(metadata, data)

    # Resolve semantic color names to hex codes (recursively)
    resolved_params = ColorResolver.resolve_deep(resolved_params)

    # Expand typed series_overrides for the line/scatter view API
    resolved_params = expand_series_overrides(resolved_params)

    # Flatten escape-hatch dicts into resolved params
    for escape_name, escape_dict in [
        ("matplotlib_config", matplotlib_config),
        ("pywaffle_config", pywaffle_config),
    ]:
        if escape_dict:
            if log_conflicts:
                conflicts = set(escape_dict.keys()) & set(resolved_params.keys())
                if conflicts:
                    logger.warning(
                        "%s keys overlap with typed params and will override: %s",
                        escape_name,
                        conflicts,
                    )
            resolved_params.update(escape_dict)

    return RenderContext(
        chart_type_v1=chart_type_v1,
        output_name=output_name,
        resolved_metadata=resolved_metadata,
        resolved_params=resolved_params,
    )


def expand_series_overrides(parameters: dict[str, Any]) -> dict[str, Any]:
    """Expand structured series_overrides into legacy series_<n> kwargs.

    The line/scatter renderer expects per-series overrides under keys
    like ``series_0`` and ``series_1``. The chart config model stores
    these as a typed ``series_overrides`` dict keyed by index.
    """
    overrides = parameters.pop("series_overrides", None)
    if not overrides:
        return parameters

    if not isinstance(overrides, dict):
        logger.warning(
            "Expected series_overrides to be a dict, got %s; skipping expansion",
            type(overrides).__name__,
        )
        return parameters

    for raw_index, override in overrides.items():
        index = raw_index
        if isinstance(raw_index, str):
            if not raw_index.isdigit():
                logger.warning("Skipping non-numeric series_overrides key: %r", raw_index)
                continue
            index = int(raw_index)

        if not isinstance(index, int):
            logger.warning("Skipping invalid series_overrides key type: %r", raw_index)
            continue

        series_key = f"series_{index}"
        if series_key in parameters:
            logger.warning(
                "%s already exists in resolved params and will be overwritten by series_overrides",
                series_key,
            )
        parameters[series_key] = override

    return parameters
