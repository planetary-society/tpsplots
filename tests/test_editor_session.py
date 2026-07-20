"""Tests for EditorSession: validation, path security, file I/O."""

import pytest
import yaml

from tests.conftest import bump_mtime
from tpsplots.editor.session import EditorSession


@pytest.fixture
def yaml_dir(tmp_path):
    """Create a temp directory with sample YAML files."""
    sample = {
        "data": {"source": "data/test.csv"},
        "chart": {"type": "bar", "output": "test_chart", "title": "Test Chart"},
    }
    (tmp_path / "sample.yaml").write_text(
        yaml.dump(sample, default_flow_style=False), encoding="utf-8"
    )
    (tmp_path / "another.yml").write_text(
        yaml.dump(sample, default_flow_style=False), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def session(yaml_dir):
    return EditorSession(yaml_dir=yaml_dir)


class TestPathSecurity:
    """Path traversal protection tests."""

    def test_reject_absolute_path(self, session):
        with pytest.raises(ValueError, match="Absolute paths"):
            session._resolve_path("/etc/passwd")

    def test_reject_traversal(self, session):
        with pytest.raises(ValueError):
            session._resolve_path("../../../etc/passwd")

    def test_reject_dot_dot(self, session):
        with pytest.raises(ValueError):
            session._resolve_path("subdir/../../secrets.yaml")

    def test_allow_valid_relative_path(self, session, yaml_dir):
        path = session._resolve_path("sample.yaml")
        assert path == yaml_dir / "sample.yaml"

    def test_resolve_uses_real_path(self, session, yaml_dir):
        """Ensure symlinks are resolved (no symlink escape)."""
        path = session._resolve_path("sample.yaml")
        assert path.is_absolute()
        assert path.resolve() == path


class TestValidation:
    def test_valid_config_returns_no_errors(self, session):
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test", "title": "Test"},
        }
        errors = session.validate_config(config)
        assert errors == []

    def test_invalid_config_returns_errors(self, session):
        config = {"data": {"source": "test.csv"}, "chart": {"type": "bar"}}
        errors = session.validate_config(config)
        assert len(errors) > 0

    def test_missing_data_key_returns_errors(self, session):
        config = {"chart": {"type": "bar", "output": "test", "title": "Test"}}
        errors = session.validate_config(config)
        assert len(errors) > 0

    def test_errors_use_json_pointer_paths(self, session):
        config = {"data": {"source": "test.csv"}, "chart": {"type": "bar"}}
        errors = session.validate_config(config)
        paths = {err["path"] for err in errors}
        assert "/chart/output" in paths
        assert "/chart/title" in paths

    def test_broken_data_source_with_refs_fails_validation(self, session):
        """A config full of {{refs}} whose data source is missing must fail
        validation and surface the real data error (not false-pass)."""
        config = {
            "data": {"source": "csv:/definitely/missing/does_not_exist_xyz.csv"},
            "chart": {
                "type": "line",
                "output": "broken",
                "title": "Broken",
                "x": "{{Year}}",
                "y": "{{Value}}",
            },
        }
        errors = session.validate_config(config)
        assert errors, "expected validation to fail for a broken data source"
        data_errors = [e for e in errors if e["path"] == "/data/source"]
        assert data_errors, f"expected a /data/source error, got: {errors}"
        assert "does_not_exist_xyz.csv" in data_errors[0]["message"]

    def test_typo_ref_with_working_source_validates_not_raises(self, session):
        """A typo'd {{ref}} against a WORKING data source must return a
        structured /chart error (with the resolver's 'Available keys' hint),
        not escape as a 500."""
        config = {
            "data": {"source": "csv:yaml/examples/data/nasa_authorizations.csv"},
            "chart": {
                "type": "line",
                "output": "typo",
                "title": "Typo",
                "x": "{{Year}}",
                "y": "{{Budgett}}",
            },
        }
        errors = session.validate_config(config)
        chart_errors = [e for e in errors if e["path"] == "/chart"]
        assert chart_errors, f"expected a /chart template error, got: {errors}"
        assert "Available keys" in chart_errors[0]["message"]

    def test_typo_ref_preflight_reports_available_keys(self, session):
        """Preflight surfaces the typo'd ref as a blocking error carrying the
        resolver's 'Available keys' hint instead of 500ing."""
        config = {
            "data": {"source": "csv:yaml/examples/data/nasa_authorizations.csv"},
            "chart": {
                "type": "line",
                "output": "typo",
                "title": "Typo",
                "x": "{{Year}}",
                "y": "{{Budgett}}",
            },
        }
        result = session.preflight(config)
        assert result["ready_for_preview"] is False
        blocking = result["blocking_errors"]
        assert any("Available keys" in e["message"] for e in blocking), blocking


