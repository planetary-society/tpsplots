"""Editor session: validates configs, renders previews, manages YAML files."""

from __future__ import annotations

import hashlib
import io
import json
import logging
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

try:
    from ruamel.yaml import YAML
except ImportError:
    YAML = None

import yaml

from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.models.data_sources import DataSourceConfig
from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.render_pipeline import build_render_context
from tpsplots.processors.resolvers import DataResolver
from tpsplots.views import VIEW_REGISTRY

logger = logging.getLogger(__name__)


class EditorSession:
    """Manages chart editor state: validation, preview rendering, file I/O.

    Security: only YAML *load and save* are restricted to ``yaml_dir`` via
    ``_resolve_path`` (``Path.resolve()`` + ``relative_to()`` for symlink-safe
    containment). Data sources are intentionally NOT contained: CSV paths and
    controller modules referenced by a config are loaded from anywhere on disk,
    exactly like the ``tpsplots`` CLI, which also imports arbitrary controllers.
    Treat the editor as trusted-input only (see ``_resolve_data``).
    """

    def __init__(self, yaml_dir: Path, outdir: Path | None = None) -> None:
        self._root = yaml_dir.resolve(strict=True)
        self._outdir = outdir or Path("charts")
        self._data_cache: dict[str, Any] = {}
        self._profile_cache: dict[str, dict[str, Any]] = {}

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
        resolved, data_error = self._resolve_chart_templates(config)
        if data_error is not None:
            # A config full of unresolved {{refs}} whose data source is broken
            # would otherwise pass Pydantic validation (the refs are valid
            # strings). Surface the real data error so validation fails.
            errors.append({"path": "/data/source", "message": str(data_error)})
        try:
            YAMLChartConfig(**resolved)
        except Exception as exc:
            for err in _extract_pydantic_errors(exc):
                errors.append(err)
        return errors

    # ------------------------------------------------------------------
    # Data resolution (cached by source hash)
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _local_source_mtime_ns(self, data_config: dict[str, Any]) -> int | None:
        """Return the mtime (ns) of a local file data source, or ``None``.

        Only local CSV file sources have a meaningful mtime; URLs and
        controllers return ``None`` so their cache behavior is unchanged.
        Mixing the mtime into the cache key means edits to a local CSV are
        picked up automatically instead of being served stale until restart.
        """
        source = data_config.get("source")
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            kind, target, _ = DataResolver._parse_source(source)
        except Exception:
            return None
        if kind != "csv":
            return None

        # Stat the same path the CSV loader reads (cwd-relative when relative).
        path = Path(target).expanduser()
        try:
            return path.stat().st_mtime_ns if path.is_file() else None
        except OSError:
            return None

    def _data_cache_key(self, data_config: dict[str, Any]) -> str:
        """Build a cache key from the data config plus any local file mtime."""
        base = self._hash_payload(data_config)
        mtime = self._local_source_mtime_ns(data_config)
        return base if mtime is None else f"{base}:{mtime}"

    @staticmethod
    def _evict_stale_variants(cache: dict[str, Any], cache_key: str) -> None:
        """Drop entries for older mtimes of the same config from a cache."""
        base = cache_key.split(":", 1)[0]
        for key in [k for k in cache if k != cache_key and k.split(":", 1)[0] == base]:
            del cache[key]

    def _resolve_data(self, data_config: dict[str, Any]) -> dict[str, Any]:
        """Resolve data source, caching by content hash (+ local file mtime).

        Note: data sources are intentionally NOT path-restricted to
        ``yaml_dir``. CSV paths and controller modules are resolved from
        anywhere on disk (and controllers execute arbitrary code), matching
        the CLI's behavior. The editor is a trusted-input tool.
        """
        cache_key = self._data_cache_key(data_config)

        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        data_source = DataSourceConfig(**data_config)
        resolved = DataResolver.resolve(data_source)
        self._evict_stale_variants(self._data_cache, cache_key)
        self._data_cache[cache_key] = resolved
        return resolved

    def _resolve_chart_templates(
        self, config: dict[str, Any]
    ) -> tuple[dict[str, Any], Exception | None]:
        """Resolve {{...}} refs in the chart section before validation.

        Uses the editor's cached data resolution.  Returns
        ``(config, data_error)`` where ``data_error`` is the exception raised
        while loading the data source, or ``None`` on success / when there is
        nothing to resolve.

        The original config is returned unchanged (with ``data_error`` set) if
        data loading fails, so ``validate_config`` can surface the real error
        while ``render_preview`` / ``preflight`` (which ignore ``data_error``)
        re-encounter the same failure downstream, keeping their behavior
        unchanged.
        """
        from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver

        data_section = config.get("data")
        chart_section = config.get("chart")

        if not data_section or not chart_section:
            return config, None

        if not ReferenceResolver.contains_references(chart_section):
            return config, None

        try:
            data = self._resolve_data(data_section)
        except Exception as exc:
            return config, exc

        resolved_chart = ReferenceResolver.resolve(dict(chart_section), data)
        return {**config, "chart": resolved_chart}, None

    def profile_data(self, data_config: dict[str, Any]) -> dict[str, Any]:
        """Return data profile details for a source configuration."""
        cache_key = self._data_cache_key(data_config)
        if cache_key in self._profile_cache:
            return self._profile_cache[cache_key]

        data_source = DataSourceConfig(**data_config)
        resolved = self._resolve_data(data_config)
        parsed_kind, _, _ = DataResolver._parse_source(data_source.source)
        source_kind = "controller" if parsed_kind.startswith("controller") else parsed_kind

        data_frame = resolved.get("data")
        warnings: list[str] = []
        columns: list[dict[str, Any]] = []
        sample_rows: list[dict[str, Any]] = []
        row_count = 0

        if isinstance(data_frame, pd.DataFrame):
            row_count = len(data_frame)
            columns = [
                {
                    "name": str(col),
                    "dtype": str(data_frame[col].dtype),
                }
                for col in data_frame.columns
            ]
            sample_rows = data_frame.head(25).to_dict(orient="records")
        else:
            warnings.append("Resolved source did not return a 'data' DataFrame")
            row_count = 0

        context_keys = sorted(str(key) for key in resolved if key != "data")

        profile = {
            "source_kind": source_kind,
            "row_count": row_count,
            "columns": columns,
            "sample_rows": sample_rows,
            "warnings": warnings,
            "context_keys": context_keys,
        }
        self._evict_stale_variants(self._profile_cache, cache_key)
        self._profile_cache[cache_key] = profile
        return profile

    def preflight(self, config: dict[str, Any]) -> dict[str, Any]:
        """Run lightweight guided preflight checks for editor UX."""
        from tpsplots.editor.ui_schema import OPTIONAL_BINDING_FIELDS, get_primary_binding_fields

        cleaned = _clean_form_data(config)
        validation_errors = self.validate_config(cleaned)
        blocking_errors = [{"path": e["path"], "message": e["message"]} for e in validation_errors]
        missing_paths: list[str] = []
        warnings: list[str] = []

        data_cfg = cleaned.get("data", {}) if isinstance(cleaned.get("data"), dict) else {}
        chart_cfg = cleaned.get("chart", {}) if isinstance(cleaned.get("chart"), dict) else {}
        source = data_cfg.get("source")
        chart_type = chart_cfg.get("type")
        primary_bindings = get_primary_binding_fields(chart_type) if chart_type else []

        if not source:
            missing_paths.append("/data/source")
            data_ready = False
        else:
            data_ready = True
            try:
                profile = self.profile_data(data_cfg)
                if profile.get("warnings"):
                    warnings.extend(profile["warnings"])
            except Exception as exc:
                data_ready = False
                blocking_errors.append({"path": "/data/source", "message": str(exc)})

        for field in primary_bindings:
            if field in OPTIONAL_BINDING_FIELDS:
                continue
            value = chart_cfg.get(field)
            if value in (None, "", [], {}):
                missing_paths.append(f"/chart/{field}")

        if data_ready and not blocking_errors and not missing_paths:
            try:
                resolved, _ = self._resolve_chart_templates(cleaned)
                validated = YAMLChartConfig(**resolved)
                data = self._resolve_data(cleaned["data"])
                build_render_context(validated, data, log_conflicts=False)
            except Exception as exc:
                blocking_errors.append({"path": "/chart", "message": str(exc)})

        # validate_config and profile_data can both report the same broken
        # data source; collapse duplicates (keeping first position) via dict keying.
        blocking_errors = list(
            {(err["path"], err["message"]): err for err in blocking_errors}.values()
        )

        missing_paths = sorted(set(missing_paths))
        ready = len(blocking_errors) == 0 and len(missing_paths) == 0

        step_status = {
            "data_source_and_preparation": (
                "complete" if data_ready else ("error" if source else "not_started")
            ),
            "data_bindings": (
                "complete"
                if primary_bindings
                and all(
                    f"/chart/{f}" not in missing_paths
                    for f in primary_bindings
                    if f not in OPTIONAL_BINDING_FIELDS
                )
                else ("error" if primary_bindings else "not_started")
            ),
            "visual_design": "in_progress" if source else "not_started",
            "annotation_output": "in_progress" if source else "not_started",
        }

        return {
            "ready_for_preview": ready,
            "missing_paths": missing_paths,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "step_status": step_status,
        }

    # ------------------------------------------------------------------
    # Preview rendering
    # ------------------------------------------------------------------

    def render_preview(
        self,
        config: dict[str, Any],
        device: str = "desktop",
    ) -> bytes:
        """Render a chart preview as PNG from a full config dict.

        Args:
            config: Full ``{data: {...}, chart: {...}}`` config dict.
            device: ``"desktop"`` or ``"mobile"``.

        Returns:
            PNG image bytes.
        """
        if device not in {"desktop", "mobile"}:
            raise ValueError(f"Unsupported device: {device}")

        # Drop empty values (empty strings, empty arrays, etc.) the editor form
        # emits for unset fields, so the pipeline sees them as absent.
        config = _clean_form_data(config)

        # Resolve {{...}} template refs, then validate
        config, _ = self._resolve_chart_templates(config)
        validated = YAMLChartConfig(**config)

        # Resolve data
        data = self._resolve_data(config["data"])

        # Build render context (shared with CLI path)
        ctx = build_render_context(validated, data, log_conflicts=False)

        # Dispatch to view
        view_class = VIEW_REGISTRY.get(ctx.chart_type_v1)
        if view_class is None:
            raise ValueError(f"Unknown chart type: {ctx.chart_type_v1}")

        view = view_class(outdir=self._outdir)
        fig = view.create_figure(
            metadata=ctx.resolved_metadata,
            device=device,
            dpi=150,
            **deepcopy(ctx.resolved_params),
        )
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi="figure")
            return buf.getvalue()
        finally:
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
        config = self._prepare_config_for_save(config)
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
        # ruamel re-emits every line through its serializer, so these settings
        # decide churn on untouched keys: without a large width it re-wraps any
        # line over 80 chars, and the indent must match the dominant hand-written
        # style in yaml/ (indented dashes) or every block sequence re-indents.
        rt.width = 100_000
        rt.indent(mapping=2, sequence=4, offset=2)

        with path.open(encoding="utf-8") as f:
            existing = rt.load(f)

        if not isinstance(existing, dict):
            raise ValueError("Invalid YAML structure: expected a top-level mapping")

        # The editor only manages the keys it round-trips (see
        # _EDITOR_MANAGED_KEYS). Everything else at the top level (notably an
        # `animation:` block) is unmanaged — protect it from the deletion pass
        # so saving does not silently drop it. Derived from the declared
        # managed set, NOT from this save's payload: a payload-derived set
        # would resurrect deleted blocks if the editor ever manages them.
        protected_keys = set(existing) - _EDITOR_MANAGED_KEYS
        _deep_replace(existing, config, protected_keys=protected_keys)

        with path.open("w", encoding="utf-8") as f:
            rt.dump(existing, f)

    def _prepare_config_for_save(self, config: dict[str, Any]) -> dict[str, Any]:
        """Clean and validate editor config before persisting it to YAML.

        Validation is a *gate only*: the returned payload is the cleaned raw
        input dict, never a ``model_dump`` of the validated model. Dumping the
        model would materialize every non-None default into the file (and make
        force-saving an invalid config impossible), whereas the raw dict keeps
        saved YAML minimal and faithful to what the user actually set.

        ``{{refs}}`` are resolved for validation when the data source loads;
        when it does not (offline Google Sheets, broken controller), the
        unresolved config is validated instead so saving still works — the
        refs themselves are valid strings.
        """
        cleaned = _clean_form_data(config)
        resolved, _data_error = self._resolve_chart_templates(cleaned)
        try:
            YAMLChartConfig(**resolved)
        except Exception as exc:
            details = []
            for err in _extract_pydantic_errors(exc):
                if err["path"]:
                    details.append(f"{err['path']}: {err['message']}")
                else:
                    details.append(err["message"])
            raise ValueError(f"Configuration validation failed: {'; '.join(details)}") from exc
        return cleaned

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
        self._profile_cache.clear()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# Top-level YAML keys the editor UI actually round-trips. When the editor
