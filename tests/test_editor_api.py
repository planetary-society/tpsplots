"""Integration tests for editor FastAPI endpoints."""

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.conftest import bump_mtime
from tpsplots.editor.app import create_editor_app
from tpsplots.editor.session import EditorSession
from tpsplots.editor.ui_schema import get_available_chart_types


@pytest.fixture
def yaml_dir(tmp_path):
    sample = {
        "data": {"source": "data/test.csv"},
        "chart": {"type": "bar", "output": "test_chart", "title": "Test"},
    }
    (tmp_path / "sample.yaml").write_text(
        yaml.dump(sample, default_flow_style=False), encoding="utf-8"
    )
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "nested.yaml").write_text(
        yaml.dump(sample, default_flow_style=False), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def client(yaml_dir):
    session = EditorSession(yaml_dir=yaml_dir)
    app = create_editor_app(session)
    return TestClient(app)


class TestSchemaEndpoint:
    def test_get_bar_schema(self, client):
        resp = client.get("/api/schema?type=bar")
        assert resp.status_code == 200
        data = resp.json()
        assert "json_schema" in data
        assert "ui_schema" in data
        assert "editor_hints" in data
        assert data["json_schema"]["type"] == "object"
        hints = data["editor_hints"]
        assert "primary_binding_fields" in hints
        assert "step_field_map" in hints
        assert "field_tiers" in hints

    def test_get_schema_all_types(self, client):
        types_resp = client.get("/api/chart-types")
        for chart_type in types_resp.json()["types"]:
            resp = client.get(f"/api/schema?type={chart_type}")
            assert resp.status_code == 200

    def test_invalid_type_returns_400(self, client):
        resp = client.get("/api/schema?type=nonexistent")
        assert resp.status_code == 400


class TestChartTypesEndpoint:
    def test_returns_chart_types(self, client):
        resp = client.get("/api/chart-types")
        assert resp.status_code == 200
        types = resp.json()["types"]
        expected = get_available_chart_types()
        assert types == expected
        assert "bar" in types
        assert "line" in types
        assert "line_subplots" not in types


class TestFilesEndpoint:
    def test_list_files(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        files = resp.json()["files"]
        paths = {f["path"] for f in files}
        assert "sample.yaml" in paths
        assert "nested/nested.yaml" in paths

    def test_list_files_enriched_shape(self, client):
        """Each entry carries path + chart type + title."""
        files = client.get("/api/files").json()["files"]
        sample = next(f for f in files if f["path"] == "sample.yaml")
        assert set(sample) == {"path", "type", "title"}
        assert sample["type"] == "bar"
        assert sample["title"] == "Test"

    def test_list_files_tolerates_unreadable(self, client, yaml_dir):
        """A malformed file is listed with null type/title, not dropped."""
        (yaml_dir / "broken.yaml").write_text("chart: [unclosed", encoding="utf-8")
        files = client.get("/api/files").json()["files"]
        broken = next(f for f in files if f["path"] == "broken.yaml")
        assert broken["type"] is None
        assert broken["title"] is None

    def test_load_file(self, client):
        resp = client.get("/api/load?path=sample.yaml")
        assert resp.status_code == 200
        config = resp.json()["config"]
        assert config["chart"]["type"] == "bar"

    def test_load_nonexistent_returns_404(self, client):
        resp = client.get("/api/load?path=nope.yaml")
        assert resp.status_code == 404

    def test_load_malformed_yaml_returns_400(self, client, yaml_dir):
        (yaml_dir / "broken.yaml").write_text("key: [unclosed", encoding="utf-8")
        resp = client.get("/api/load?path=broken.yaml")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Malformed YAML" in detail

    def test_save_file(self, client, yaml_dir):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "donut", "output": "new", "title": "New"},
        }
        resp = client.post("/api/save", json={"path": "new.yaml", "config": config})
        assert resp.status_code == 200
        assert (yaml_dir / "new.yaml").exists()

    def test_save_invalid_config_returns_409_validation(self, client, yaml_dir):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "bar"},
        }
        resp = client.post("/api/save", json={"path": "invalid.yaml", "config": config})
        assert resp.status_code == 409
        body = resp.json()
        assert body["kind"] == "validation"
        assert body["errors"], "expected structured validation errors"
        # The blocked save must not have written the file.
        assert not (yaml_dir / "invalid.yaml").exists()

    def test_save_path_traversal_blocked(self, client):
        config = {
            "data": {"source": "test"},
            "chart": {"type": "bar", "output": "x", "title": "x"},
        }
        resp = client.post("/api/save", json={"path": "../../evil.yaml", "config": config})
        assert resp.status_code == 400

    def test_save_conflict_returns_409(self, client, yaml_dir):
        """Load a file, then change it on disk: the next save is refused."""
        client.get("/api/load?path=sample.yaml")
        # Make the on-disk file strictly newer than the recorded load mtime.
        sample = yaml_dir / "sample.yaml"
        bump_mtime(sample)

        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "New Title"},
        }
        resp = client.post("/api/save", json={"path": "sample.yaml", "config": config})
        assert resp.status_code == 409
        assert resp.json()["kind"] == "conflict"

    def test_override_validation_saves_invalid_config(self, client, yaml_dir):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "bar"},  # missing required output/title
        }
        resp = client.post(
            "/api/save",
            json={"path": "forced.yaml", "config": config, "override_validation": True},
        )
        assert resp.status_code == 200
        assert (yaml_dir / "forced.yaml").exists()

    def test_override_conflict_keeps_validation(self, client, yaml_dir):
        client.get("/api/load?path=sample.yaml")
        sample = yaml_dir / "sample.yaml"
        bump_mtime(sample)

        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "Forced Title"},
        }
        resp = client.post(
            "/api/save",
            json={"path": "sample.yaml", "config": config, "override_conflict": True},
        )
        assert resp.status_code == 200
        loaded = yaml.safe_load(sample.read_text(encoding="utf-8"))
        assert loaded["chart"]["title"] == "Forced Title"

        # The same override must NOT bypass validation.
        bad = {"data": {"source": "data/test.csv"}, "chart": {"type": "bar"}}
        resp = client.post(
            "/api/save",
            json={"path": "sample.yaml", "config": bad, "override_conflict": True},
        )
        assert resp.status_code == 409
        assert resp.json()["kind"] == "validation"