class TestFileIO:
    def test_load_yaml(self, session):
        config = session.load_yaml("sample.yaml")
        assert config["chart"]["type"] == "bar"
        assert config["chart"]["title"] == "Test Chart"

    def test_load_nonexistent_raises(self, session):
        with pytest.raises(FileNotFoundError):
            session.load_yaml("nonexistent.yaml")

    def test_load_non_yaml_raises(self, session, yaml_dir):
        (yaml_dir / "readme.txt").write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError, match="Not a YAML file"):
            session.load_yaml("readme.txt")

    def test_save_yaml_new_file(self, session, yaml_dir):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "donut", "output": "new_chart", "title": "New"},
        }
        session.save_yaml("new.yaml", config)
        assert (yaml_dir / "new.yaml").exists()

        loaded = yaml.safe_load((yaml_dir / "new.yaml").read_text(encoding="utf-8"))
        assert loaded["chart"]["type"] == "donut"

    def test_save_yaml_updates_existing(self, session, yaml_dir):
        config = {
            "data": {"source": "data/updated.csv"},
            "chart": {"type": "bar", "output": "updated", "title": "Updated"},
        }
        session.save_yaml("sample.yaml", config)

        loaded = yaml.safe_load((yaml_dir / "sample.yaml").read_text(encoding="utf-8"))
        assert loaded["chart"]["title"] == "Updated"

    def test_save_yaml_rejects_invalid_config(self, session, yaml_dir):
        config = {"data": {"source": "data/updated.csv"}, "chart": {"type": "bar"}}
        with pytest.raises(ValueError):
            session.save_yaml("invalid.yaml", config)
        assert not (yaml_dir / "invalid.yaml").exists()

    def test_save_yaml_strips_empty_form_values(self, session, yaml_dir):
        config = {
            "data": {"source": "data/updated.csv"},
            "chart": {
                "type": "bar",
                "output": "updated",
                "title": "Updated",
                "subtitle": "",
                "figsize": [],
            },
        }
        session.save_yaml("cleaned.yaml", config)
        loaded = yaml.safe_load((yaml_dir / "cleaned.yaml").read_text(encoding="utf-8"))
        assert "subtitle" not in loaded["chart"]
        assert "figsize" not in loaded["chart"]

    def test_save_yaml_roundtrip_removes_deleted_fields(self, session, yaml_dir):
        (yaml_dir / "with_subtitle.yaml").write_text(
            yaml.dump(
                {
                    "data": {"source": "data/test.csv"},
                    "chart": {
                        "type": "bar",
                        "output": "keep_output",
                        "title": "Keep Title",
                        "subtitle": "remove me",
                    },
                },
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        session.save_yaml(
            "with_subtitle.yaml",
            {
                "data": {"source": "data/test.csv"},
                "chart": {"type": "bar", "output": "keep_output", "title": "Keep Title"},
            },
        )
        loaded = yaml.safe_load((yaml_dir / "with_subtitle.yaml").read_text(encoding="utf-8"))
        assert "subtitle" not in loaded["chart"]

    def test_save_preserves_unmanaged_animation_block(self, session, yaml_dir):
        """Regression: the editor manages only data/chart, but saving must not
        delete a top-level `animation:` block it does not surface."""
        yaml_dir_file = yaml_dir / "animated.yaml"
        yaml_dir_file.write_text(
            yaml.dump(
                {
                    "data": {"source": "data/test.csv"},
                    "chart": {
                        "type": "bar",
                        "output": "animated",
                        "title": "Animated",
                        "subtitle": "keep me too",
                    },
                    "animation": {"fps": 30, "formats": ["square", "landscape"]},
                },
                default_flow_style=False,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        # Editor-managed state carries data + chart only (no animation), as the
        # editor UI does not surface the animation block.
        session.save_yaml(
            "animated.yaml",
            {
                "data": {"source": "data/test.csv"},
                "chart": {"type": "bar", "output": "animated", "title": "Animated"},
            },
        )

        loaded = yaml.safe_load(yaml_dir_file.read_text(encoding="utf-8"))
        # The unmanaged animation block survived intact.
        assert loaded["animation"] == {"fps": 30, "formats": ["square", "landscape"]}
        # Managed edits still applied: subtitle removed from chart.
        assert "subtitle" not in loaded["chart"]

    def test_list_yaml_files(self, session):
        files = session.list_yaml_files()
        paths = {f["path"] for f in files}
        assert "sample.yaml" in paths
        assert "another.yml" in paths
        assert len(files) == 2
        # Enriched with chart metadata from the file's chart block.
        sample = next(f for f in files if f["path"] == "sample.yaml")
        assert sample["type"] == "bar"
        assert sample["title"] == "Test Chart"

    def test_list_yaml_files_includes_nested_paths(self, session, yaml_dir):
        nested = yaml_dir / "nested"
        nested.mkdir()
        (nested / "child.yaml").write_text("chart: {}\n", encoding="utf-8")
        files = session.list_yaml_files()
        paths = {f["path"] for f in files}
        assert "nested/child.yaml" in paths

    def test_list_yaml_files_tolerates_unreadable(self, session, yaml_dir):
        """A malformed YAML file still lists, with null type/title."""
        (yaml_dir / "broken.yaml").write_text("chart: [unclosed", encoding="utf-8")
        files = session.list_yaml_files()
        broken = next(f for f in files if f["path"] == "broken.yaml")
        assert broken["type"] is None
        assert broken["title"] is None

    def test_list_yaml_files_caches_by_mtime(self, session, yaml_dir):
        """The metadata read is cached per mtime and refreshed when it changes."""
        first = {f["path"]: f for f in session.list_yaml_files()}
        assert first["sample.yaml"]["title"] == "Test Chart"

        (yaml_dir / "sample.yaml").write_text(
            yaml.dump(
                {
                    "data": {"source": "data/test.csv"},
                    "chart": {"type": "line", "output": "o", "title": "Renamed"},
                },
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        bump_mtime(yaml_dir / "sample.yaml")

        second = {f["path"]: f for f in session.list_yaml_files()}
        assert second["sample.yaml"]["type"] == "line"
        assert second["sample.yaml"]["title"] == "Renamed"


class TestSaveContract:
    """mtime conflict detection, force bypass, and structured validation errors."""

    def test_save_conflict_after_external_edit(self, session, yaml_dir):
        from tpsplots.editor.session import SaveConflict

        session.load_yaml("sample.yaml")
        sample = yaml_dir / "sample.yaml"
        bump_mtime(sample)

        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "Conflicting"},
        }
        with pytest.raises(SaveConflict):
            session.save_yaml("sample.yaml", config)

    def test_overrides_bypass_conflict_and_validation(self, session, yaml_dir):
        session.load_yaml("sample.yaml")
        sample = yaml_dir / "sample.yaml"
        bump_mtime(sample)

        # Invalid (missing output/title) AND file changed on disk — both
        # overrides together write anyway.
        config = {"data": {"source": "data/test.csv"}, "chart": {"type": "bar"}}
        session.save_yaml("sample.yaml", config, override_conflict=True, override_validation=True)
        assert sample.exists()

    def test_overrides_are_separable(self, session, yaml_dir):
        """Overriding the conflict must not also disable validation."""
        from tpsplots.editor.session import SaveValidationError

        session.load_yaml("sample.yaml")
        sample = yaml_dir / "sample.yaml"
        bump_mtime(sample)

        invalid = {"data": {"source": "data/test.csv"}, "chart": {"type": "bar"}}
        with pytest.raises(SaveValidationError):
            session.save_yaml("sample.yaml", invalid, override_conflict=True)

    def test_save_after_own_write_does_not_conflict(self, session, yaml_dir):
        """A save updates the recorded mtime, so an immediate re-save is fine."""
        session.load_yaml("sample.yaml")
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "First"},
        }
        session.save_yaml("sample.yaml", config)
        config["chart"]["title"] = "Second"
        session.save_yaml("sample.yaml", config)  # must not raise SaveConflict
        loaded = yaml.safe_load((yaml_dir / "sample.yaml").read_text(encoding="utf-8"))
        assert loaded["chart"]["title"] == "Second"

    def test_save_validation_error_carries_structured_errors(self, session):
        from tpsplots.editor.session import SaveValidationError

        config = {"data": {"source": "data/test.csv"}, "chart": {"type": "bar"}}
        with pytest.raises(SaveValidationError) as excinfo:
            session.save_yaml("invalid.yaml", config)
        assert excinfo.value.errors, "SaveValidationError must carry structured errors"

    def test_unloaded_file_save_skips_conflict_check(self, session, yaml_dir):
        """A file never loaded this session has no recorded mtime — no conflict."""
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "brand_new", "title": "New"},
        }
        session.save_yaml("brand_new.yaml", config)
        assert (yaml_dir / "brand_new.yaml").exists()


