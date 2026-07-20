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
from typing import Any, NamedTuple

import matplotlib.pyplot as plt
import pandas as pd

try:
    from ruamel.yaml import YAML
except ImportError:
    YAML = None

import yaml

from tpsplots.exceptions import TPSPlotsError
from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.models.data_sources import DataSourceConfig
from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.render_pipeline import build_render_context
from tpsplots.processors.resolvers import DataResolver
from tpsplots.views import VIEW_REGISTRY

logger = logging.getLogger(__name__)


class SaveConflict(Exception):
    """Raised when a save target changed on disk since it was loaded.

    The editor records each loaded file's mtime; if the file is newer on disk
    at save time (someone edited it out-of-band), the save is refused unless
    forced, so concurrent edits are not silently clobbered.
    """


class SaveValidationError(ValueError):
    """Raised when a save is blocked because the config fails validation.

    Subclasses ``ValueError`` (so existing ``except ValueError`` save guards
    still catch it) but also carries the structured ``errors`` list so the API
    can return field-level messages to the client.
    """

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors: list[dict[str, Any]] = errors or []


class _EditorDumper(yaml.SafeDumper):
    """SafeDumper that spells embedded newlines as ``\\n`` in double quotes.

    Chart text uses real newlines for line breaks (``"Enacted\\n(2025 $)"``).
    PyYAML's default is a single-quoted scalar with a blank line, which is
    valid but unreadable and unlike the hand-written files in ``yaml/`` — and
    ruamel already emits the double-quoted form on the round-trip save path.
    """


def _represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    style = '"' if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_EditorDumper.add_representer(str, _represent_str)


