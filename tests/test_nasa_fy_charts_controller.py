"""Regression tests for directorate filtering in NASAFYChartsController."""

import pandas as pd
import pytest

from tpsplots.controllers.nasa_fy_charts_controller import NASAFYChartsController


class _StubFY2026Controller(NASAFYChartsController):
    FISCAL_YEAR = 2026
    ACCOUNTS = {
        "Deep Space Exploration Systems": "Exploration",
        "LEO & Space Ops": "Space Ops",
        "Science": "Science",
    }
    ACCOUNT_ALIASES = {
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