class TestDataCache:
    def test_invalidate_cache(self, session):
        session._data_cache["test_key"] = {"some": "data"}
        assert len(session._data_cache) == 1
        session.invalidate_data_cache()
        assert len(session._data_cache) == 0

    def test_invalidate_clears_profile_cache(self, session):
        session._profile_cache["test_key"] = {"some": "profile"}
        session.invalidate_data_cache()
        assert len(session._profile_cache) == 0

    def test_cache_key_mixes_local_file_mtime(self, session, yaml_dir):
        csv_path = yaml_dir / "keyed.csv"
        csv_path.write_text("Year,Value\n2024,10\n", encoding="utf-8")
        config = {"source": f"csv:{csv_path}"}

        key_before = session._data_cache_key(config)
        assert session._hash_payload(config) in key_before
        assert key_before != session._hash_payload(config)  # mtime suffix present

        bump_mtime(csv_path)
        assert session._data_cache_key(config) != key_before

    def test_cache_key_unchanged_for_non_file_sources(self, session):
        # URLs and controllers have no mtime — key is the plain payload hash.
        for source in ("https://example.com/data.csv", "nasa_budget_chart.nasa_budget_by_year"):
            config = {"source": source}
            assert session._data_cache_key(config) == session._hash_payload(config)

    def test_profile_picks_up_local_file_mtime_change(self, session, yaml_dir):
        csv_path = yaml_dir / "mtime.csv"
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")
        config = {"source": f"csv:{csv_path}"}

        first = session.profile_data(config)
        assert first["row_count"] == 2

        # Modify the underlying file; force a strictly newer mtime so the cache
        # key changes even on filesystems with coarse mtime resolution.
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n2026,30\n", encoding="utf-8")
        bump_mtime(csv_path)

        second = session.profile_data(config)
        assert second["row_count"] == 3