def _dump_plain(config: dict[str, Any], stream: Any = None) -> str:
    """Dump a config with the editor's plain-YAML options.

    The YAML drawer promises to show byte-for-byte what a save would write, so
    both paths must use identical dump options — hence one function rather than
    two copies of the keyword list.
    """
    return yaml.dump(
        config,
        stream,
        Dumper=_EditorDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


class ResolvedTemplates(NamedTuple):
    """Result of ``_resolve_chart_templates``: config plus stage-specific errors."""

    config: dict[str, Any]
    data_error: Exception | None = None
    template_error: TPSPlotsError | None = None


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
        # mtime (ns) of each file at load time, keyed by relative path, so a
        # save can detect the file was changed on disk since it was loaded.
        self._loaded_mtimes: dict[str, int] = {}
        # Open-menu listing entries keyed by relative path, each paired with the
        # mtime (ns) they were parsed from: {rel: (mtime_ns, entry)}.
        self._file_meta_cache: dict[str, tuple[int | None, dict[str, Any]]] = {}

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
        resolved, data_error, template_error = self._resolve_chart_templates(config)
        if data_error is not None:
            # A config full of unresolved {{refs}} whose data source is broken
            # would otherwise pass Pydantic validation (the refs are valid
            # strings). Surface the real data error so validation fails.
            errors.append({"path": "/data/source", "message": str(data_error)})
        if template_error is not None:
            # A typo'd {{ref}} against a working data source. Surface the
            # resolver's message (it lists "Available keys: [...]") verbatim as
            # a structured /chart error rather than escaping as a 500.
            errors.append({"path": "/chart", "message": str(template_error)})
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

    def _resolve_chart_templates(self, config: dict[str, Any]) -> ResolvedTemplates:
        """Resolve {{...}} refs in the chart section before validation.

        Uses the editor's cached data resolution.  ``data_error`` is the
        exception raised while loading the data source and ``template_error`` is
        raised while resolving the ``{{refs}}`` themselves (e.g. a typo'd key).
        Both are ``None`` on success / when there is nothing to resolve.

        The original config is returned unchanged (with the relevant error set)
        when either stage fails, so ``validate_config`` can surface the real
        error while ``render_preview`` / ``preflight`` re-encounter or re-raise
        the same failure downstream, keeping their behavior unchanged.

        The resolve call is wrapped: a typo'd ``{{ref}}`` raises
        ``ConfigurationError`` (a ``TPSPlotsError``) even when the data source
        loads fine. Returning it here instead of letting it propagate keeps
        ``/api/validate`` and ``/api/preflight`` from turning it into a 500.
        """
        from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver

        data_section = config.get("data")
        chart_section = config.get("chart")

        if not data_section or not chart_section:
            return ResolvedTemplates(config)

        if not ReferenceResolver.contains_references(chart_section):
            return ResolvedTemplates(config)

        try:
            data = self._resolve_data(data_section)
        except Exception as exc:
            return ResolvedTemplates(config, data_error=exc)

        try:
            resolved_chart = ReferenceResolver.resolve(dict(chart_section), data)
        except TPSPlotsError as exc:
            return ResolvedTemplates(config, template_error=exc)
        return ResolvedTemplates({**config, "chart": resolved_chart})

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
                resolved = self._resolve_chart_templates(cleaned).config
                validated = YAMLChartConfig(**resolved)
                data = self._resolve_data(cleaned["data"])
                build_render_context(validated, data, log_conflicts=False)
            except Exception as exc:
                blocking_errors.append({"path": "/chart", "message": str(exc)})

        # (a) A fresh editor with no data source yet emits a spurious
        # "/data: Field required" from Pydantic (the empty data section was
        # dropped by _clean_form_data). The missing source is already reported
        # via missing_paths, so drop that whole-section blocking error and let
        # the editor guide the user to pick a source instead.
        if not source:
            blocking_errors = [e for e in blocking_errors if e["path"] != "/data"]

        # validate_config and profile_data can both report the same broken
        # data source; collapse duplicates (keeping first position) via dict keying.
        blocking_errors = list(
            {(err["path"], err["message"]): err for err in blocking_errors}.values()
        )

        missing_paths = sorted(set(missing_paths))
        ready = len(blocking_errors) == 0 and len(missing_paths) == 0

        # Honest binding-step status: "not_started" until there is a working
        # data source or at least one binding value; "complete" only when every
        # required binding is set AND the data source actually loads (a broken
        # source must never read as complete); otherwise "error".
        required_bindings = [f for f in primary_bindings if f not in OPTIONAL_BINDING_FIELDS]
        any_binding_value = any(
            chart_cfg.get(f) not in (None, "", [], {}) for f in primary_bindings
        )
        all_required_bound = bool(required_bindings) and all(
            f"/chart/{f}" not in missing_paths for f in required_bindings
        )
        if not primary_bindings:
            data_bindings_status = "not_started"
        elif all_required_bound and data_ready:
            data_bindings_status = "complete"
        elif not data_ready and not any_binding_value:
            data_bindings_status = "not_started"
        else:
            data_bindings_status = "error"

        step_status = {
            "data_source_and_preparation": (
                "complete" if data_ready else ("error" if source else "not_started")
            ),
            "data_bindings": data_bindings_status,
            "visual_design": "in_progress" if source else "not_started",
            "annotation_output": "in_progress" if source else "not_started",
        }

        # Section badge counts are deliberately NOT computed here: the frontend
        # already receives blocking_errors + missing_paths (with paths) and the
        # step field map in editor_hints, so it can bucket per-section counts
        # itself without a second server-side copy of the field taxonomy.
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
            device: ``"desktop"``, ``"mobile"``, or ``"social"``.

        Returns:
            PNG image bytes.
        """
        # Keep this strict: create_figure silently falls back to DESKTOP for
        # unknown device names, which would mask typos as wrong-looking charts.
        if device not in {"desktop", "mobile", "social"}:
            raise ValueError(f"Unsupported device: {device}")

        # Drop empty values (empty strings, empty arrays, etc.) the editor form
        # emits for unset fields, so the pipeline sees them as absent.
        config = _clean_form_data(config)

        # Resolve {{...}} template refs, then validate
        resolution = self._resolve_chart_templates(config)
        if resolution.template_error is not None:
            # A typo'd {{ref}} — raise as ValueError so the route returns 400
            # with the resolver's message instead of a 500.
            raise ValueError(str(resolution.template_error))
        config = resolution.config
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
        params = deepcopy(ctx.resolved_params)
        # Previews are always rendered at 150 dpi for speed; a config's own `dpi`
        # applies only on `generate`. Pop it so an explicit dpi can't collide
        # with the dpi=150 kwarg below (duplicate-kwarg TypeError).
        params.pop("dpi", None)
        fig = view.create_figure(
            metadata=ctx.resolved_metadata,
            device=device,
            dpi=150,
            **params,
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

        # Record the on-disk mtime so a later save can detect out-of-band edits.
        self._record_mtime(relative_path, path)
        return data

    def save_yaml(
        self,
        relative_path: str,
        config: dict[str, Any],
        *,
        override_conflict: bool = False,
        override_validation: bool = False,
    ) -> None:
        """Save config to YAML, preserving comments for existing files.

        Uses ruamel.yaml round-trip editing when available and the file
        already exists. Falls back to plain yaml.dump for new files.

        The two overrides are separable intents matching the API's two 409
        kinds: overriding a disk conflict must not also disable validation.

        Args:
            override_conflict: Skip the changed-on-disk check (deliberately
                overwrite a file edited out-of-band since load).
            override_validation: Skip config validation ("save anyway") — the
                cleaned raw config is dumped regardless. Cleaning still runs.

        Raises:
            ValueError: Invalid path/suffix (plain ``ValueError``).
            SaveValidationError: Config failed validation (unless overridden).
            SaveConflict: File changed on disk since load (unless overridden).
        """
        # Path/suffix errors first, independent of overrides — always plain ValueError.
        path = self._resolve_path(relative_path)
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError(f"Not a YAML file: {relative_path}")

        # Conflict check: refuse to clobber a file edited on disk since we
        # loaded it, unless the caller explicitly overrides.
        if not override_conflict and path.exists() and relative_path in self._loaded_mtimes:
            current_mtime = _safe_mtime_ns(path)
            if current_mtime is not None and current_mtime > self._loaded_mtimes[relative_path]:
                raise SaveConflict(f"File changed on disk since it was loaded: {relative_path}")

        # Cleaning always runs; validation gates each output path exactly once
        # (the round-trip branch validates the *merged* document, a superset of
        # this payload, so a payload-level pre-check would be redundant).
        config = _clean_form_data(config)

        if path.exists() and YAML is not None:
            self._save_roundtrip(path, config, validate=not override_validation)
        else:
            if not override_validation:
                self._validate_or_raise(config, "Configuration validation failed")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                _dump_plain(config, f)

        # Record the freshly written mtime as the new baseline so a subsequent
        # save from this session does not falsely trip the conflict check.
        self._record_mtime(relative_path, path)

    def _record_mtime(self, relative_path: str, path: Path) -> None:
        """Store the file's current mtime as the conflict-check baseline."""
        mtime = _safe_mtime_ns(path)
        if mtime is not None:
            self._loaded_mtimes[relative_path] = mtime

    @staticmethod
    def _build_roundtrip_yaml() -> Any:
        """ruamel instance with the editor's churn-minimizing dump settings.

        ruamel re-emits every line through its serializer, so these settings
        decide churn on untouched keys: without a large width it re-wraps any
        line over 80 chars, and the indent must match the dominant hand-written
        style in yaml/ (indented dashes) or every block sequence re-indents.
        """
        rt = YAML(typ="rt")
        rt.preserve_quotes = True
        rt.width = 100_000
        rt.indent(mapping=2, sequence=4, offset=2)
        return rt

    def _merge_into_existing(self, path: Path, config: dict[str, Any]) -> tuple[Any, Any]:
        """Load an existing file and merge the payload into it (no write).

        Shared by the save path and the YAML-preview pane so the pane shows
        exactly what a save would write, comments and protected keys included.
        """
        rt = self._build_roundtrip_yaml()
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
        config = _graft_protected_chart_keys(existing, config)
        _deep_replace(existing, config, protected_keys=protected_keys)
        return rt, existing

    def _save_roundtrip(self, path: Path, config: dict[str, Any], validate: bool = True) -> None:
        """Merge changed fields into existing YAML preserving comments."""
        rt, existing = self._merge_into_existing(path, config)

        # The graft can preserve keys the payload's chart type does not allow
        # (and hand-edits since load can too), so gate on the merged document
        # — never write a file the CLI would reject. Skipped on force saves.
        if validate:
            self._validate_or_raise(
                _to_plain(existing), "Save aborted — merged file would be invalid"
            )

        with path.open("w", encoding="utf-8") as f:
            rt.dump(existing, f)

    def render_save_output(self, config: dict[str, Any], relative_path: str | None = None) -> str:
        """Render the YAML a save would write, without writing anything.

        Backs the editor's YAML pane. With a ``relative_path`` to an existing
        file, the output is the comment-preserving ruamel merge — byte-for-byte
        what ``save_yaml`` would produce. Without one (never-saved config), a
        plain dump of the cleaned config. Never validates: the pane must show
        work-in-progress configs too.
        """
        cleaned = _clean_form_data(config)

        if relative_path:
            path = self._resolve_path(relative_path)
            if path.exists() and YAML is not None:
                rt, existing = self._merge_into_existing(path, cleaned)
                buf = io.StringIO()
                rt.dump(existing, buf)
                return buf.getvalue()

        return _dump_plain(cleaned)

    def _validate_or_raise(self, config: dict[str, Any], prefix: str) -> None:
        """Validate a config (with {{refs}} resolved when data loads) or raise.

        Validation is a *gate only*: the saved payload is always the cleaned
        raw input dict, never a ``model_dump`` of the validated model. Dumping
        the model would materialize every non-None default into the file (and
        make save-anyway impossible for invalid configs), whereas the raw dict
        keeps saved YAML minimal and faithful to what the user actually set.

        On data-load failure the unresolved config is validated instead — the
        refs are valid strings, so offline sources stay saveable. Raises
        ``SaveValidationError`` carrying the structured error list so the API
        can surface field-level messages.
        """
        resolved = self._resolve_chart_templates(config).config
        try:
            YAMLChartConfig(**resolved)
        except Exception as exc:
            raise SaveValidationError(
                f"{prefix}: {_format_pydantic_errors(exc)}",
                errors=_extract_pydantic_errors(exc),
            ) from exc

    def list_yaml_files(self) -> list[dict[str, Any]]:
        """List YAML files in yaml_dir recursively, enriched with chart metadata.

        Each entry is ``{"path": <relative path>, "type": <chart type or None>,
        "title": <chart title or None>}``. The chart type/title are read with a
        lightweight ``yaml.safe_load`` cached per file mtime, so repeated Open-menu
        listings do not re-parse unchanged files. Unreadable or malformed files are
        tolerated: they list with ``type``/``title`` of ``None`` rather than
        failing the whole listing.
        """
        cache = self._file_meta_cache

        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ext in ("*.yaml", "*.yml"):
            for path in self._root.rglob(ext):
                rel = str(path.relative_to(self._root))
                if rel in seen:
                    continue
                seen.add(rel)

                mtime = _safe_mtime_ns(path)
                cached = cache.get(rel)
                if cached is not None and cached[0] == mtime:
                    entries.append(cached[1])
                    continue

                chart_type: str | None = None
                title: str | None = None
                try:
                    with path.open(encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and isinstance(data.get("chart"), dict):
                        chart = data["chart"]
                        raw_type = chart.get("type")
                        chart_type = str(raw_type) if raw_type is not None else None
                        raw_title = chart.get("title")
                        title = str(raw_title) if raw_title is not None else None
                except Exception:
                    # Malformed / unreadable file: list it with null metadata.
                    chart_type = None
                    title = None

                entry = {"path": rel, "type": chart_type, "title": title}
                cache[rel] = (mtime, entry)
                entries.append(entry)

        entries.sort(key=lambda e: e["path"])
        return entries

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


def _safe_mtime_ns(path: Path) -> int | None:
    """Return the file's mtime in nanoseconds, or ``None`` when unreadable."""
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _graft_protected_chart_keys(
    existing: Mapping[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Copy protected chart-section nodes from the file into the save payload.

    The editor strips base excluded fields (``annotations``, ``figsize``,
    ``matplotlib_config``, ...) from its schema, so its payload never carries
    them — mirroring the payload would delete hand-authored blocks from disk.
    Grafting the existing ruamel nodes into the payload preserves them (the
    equality skip in ``_deep_replace`` then leaves the original nodes, and
    their comments, untouched). Keys are filtered to the payload type's model
    fields so a type switch never smuggles a field into a type that forbids it.
    """
    from tpsplots.editor.ui_schema import get_protected_chart_keys

    existing_chart = existing.get("chart")
    payload_chart = config.get("chart")
    if not isinstance(existing_chart, Mapping) or not isinstance(payload_chart, Mapping):
        return config

    chart_type = str(payload_chart.get("type", ""))
    grafted = dict(payload_chart)
    for key in get_protected_chart_keys(chart_type):
        if key in existing_chart and key not in grafted:
            grafted[key] = existing_chart[key]
    return {**config, "chart": grafted}


def _to_plain(obj: Any) -> Any:
    """Convert ruamel containers to plain dicts/lists for validation."""
    if isinstance(obj, Mapping):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


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
            # Only ISO-date-coerce list items for axis-range fields. Coercing
            # every list would rewrite literal date-like strings elsewhere
            # (e.g. labels: ["2026-01-01"], bar categories) into date objects.
            if key in _DATE_COERCED_FIELDS:
                cleaned[key] = [_coerce_date(v) if isinstance(v, str) else v for v in value]
            else:
                cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


# Fields whose list items may be real ISO dates the frontend stringified back.
# Restricted to axis-range/tick fields — field names are unique across the
# schema, so a plain key check works at any nesting depth.
_DATE_COERCED_FIELDS = frozenset({"xlim", "ylim", "xticks"})


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


def _format_pydantic_errors(exc: Exception) -> str:
    """Render extracted validation errors as one ``path: message; ...`` string."""
    return "; ".join(
        f"{err['path']}: {err['message']}" if err["path"] else err["message"]
        for err in _extract_pydantic_errors(exc)
    )


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
