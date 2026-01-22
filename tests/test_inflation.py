import logging

import pandas as pd
import pytest

from tpsplots.data_sources.inflation import GDP, NNSI
from tpsplots.exceptions import DataSourceError


class DummyGDP(GDP):
    def __init__(self, year: str, df: pd.DataFrame):
        self._test_df = df
        super().__init__(year=year)

    def _load_raw(self) -> pd.DataFrame:
        return self._test_df


class DummyNNSI(NNSI):
    def __init__(self, year: str, df: pd.DataFrame):
        self._test_df = df
        super().__init__(year=year)

    def _load_raw(self) -> pd.DataFrame:
        return self._test_df


def _nnsi_raw_table() -> pd.DataFrame:
    rows = [
        ["", "", ""],
        ["FROM", "2024", "2025"],
        ["FROM 2024", "100%", "110%"],
        ["FROM 2025", "90%", "100%"],
        ["FROM TQ", "105%", "115%"],
    ]
    return pd.DataFrame(rows)


def test_gdp_partial_quarters_use_available_data(caplog):
    df = pd.DataFrame(
        {
            "observation_date": [
                "2023-10-01",
                "2024-01-01",
                "2024-04-01",
                "2024-07-01",
                "2024-10-01",
                "2025-01-01",
                "2025-04-01",
            ],
            "GDPDEF": [100, 110, 120, 130, 140, 150, 160],
        }
    )

    with caplog.at_level(logging.WARNING):
        gdp = DummyGDP(year="2025", df=df)

    expected_fy2024 = 150 / 115

    assert "computed from 3 quarters" in caplog.text
    assert gdp.calc("2025", 1.0) == pytest.approx(1.0)
    assert gdp.calc("2024", 1.0) == pytest.approx(expected_fy2024)


def test_gdp_missing_target_year_raises():
    df = pd.DataFrame(
        {
            "observation_date": [
                "2023-10-01",
                "2024-01-01",
                "2024-04-01",
                "2024-07-01",
            ],
            "GDPDEF": [100, 110, 120, 130],
        }
    )

    with pytest.raises(DataSourceError):
        DummyGDP(year="2025", df=df)


def test_nnsi_parses_percentages_and_tq():
    nnsi = DummyNNSI(year="2025", df=_nnsi_raw_table())

    assert nnsi.calc("2024", 100) == pytest.approx(110.0)
    assert nnsi.calc("2025", 100) == pytest.approx(100.0)
    assert nnsi.calc("TQ", 100) == pytest.approx(115.0)
    assert nnsi.calc("1976 TQ", 100) == pytest.approx(115.0)


def test_nnsi_different_years_produce_different_results():
    """Adjusting to different target years should produce different values."""
    # Target year 2024: FROM 2024 → 2024 should give 100%
    nnsi_2024 = DummyNNSI(year="2024", df=_nnsi_raw_table())
    assert nnsi_2024.calc("2024", 100) == pytest.approx(100.0)

    # Target year 2025: FROM 2024 → 2025 should give 110%
    nnsi_2025 = DummyNNSI(year="2025", df=_nnsi_raw_table())
    assert nnsi_2025.calc("2024", 100) == pytest.approx(110.0)

def test_nnsi_year_parameter_is_used():
    """Verify that specifying year=X creates an adjuster targeting year X."""
    # This test ensures the year parameter is actually being used
    # and not ignored (which was the bug)
    nnsi_2024 = DummyNNSI(year="2024", df=_nnsi_raw_table())
    nnsi_2025 = DummyNNSI(year="2025", df=_nnsi_raw_table())

    # Same source year, different target years = different results
    result_2024 = nnsi_2024.calc("2025", 100)
    result_2025 = nnsi_2025.calc("2025", 100)

    # 2025 → 2024 should be 90%, 2025 → 2025 should be 100%
    assert result_2024 == pytest.approx(90.0)
    assert result_2025 == pytest.approx(100.0)
    assert result_2024 != result_2025