class TestCleanFormData:
    """Verify editor-form empty-value cleanup."""

    def test_strips_empty_strings(self):
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"title": "Keep", "subtitle": "", "source": ""})
        assert result == {"title": "Keep"}

    def test_strips_empty_arrays(self):
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"figsize": [], "y": ["col1"], "title": "X"})
        assert result == {"y": ["col1"], "title": "X"}

    def test_preserves_false_booleans(self):
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"grid": False, "legend": True})
        assert result == {"grid": False, "legend": True}

    def test_preserves_zero_values(self):
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"tick_rotation": 0, "linewidth": 0.0})
        assert result == {"tick_rotation": 0, "linewidth": 0.0}

    def test_recurses_into_nested_dicts(self):
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data(
            {"data": {"source": "test.csv", "extra": ""}, "chart": {"type": "bar"}}
        )
        assert result == {"data": {"source": "test.csv"}, "chart": {"type": "bar"}}

    def test_coerces_iso_date_strings_in_lists(self):
        """Date strings in lists (e.g. xlim) are converted to datetime.date."""
        from datetime import date

        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"xlim": ["1958-01-01", "2030-01-01"]})
        assert result == {"xlim": [date(1958, 1, 1), date(2030, 1, 1)]}

    def test_leaves_non_date_strings_in_lists(self):
        """Regular strings in lists are not converted."""
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"labels": ["Series A", "Series B"]})
        assert result == {"labels": ["Series A", "Series B"]}

    def test_date_coercion_restricted_to_allowlist(self):
        """Only allowlisted fields (xlim/ylim/xticks) coerce ISO dates. A
        literal date-like string in labels must round-trip as a str, while
        xlim items still become datetime.date."""
        from datetime import date

        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data(
            {
                "labels": ["2026-01-01", "2027-01-01"],
                "xlim": ["1958-01-01", "2030-01-01"],
            }
        )
        # labels: literal strings, untouched
        assert result["labels"] == ["2026-01-01", "2027-01-01"]
        assert all(isinstance(v, str) for v in result["labels"])
        # xlim: real axis dates, coerced
        assert result["xlim"] == [date(1958, 1, 1), date(2030, 1, 1)]
        assert all(isinstance(v, date) for v in result["xlim"])

    def test_leaves_partial_date_strings_as_strings(self):
        """Strings that look date-like but aren't exact YYYY-MM-DD stay as strings."""
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"colors": ["2024-01-01T00:00", "not-a-date"]})
        assert result == {"colors": ["2024-01-01T00:00", "not-a-date"]}

    def test_preserves_legend_dict(self):
        """Legend dict values survive clean_form_data unchanged (original bug scenario)."""
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"legend": {"loc": "upper right", "fontsize": "medium"}})
        assert result == {"legend": {"loc": "upper right", "fontsize": "medium"}}

    def test_preserves_legend_false(self):
        """Legend=False (disable legend) survives clean_form_data."""
        from tpsplots.editor.session import _clean_form_data

        result = _clean_form_data({"legend": False})
        assert result == {"legend": False}


