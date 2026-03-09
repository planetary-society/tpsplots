"""Tests for GoogleSheetsController behavior."""

import pandas as pd

from tpsplots.controllers.google_sheets_controller import GoogleSheetsController


def test_load_data_normalizes_google_sheets_url(monkeypatch):
    """Controller should normalize edit URLs to CSV export URLs before fetch."""
    captured: dict[str, str] = {}

    class DummySource:
        def __init__(self, url, **_kwargs):
            captured["url"] = url

        def data(self):
            return pd.DataFrame({"Year": [2024], "Value": [1]})

    monkeypatch.setattr(
        "tpsplots.controllers.google_sheets_controller.GoogleSheetsSource",
        DummySource,
    )

    controller = GoogleSheetsController(
        url="https://docs.google.com/spreadsheets/d/abc123/edit#gid=0"
    )
    result = controller.load_data()

    assert (
        captured["url"] == "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=0"
    )
    assert "data" in result
    assert list(result["data"].columns) == ["Year", "Value"]


_normalize = staticmethod(GoogleSheetsController.normalize_google_sheets_url)


class TestNormalizeGoogleSheetsUrl:
    """Tests for gid preservation during URL normalization."""

    def test_edit_url_with_fragment_gid(self):
        url = "https://docs.google.com/spreadsheets/d/abc123/edit#gid=456"
        assert _normalize(url) == (
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=456"
        )

    def test_edit_url_without_gid(self):
        url = "https://docs.google.com/spreadsheets/d/abc123/edit"
        assert _normalize(url) == (
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv"
        )

    def test_edit_url_with_query_gid(self):
        url = "https://docs.google.com/spreadsheets/d/abc123/edit?gid=789&other=1"
        assert _normalize(url) == (
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=789"
        )

    def test_already_export_url_unchanged(self):
        url = "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=456"
        assert _normalize(url) == url

    def test_non_google_url_unchanged(self):
        url = "https://example.com/data.csv"
        assert _normalize(url) == url