class TestValidateEndpoint:
    def test_valid_config(self, client):
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test", "title": "Test"},
        }
        resp = client.post("/api/validate", json=config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_invalid_config(self, client):
        config = {"data": {"source": "test"}, "chart": {"type": "bar"}}
        resp = client.post("/api/validate", json=config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        paths = {err["path"] for err in data["errors"]}
        assert "/chart/output" in paths
        assert "/chart/title" in paths

    def test_valid_line_config_accepts_markersize_list(self, client, yaml_dir):
        csv_path = yaml_dir / "markersize.csv"
        csv_path.write_text("Year,SeriesA,SeriesB\n2024,10,20\n2025,15,25\n", encoding="utf-8")
        config = {
            "data": {"source": f"csv:{csv_path}"},
            "chart": {
                "type": "line",
                "output": "line_markersize_list",
                "title": "Line Markersize List",
                "x": "{{Year}}",
                "y": ["{{SeriesA}}", "{{SeriesB}}"],
                "markersize": [4, 8],
            },
        }
        resp = client.post("/api/validate", json=config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["errors"] == []


class TestColorsEndpoint:
    def test_returns_colors(self, client):
        resp = client.get("/api/colors")
        assert resp.status_code == 200
        data = resp.json()
        assert "colors" in data
        assert "tps_colors" in data
        assert "Neptune Blue" in data["tps_colors"]


class TestDataEndpoints:
    def test_get_data_schema(self, client):
        resp = client.get("/api/data-schema")
        assert resp.status_code == 200
        payload = resp.json()
        assert "json_schema" in payload
        assert "ui_schema" in payload
        assert payload["json_schema"]["type"] == "object"
        assert "source" in payload["json_schema"]["properties"]
        assert payload["ui_schema"]["params"]["ui:widget"] == "dataParams"
        assert payload["ui_schema"]["calculate_inflation"]["ui:widget"] == "inflationConfig"

    def test_data_profile_valid_csv_source(self, client, yaml_dir):
        csv_path = yaml_dir / "profile.csv"
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")

        resp = client.post(
            "/api/data-profile",
            json={"data": {"source": f"csv:{csv_path}"}},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["source_kind"] == "csv"
        assert payload["row_count"] == 2
        assert any(col["name"] == "Year" for col in payload["columns"])
        assert isinstance(payload["sample_rows"], list)
        assert "warnings" in payload
        assert "context_keys" in payload
        assert isinstance(payload["context_keys"], list)

    def test_data_profile_invalid_source_returns_400(self, client):
        resp = client.post(
            "/api/data-profile",
            json={"data": {"source": "csv:/definitely/missing/file.csv"}},
        )
        assert resp.status_code == 400

    def test_preflight_reports_missing_bindings(self, client):
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "line", "output": "x", "title": "T"},
        }
        resp = client.post("/api/preflight", json={"config": config})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ready_for_preview"] is False
        missing = set(payload["missing_paths"])
        assert "/chart/x" in missing
        assert "/chart/y" in missing
        assert "step_status" in payload

    def test_preflight_reports_missing_us_map_pie_binding(self, client):
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "us_map_pie", "output": "map", "title": "Map"},
        }
        resp = client.post("/api/preflight", json={"config": config})
        assert resp.status_code == 200
        payload = resp.json()
        missing = set(payload["missing_paths"])
        assert "/chart/pie_data" in missing

    def test_preflight_yaml_preview_only_when_requested(self, client):
        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "Test"},
        }
        resp = client.post("/api/preflight", json={"config": config})
        assert "yaml_preview" not in resp.json()

        resp = client.post("/api/preflight", json={"config": config, "include_yaml": True})
        preview = resp.json()["yaml_preview"]
        assert "type: bar" in preview
        assert "title: Test" in preview

    def test_preflight_yaml_preview_merges_existing_file(self, client, yaml_dir):
        """With a path, the preview is the comment-preserving merge — the pane
        shows exactly what a save would write, protected keys included."""
        target = yaml_dir / "sample.yaml"
        target.write_text("# hand comment\n" + target.read_text(encoding="utf-8"), encoding="utf-8")
        client.get("/api/load?path=sample.yaml")

        config = {
            "data": {"source": "data/test.csv"},
            "chart": {"type": "bar", "output": "test_chart", "title": "Renamed"},
        }
        resp = client.post(
            "/api/preflight",
            json={"config": config, "include_yaml": True, "path": "sample.yaml"},
        )
        preview = resp.json()["yaml_preview"]
        assert "# hand comment" in preview
        assert "title: Renamed" in preview
        # Preview must not have written anything.
        assert "Renamed" not in target.read_text(encoding="utf-8")

    def test_preflight_yaml_preview_renders_invalid_config(self, client):
        """The pane shows work-in-progress configs too — no validation gate."""
        config = {"data": {"source": "data/test.csv"}, "chart": {"type": "bar"}}
        resp = client.post("/api/preflight", json={"config": config, "include_yaml": True})
        assert resp.status_code == 200
        assert "type: bar" in resp.json()["yaml_preview"]