class TestPreflight:
    """Honest preflight states + section issue counts."""

    def test_fresh_empty_editor_has_no_blocking_errors(self, session):
        """(a) No source yet: the spurious '/data: Field required' is filtered;
        the missing source is reported only via missing_paths."""
        config = {
            "data": {"source": ""},
            "chart": {"type": "line", "output": "chart", "title": "T"},
        }
        result = session.preflight(config)
        assert result["blocking_errors"] == []
        assert "/data/source" in result["missing_paths"]
        assert result["step_status"]["data_source_and_preparation"] == "not_started"

    def test_data_bindings_not_started_when_nothing_bound(self, session):
        """(b) data_bindings is 'not_started' (not 'error') before there is a
        working data source or any binding value."""
        config = {
            "data": {"source": ""},
            "chart": {"type": "line", "output": "chart", "title": "T"},
        }
        result = session.preflight(config)
        assert result["step_status"]["data_bindings"] == "not_started"

    def test_data_bindings_not_complete_when_source_broken(self, session):
        """(c) Even with every binding set, a broken data source must not read
        as complete."""
        config = {
            "data": {"source": "csv:/definitely/missing/does_not_exist_abc.csv"},
            "chart": {
                "type": "line",
                "output": "chart",
                "title": "T",
                "x": "{{Year}}",
                "y": "{{Value}}",
            },
        }
        result = session.preflight(config)
        assert result["step_status"]["data_bindings"] != "complete"
        assert result["step_status"]["data_bindings"] == "error"

    def test_data_bindings_complete_with_working_source(self, session, tmp_path):
        """A working source with every required binding set reads as complete."""
        csv = tmp_path / "ok.csv"
        csv.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")
        config = {
            "data": {"source": f"csv:{csv}"},
            "chart": {
                "type": "line",
                "output": "o",
                "title": "T",
                "x": "{{Year}}",
                "y": "{{Value}}",
            },
        }
        result = session.preflight(config)
        assert result["step_status"]["data_bindings"] == "complete"