# grows a UI for another section (e.g. `animation`), add it here so deleting
# the section in the editor deletes it from the file.
_EDITOR_MANAGED_KEYS = frozenset({"data", "chart"})


def _deep_replace(
    target: MutableMapping[str, Any],
    source: Mapping[str, Any],
    protected_keys: frozenset[str] | set[str] = frozenset(),
) -> None:
    """Recursively replace mapping content to mirror source exactly.

    ``protected_keys`` exempts top-level keys from deletion when they are absent
    from ``source`` (used to preserve editor-unmanaged blocks like ``animation``).
    It applies only to this call's deletion pass; nested recursion mirrors its
    source exactly, so fields removed inside ``data``/``chart`` are still dropped.
    """
    for key in list(target.keys()):
        if key not in source and key not in protected_keys:
            del target[key]

    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, MutableMapping) and isinstance(value, Mapping):
            _deep_replace(existing, value)
        elif key not in target or _values_differ(existing, value):
            # Skip assignment when the value is unchanged: reassigning replaces
            # ruamel nodes, which rewraps long strings, converts flow lists to
            # block style, and re-types scalars (12 -> 12.0) even for keys the
            # user never touched.
            target[key] = value


def _values_differ(existing: Any, value: Any) -> bool:
    """True when a save must overwrite ``existing`` with ``value``.

    Plain ``!=`` is almost right (ruamel scalar/sequence nodes subclass their
    builtin types), but Python's ``True == 1`` would treat a bool/int swap as
    equal and silently keep the wrong YAML type.
    """
    if isinstance(existing, bool) is not isinstance(value, bool):
        return True
    try:
        return bool(existing != value)
    except Exception:
        return True


def _clean_form_data(config: dict[str, Any]) -> dict[str, Any]:
    """Remove empty values the editor form emits for unset fields.

    The custom SchemaForm sends empty strings, empty arrays, and empty
    objects for fields that have no user-supplied value. The chart pipeline
    expects these to be absent (Pydantic defaults them to None).

    Also recovers ``datetime.date`` objects from ISO date strings.
    YAML auto-parses ``1958-01-01`` as ``datetime.date``, but the
    JSON round-trip through the frontend converts them to strings.
    Matplotlib needs real date objects for axis limits.
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
        elif isinstance(value, list):
            cleaned[key] = [_coerce_date(v) if isinstance(v, str) else v for v in value]
        else:
            cleaned[key] = value
    return cleaned


# Matches exactly YYYY-MM-DD (ISO 8601 date, no time component).
_ISO_DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def _coerce_date(value: str) -> str | date:
    """Convert an ISO date string to ``datetime.date`` if it matches.

    YAML auto-parses unquoted ``2024-01-15`` as a date object. After a
    JSON round-trip through the editor frontend, these become strings.
    This function recovers the original date type so matplotlib axis
    limits and other date-sensitive code works correctly.
    """
    if _ISO_DATE_RE.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return value


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
