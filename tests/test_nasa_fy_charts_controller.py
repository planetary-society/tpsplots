"""Regression tests for directorate filtering in NASAFYChartsController."""

from typing import ClassVar
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController


class _StubFY2026Controller(NASAFYChartsController):
    FISCAL_YEAR = 2026
    ACCOUNTS: ClassVar[dict[str, str]] = {
        "Deep Space Exploration Systems": "Exploration",
        "LEO & Space Ops": "Space Ops",
        "Science": "Science",
    }
    ACCOUNT_ALIASES: ClassVar[dict[str, list[str]]] = {
        "LEO & Space Ops": ["Space Operations"],
    }


def _make_controller(budget_detail: pd.DataFrame) -> _StubFY2026Controller:
    controller = object.__new__(_StubFY2026Controller)
    controller.budget_detail = budget_detail
    return controller


def test_directorates_grouped_matches_uppercase_account_labels():
    """Uppercase account labels from source data should still match ACCOUNTS."""
    controller = _make_controller(
        pd.DataFrame(
            {
                "Account": [
                    "DEEP SPACE EXPLORATION SYSTEMS",
                    "LEO & SPACE OPS",
                    "SCIENCE",
                ],
                "FY 2025 Enacted": [9, 8, 7],
                "FY 2026 Request": [9.5, 8.5, 7.5],
                "Appropriated": [9.1, 8.1, 7.1],
            }
        )
    )

    result = controller.directorates_comparison_grouped()

    assert result["categories"] == ["Exploration", "Space Ops", "Science"]
    assert result["export_df"].shape[0] == 3
    assert len(result["groups_all"]) == 3


def test_directorates_grouped_raises_if_no_rows_match_accounts():
    """Should fail fast when account filtering produces no rows."""
    controller = _make_controller(
        pd.DataFrame(
            {
                "Account": ["Unknown Directorate"],
                "FY 2025 Enacted": [1],
                "FY 2026 Request": [2],
                "Appropriated": [3],
            }
        )
    )

    with pytest.raises(ValueError, match="No directorate rows matched configured accounts"):
        controller.directorates_comparison_grouped()


def test_directorates_grouped_supports_configured_account_aliases():
    """Controller should pass ACCOUNT_ALIASES through account filtering."""
    controller = _make_controller(
        pd.DataFrame(
            {
                "Account": ["Space Operations", "SCIENCE"],
                "FY 2025 Enacted": [8, 7],
                "FY 2026 Request": [8.5, 7.5],
                "Appropriated": [8.1, 7.1],
            }
        )
    )

    result = controller.directorates_comparison_grouped()

    assert result["categories"] == ["Space Ops", "Science"]
    assert result["export_df"].shape[0] == 2


def test_major_accounts_context_matches_case_insensitive_account_labels():
    """Major accounts filtering should be case-insensitive."""
    controller = _make_controller(
        pd.DataFrame(
            {
                "Account": [
                    "DEEP SPACE EXPLORATION SYSTEMS",
                    "LEO & SPACE OPS",
                    "SCIENCE",
                    "UNRELATED",
                ],
                "FY 2026 Request": [9.5, 8.5, 7.5, 1.0],
            }
        )
    )

    result = controller.major_accounts_context()

    assert result["Account"].tolist() == [
        "DEEP SPACE EXPLORATION SYSTEMS",
        "LEO & SPACE OPS",
        "SCIENCE",
    ]
    assert result["FY 2026 Request"].tolist() == [9.5, 8.5, 7.5]


def test_directorates_context_applies_inflation_adjustment(monkeypatch):
    """Directorate context should expose inflation-adjusted directorate series."""
    controller = object.__new__(_StubFY2026Controller)
    directorates_df = pd.DataFrame(
        {
            "Fiscal Year": pd.to_datetime(["2024-01-01", "2025-01-01", "2026-01-01"]),
            "Exploration": [10.0, 11.0, 12.0],
            "Exploration White House Budget Projection": [pd.NA, 12.5, 13.5],
            "Science": [20.0, 21.0, 22.0],
            "Science White House Budget Projection": [pd.NA, 22.5, 23.5],
        }
    )

    monkeypatch.setattr(
        _StubFY2026Controller,
        "_directorates_data",
        lambda self: directorates_df.copy(),
    )

    mock_processor = MagicMock()

    def _apply_adjustment(df):
        adjusted = df.copy()
        for col in ["Exploration", "Science"]:
            adjusted[f"{col}_adjusted_nnsi"] = adjusted[col] * 1.5
        adjusted.attrs["inflation_target_year"] = 2025
        return adjusted

    mock_processor.process.side_effect = _apply_adjustment

    with patch(
        "tpsplots.controllers.nasa_fy_charts_controller.InflationAdjustmentProcessor",
        return_value=mock_processor,
    ) as processor_cls:
        result = controller.directorates_context()

    inflation_config = processor_cls.call_args.args[0]
    assert inflation_config.target_year == 2025
    assert inflation_config.nnsi_columns == ["Exploration", "Science"]
    assert "Exploration_adjusted_nnsi" in result
    assert "Science_adjusted_nnsi" in result
    assert "Exploration White House Budget Projection_adjusted_nnsi" not in result
    assert result["metadata"]["inflation_adjusted_year"] == 2025
