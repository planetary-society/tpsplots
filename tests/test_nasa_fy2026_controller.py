"""Tests for NASAFY2026Controller matching behavior."""

from datetime import datetime

import pandas as pd

from tpsplots.controllers.nasa_fy2026_controller import NASAFY2026Controller


def test_cancelled_missions_filters_status_case_insensitively(monkeypatch):
    """Mixed-case status labels should match mission status filter."""

    class _StubMissions:
        def data(self):
            return pd.DataFrame(
                {
                    "Mission": ["Mission Alpha", "Mission Beta", "Mission Gamma"],
                    "Launch Date": [
                        datetime(2010, 1, 1),
                        datetime(2012, 1, 1),
                        datetime(2014, 1, 1),
                    ],
                    "Formulation Start": [datetime(2005, 1, 1), datetime(2007, 1, 1), None],
                    "LCC": [1_000_000_000, 2_000_000_000, 3_000_000_000],
                    "NASA Led?": [True, True, True],
                    "Status": ["prime mission", "EXTENDED MISSION", "FORMULATION"],
                }
            )

    monkeypatch.setattr("tpsplots.controllers.nasa_fy2026_controller.Missions", _StubMissions)

    controller = object.__new__(NASAFY2026Controller)
    result = controller.cancelled_missions_lollipop_chart()

    assert result["categories"].tolist() == ["Mission Alpha", "Mission Beta"]
    assert result["total_projects"] == 2
