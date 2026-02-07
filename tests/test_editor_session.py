"""Tests for EditorSession: validation, path security, file I/O."""

import pytest
import yaml

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

    def test_list_yaml_files(self, session):
        files = session.list_yaml_files()
        assert "sample.yaml" in files
        assert "another.yml" in files
        assert len(files) == 2


class TestDataCache:
    def test_invalidate_cache(self, session):
        session._data_cache["test_key"] = {"some": "data"}
        assert len(session._data_cache) == 1
        session.invalidate_data_cache()
        assert len(session._data_cache) == 0


class TestCleanFormData:
    """Verify RJSF empty-value cleanup."""

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