class TestRenderPreview:
    """Direct render_preview coverage for edge-case configs."""

    def test_preview_with_explicit_dpi_does_not_collide(self, session, tmp_path):
        """A config with an explicit ``dpi:`` must not crash with a duplicate
        dpi kwarg — the preview pins dpi=150 regardless."""
        csv = tmp_path / "dpi.csv"
        csv.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")
        config = {
            "data": {"source": f"csv:{csv}"},
            "chart": {
                "type": "line",
                "output": "dpi_preview",
                "title": "DPI",
                "x": "{{Year}}",
                "y": "{{Value}}",
                "dpi": 300,
            },
        }
        png = session.render_preview(config)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")

    def test_preview_sparse_color_and_linestyle_with_none(self, session, tmp_path):
        """Sparse per-series color/linestyle arrays with None entries validate
        and render — None color falls back to the cycle, None linestyle to solid."""
        csv = tmp_path / "sparse.csv"
        csv.write_text("Year,A,B,C\n2024,10,20,30\n2025,15,25,35\n", encoding="utf-8")
        config = {
            "data": {"source": f"csv:{csv}"},
            "chart": {
                "type": "line",
                "output": "sparse_style",
                "title": "Sparse",
                "x": "{{Year}}",
                "y": ["{{A}}", "{{B}}", "{{C}}"],
                "color": [None, None, "Neptune Blue"],
                "linestyle": [None, "--", None],
            },
        }
        # Validates (list[str | None] is accepted) and renders without error.
        assert session.validate_config(config) == []
        png = session.render_preview(config)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")


class TestLegendDictIntegration:
    """Integration test: legend dict survives clean → validate → build_render_context."""

    def test_legend_dict_reaches_render_context(self, tmp_path):
        """Legend dict form data flows through the full editor pipeline."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,A,B\n2024,10,30\n2025,20,40\n")

        config = {
            "data": {"source": f"csv:{csv}"},
            "chart": {
                "type": "line",
                "output": "legend_integration",
                "title": "Legend Test",
                "x": "{{Year}}",
                "y": ["{{A}}", "{{B}}"],
                "legend": {"loc": "upper right", "fontsize": "medium", "ncol": 3},
            },
        }

        from tpsplots.editor.session import _clean_form_data
        from tpsplots.models.yaml_config import YAMLChartConfig
        from tpsplots.processors.render_pipeline import build_render_context
        from tpsplots.processors.resolvers import DataResolver

        cleaned = _clean_form_data(config)
        validated = YAMLChartConfig(**cleaned)
        data = DataResolver.resolve(validated.data)
        ctx = build_render_context(validated, data, log_conflicts=False)

        # Legend dict should survive the full pipeline
        assert isinstance(ctx.resolved_params["legend"], dict)
        assert ctx.resolved_params["legend"]["loc"] == "upper right"
        assert ctx.resolved_params["legend"]["fontsize"] == "medium"
        assert ctx.resolved_params["legend"]["ncol"] == 3

    def test_grid_false_reaches_render_context(self, tmp_path):
        """grid=False survives the full editor pipeline."""
        csv = tmp_path / "data.csv"
        csv.write_text("Category,Amount\nA,100\n")

        config = {
            "data": {"source": f"csv:{csv}"},
            "chart": {
                "type": "bar",
                "output": "grid_test",
                "title": "Grid Test",
                "categories": "{{Category}}",
                "values": "{{Amount}}",
                "grid": False,
            },
        }

        from tpsplots.editor.session import _clean_form_data
        from tpsplots.models.yaml_config import YAMLChartConfig
        from tpsplots.processors.render_pipeline import build_render_context
        from tpsplots.processors.resolvers import DataResolver

        cleaned = _clean_form_data(config)
        validated = YAMLChartConfig(**cleaned)
        data = DataResolver.resolve(validated.data)
        ctx = build_render_context(validated, data, log_conflicts=False)

        assert ctx.resolved_params["grid"] is False
