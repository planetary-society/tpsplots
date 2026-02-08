"""Editor session: validates configs, renders previews, manages YAML files."""

from __future__ import annotations

import hashlib
import io
import logging
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

try:
    from ruamel.yaml import YAML
except ImportError:
    YAML = None

import yaml

from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.resolvers import (
    ColorResolver,
    DataResolver,
    MetadataResolver,
    ParameterResolver,
)
from tpsplots.views import VIEW_REGISTRY

logger = logging.getLogger(__name__)


class EditorSession:
    """Manages chart editor state: validation, preview rendering, file I/O.

    Security: all file operations are restricted to ``yaml_dir`` via
    ``_resolve_path`` which uses ``Path.resolve()`` + ``relative_to()``
    for symlink-safe containment.
    """

    def __init__(self, yaml_dir: Path, outdir: Path | None = None) -> None:
        self._root = yaml_dir.resolve(strict=True)
        self._outdir = outdir or Path("charts")
        self._data_cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Path security
    # ------------------------------------------------------------------

    def _resolve_path(self, relative: str) -> Path:
        """Resolve a relative path safely within yaml_dir.

        Rejects absolute paths and any traversal outside the root,
        including via symlinks.
        """
        if Path(relative).is_absolute():
            raise ValueError(f"Absolute paths are not allowed: {relative}")

        candidate = (self._root / relative).resolve()
        # Will raise ValueError if candidate is outside _root
        candidate.relative_to(self._root)
        return candidate

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_config(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Validate a full config dict, returning structured errors.

        Returns an empty list when valid. Each error dict has:
        - ``path``: JSON Pointer to the failing field (e.g. ``chart.xlim``)
        - ``message``: Human-readable description
        """
        errors: list[dict[str, Any]] = []
        try:
            YAMLChartConfig(**config)
        except Exception as exc:
            for err in _extract_pydantic_errors(exc):
                errors.append(err)
        return errors

    # ------------------------------------------------------------------
    # Data resolution (cached by source hash)
    # ------------------------------------------------------------------

    def _resolve_data(self, data_config: dict[str, Any]) -> dict[str, Any]:
        """Resolve data source, caching by content hash."""
        cache_key = hashlib.sha256(repr(sorted(data_config.items())).encode()).hexdigest()[:16]

        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        from tpsplots.models.data_sources import DataSourceConfig

        data_source = DataSourceConfig(**data_config)
        resolved = DataResolver.resolve(data_source)
        self._data_cache[cache_key] = resolved
        return resolved

    # ------------------------------------------------------------------
    # Preview rendering
    # ------------------------------------------------------------------

    def render_preview(
        self,
        config: dict[str, Any],
        device: str = "desktop",
    ) -> str:
        """Render a chart preview as SVG from a full config dict.

        Args:
            config: Full ``{data: {...}, chart: {...}}`` config dict.
            device: ``"desktop"`` or ``"mobile"``.

        Returns:
            SVG string.
        """
        if device not in {"desktop", "mobile"}:
            raise ValueError(f"Unsupported device: {device}")

        # Clean empty values injected by RJSF (empty strings, empty arrays, etc.)
        config = _clean_form_data(config)

        # Validate
        validated = YAMLChartConfig(**config)

        # Resolve data
        data = self._resolve_data(config["data"])

        # Extract chart params (mirrors YAMLChartProcessor.generate_chart)
        chart_dict = validated.chart.model_dump(exclude_none=True)

        metadata_fields = {"title", "subtitle", "source"}
        metadata = {k: chart_dict.pop(k) for k in metadata_fields if k in chart_dict}

        chart_type_v2 = chart_dict.pop("type")
        output_name = chart_dict.pop("output")
        chart_type_v1 = CHART_TYPES.get(chart_type_v2, f"{chart_type_v2}_plot")

        parameters = chart_dict

        # Pop escape-hatch dicts before resolution
        matplotlib_config = parameters.pop("matplotlib_config", None)
        pywaffle_config = parameters.pop("pywaffle_config", None)

        # Resolve references, colors, series overrides
        resolved_params = ParameterResolver.resolve(parameters, data)
        resolved_metadata = MetadataResolver.resolve(metadata, data)
        resolved_params = ColorResolver.resolve_deep(resolved_params)
        resolved_params = _expand_series_overrides(resolved_params)

        # Flatten escape hatches
        for escape_dict in (matplotlib_config, pywaffle_config):
            if escape_dict:
                resolved_params.update(escape_dict)

        # Dispatch to view
        view_class = VIEW_REGISTRY.get(chart_type_v1)
        if view_class is None:
            raise ValueError(f"Unknown chart type: {chart_type_v2}")

        view = view_class(outdir=self._outdir)
        plot_method = getattr(view, chart_type_v1)

        result: dict[str, Any] | None = None
        try:
            result = plot_method(
                metadata=resolved_metadata,
                stem=f"{output_name}_editor_preview",
                preview=True,
                **deepcopy(resolved_params),
            )

            fig = result[device]
            buf = io.StringIO()
            fig.savefig(buf, format="svg", dpi="figure")
            return buf.getvalue()
        finally:
            # Always close all figures to prevent leaks
            if result is not None:
                for key in ("desktop", "mobile"):
                    fig = result.get(key)
                    if fig is not None:
                        plt.close(fig)

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load_yaml(self, relative_path: str) -> dict[str, Any]:
        """Load a YAML file as a dict, path-restricted to yaml_dir."""
        path = self._resolve_path(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError(f"Not a YAML file: {relative_path}")

        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in {relative_path}")
        return data

    def save_yaml(self, relative_path: str, config: dict[str, Any]) -> None:
        """Save config to YAML, preserving comments for existing files.

        Uses ruamel.yaml round-trip editing when available and the file
        already exists. Falls back to plain yaml.dump for new files.
        """
        config = _prepare_config_for_save(config)
        path = self._resolve_path(relative_path)
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError(f"Not a YAML file: {relative_path}")

        if path.exists() and YAML is not None:
            self._save_roundtrip(path, config)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

    def _save_roundtrip(self, path: Path, config: dict[str, Any]) -> None:
        """Merge changed fields into existing YAML preserving comments."""
        rt = YAML(typ="rt")
        rt.preserve_quotes = True

        with path.open(encoding="utf-8") as f:
            existing = rt.load(f)

        if not isinstance(existing, dict):
            raise ValueError("Invalid YAML structure: expected a top-level mapping")

        _deep_replace(existing, config)

        with path.open("w", encoding="utf-8") as f:
            rt.dump(existing, f)

    def list_yaml_files(self) -> list[str]:
        """List YAML files in yaml_dir recursively as relative paths."""
        files: set[str] = set()
        for ext in ("*.yaml", "*.yml"):
            for path in self._root.rglob(ext):
                files.add(str(path.relative_to(self._root)))
        return sorted(files)

    def invalidate_data_cache(self) -> None:
        """Clear the data cache (e.g. after data source changes)."""
        self._data_cache.clear()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _prepare_config_for_save(config: dict[str, Any]) -> dict[str, Any]:
    """Clean and validate editor config before persisting it to YAML."""
    cleaned = _clean_form_data(config)
    try:
        validated = YAMLChartConfig(**cleaned)
    except Exception as exc:
        details = []
        for err in _extract_pydantic_errors(exc):
            if err["path"]:
                details.append(f"{err['path']}: {err['message']}")
            else:
                details.append(err["message"])
        raise ValueError(f"Configuration validation failed: {'; '.join(details)}") from exc
    return validated.model_dump(exclude_none=True)


def _deep_replace(target: MutableMapping[str, Any], source: Mapping[str, Any]) -> None:
    """Recursively replace mapping content to mirror source exactly."""
    for key in list(target.keys()):
        if key not in source:
            del target[key]

    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, MutableMapping) and isinstance(value, Mapping):
            _deep_replace(existing, value)
        else:
            target[key] = value


def _expand_series_overrides(parameters: dict[str, Any]) -> dict[str, Any]:
    """Expand series_overrides into legacy series_<n> kwargs."""
    overrides = parameters.pop("series_overrides", None)
    if not overrides or not isinstance(overrides, dict):
        return parameters

    for raw_index, override in overrides.items():
        index = raw_index
        if isinstance(raw_index, str):
            if not raw_index.isdigit():
                continue
            index = int(raw_index)
        if isinstance(index, int):
            parameters[f"series_{index}"] = override

    return parameters


def _clean_form_data(config: dict[str, Any]) -> dict[str, Any]:
    """Remove empty values that RJSF injects for unset fields.

    RJSF sets empty strings, empty arrays, and empty objects for
    fields that have no user-supplied value. The chart pipeline expects
    these to be absent (Pydantic defaults them to None).
    """
    cleaned = {}
    for key, value in config.items():
        if isinstance(value, dict):
            inner = _clean_form_data(value)
            if inner:
                cleaned[key] = inner
        elif isinstance(value, list) and len(value) == 0:
            continue  # drop empty arrays (e.g. figsize: [])
        elif isinstance(value, str) and value == "":
            continue  # drop empty strings
        else:
            cleaned[key] = value
    return cleaned


def _extract_pydantic_errors(exc: Exception) -> list[dict[str, Any]]:
    """Extract structured errors from a Pydantic ValidationError."""
    errors = []
    if hasattr(exc, "errors"):
        for err in exc.errors():
            loc = list(err.get("loc", []))
            if (
                len(loc) >= 3
                and loc[0] == "chart"
                and isinstance(loc[1], str)
                and loc[1] in CHART_TYPES
            ):
                loc = [loc[0], *loc[2:]]
            if loc:
                path = "/" + "/".join(
                    str(part).replace("~", "~0").replace("/", "~1") for part in loc
                )
            else:
                path = ""
            errors.append({"path": path, "message": err.get("msg", str(err))})
    else:
        errors.append({"path": "", "message": str(exc)})
    return errors
