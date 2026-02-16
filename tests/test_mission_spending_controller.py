"""Tests for MissionSpendingController matching behavior."""

import pandas as pd

from tpsplots.controllers.mission_spending_controller import MissionSpendingController


def test_process_mission_spending_data_accepts_uppercase_reporting_type(monkeypatch):
    """Reporting type matching should be case-insensitive."""
    controller = MissionSpendingController(csv_path=".")

    sample = pd.DataFrame(
        {
            "fiscal_year": [2025, 2025, 2024, 2024],
            "fiscal_period": [1, 2, 1, 2],
            "cumulative_outlay": [10.0, 20.0, 8.0, 16.0],
        }
    )
    monkeypatch.setattr(controller, "_read_csv", lambda _path: sample)

    result = controller._process_mission_spending_data("unused.csv", "OUTLAYS")

    assert result["current_fy"] == 2025
    assert result["prior_fy"] == 2024
    assert list(result["y2"]) == [8.0, 16.0]
