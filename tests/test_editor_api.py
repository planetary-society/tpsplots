"""Integration tests for editor FastAPI endpoints."""

import pytest
import yaml
from fastapi.testclient import TestClient

from tpsplots.editor.app import create_editor_app
from tpsplots.editor.session import EditorSession


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
        assert data["json_schema"]["type"] == "object"

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
        assert "bar" in types
        assert "line" in types
        assert len(types) == 10


class TestFilesEndpoint:
    def test_list_files(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        files = resp.json()["files"]
        assert "sample.yaml" in files
        assert "nested/nested.yaml" in files

    def test_load_file(self, client):
        resp = client.get("/api/load?path=sample.yaml")
        assert resp.status_code == 200
        config = resp.json()["config"]
        assert config["chart"]["type"] == "bar"

    def test_load_nonexistent_returns_404(self, client):
        resp = client.get("/api/load?path=nope.yaml")
        assert resp.status_code == 404

    def test_save_file(self, client, yaml_dir):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "donut", "output": "new", "title": "New"},
        }
        resp = client.post("/api/save", json={"path": "new.yaml", "config": config})
        assert resp.status_code == 200
        assert (yaml_dir / "new.yaml").exists()

    def test_save_invalid_config_returns_400(self, client):
        config = {
            "data": {"source": "data/new.csv"},
            "chart": {"type": "bar"},
        }
        resp = client.post("/api/save", json={"path": "invalid.yaml", "config": config})
        assert resp.status_code == 400

    def test_save_path_traversal_blocked(self, client):
        config = {
            "data": {"source": "test"},
            "chart": {"type": "bar", "output": "x", "title": "x"},
        }
        resp = client.post("/api/save", json={"path": "../../evil.yaml", "config": config})
        assert resp.status_code == 400


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


class TestColorsEndpoint:
    def test_returns_colors(self, client):
        resp = client.get("/api/colors")
        assert resp.status_code == 200
        data = resp.json()
        assert "colors" in data
        assert "tps_colors" in data
        assert "Neptune Blue" in data["tps_colors"]


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