class TestRefreshDataEndpoint:
    def test_refresh_data_returns_ok(self, client):
        resp = client.post("/api/refresh-data")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_refresh_data_invalidates_cache(self, yaml_dir):
        session = EditorSession(yaml_dir=yaml_dir)
        client = TestClient(create_editor_app(session))
        session._data_cache["k"] = {"some": "data"}
        session._profile_cache["k"] = {"some": "profile"}

        resp = client.post("/api/refresh-data")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        assert session._data_cache == {}
        assert session._profile_cache == {}


class TestPreviewEndpoint:
    def test_preview_renders_png_for_line_chart(self, client, yaml_dir):
        csv_path = yaml_dir / "preview.csv"
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")

        config = {
            "data": {"source": f"csv:{csv_path}"},
            "chart": {
                "type": "line",
                "output": "preview_line",
                "title": "Preview",
                "x": "{{Year}}",
                "y": "{{Value}}",
            },
        }

        resp = client.post("/api/preview", json={"config": config, "device": "desktop"})

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content.startswith(b"\x89PNG\r\n\x1a\n")

    def test_preview_typo_ref_returns_400(self, client):
        """A typo'd {{ref}} against a working data source returns 400 (with the
        resolver message), never a 500."""
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
        resp = client.post("/api/preview", json={"config": config, "device": "desktop"})
        assert resp.status_code == 400
        assert "Available keys" in resp.json()["detail"]


class TestSecurityHeaders:
    def test_csp_header_on_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        csp = resp.headers.get("content-security-policy", "")
        assert "script-src" in csp
        assert "esm.sh" in csp

    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"
