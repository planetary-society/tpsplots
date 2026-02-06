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

    assert captured["url"] == "https://docs.google.com/spreadsheets/d/abc123/export?format=csv"
    assert "data" in result
    assert list(result["data"].columns) == ["Year", "Value"]
