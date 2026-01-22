import csv
import logging
from datetime import datetime
from pathlib import Path

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
    """Inject a lightweight in-memory table without hitting the network."""

    def __init__(self, year: str, df: pd.DataFrame):
        self._test_df = df
        super().__init__(year=year)

    def _load_raw(self) -> pd.DataFrame:
        return self._test_df


def _nnsi_from_rows(rows: list[list[object]], year: str = "2025") -> NNSI:
    """Build a minimal NNSI instance from a list-of-rows table."""
    return DummyNNSI(year=year, df=pd.DataFrame(rows))


@pytest.fixture(scope="module")
def nnsi_fixture_path() -> Path:
    # Large CSV fixture is parsed once per module to keep tests fast.
    return Path(__file__).parent / "fixtures" / "nnsi.csv"


@pytest.fixture(scope="module")
def nnsi_2025(nnsi_fixture_path: Path) -> NNSI:
    # Exercise the full parsing pipeline against the real-shaped fixture.
    return NNSI(year="2025", source=nnsi_fixture_path)


def _coerce_numeric(value: str) -> float:
    text = value.strip()
    if text.endswith("%"):
        return float(text.rstrip("%")) / 100
    return float(text)


def _fixture_multiplier(path: Path, from_label: str, target_year: int) -> float:
    # Read fixture data directly to validate NNSI parsing against the raw source.
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))

    header_idx = next(i for i, row in enumerate(rows) if row and row[0].strip().upper() == "YEAR")
    header = rows[header_idx]
    col_idx = header.index(str(target_year))

    for row in rows[header_idx + 1 :]:
        if row and row[0].strip() == from_label:
            if col_idx >= len(row):
                raise AssertionError(f"Missing column {target_year} for {from_label}")
            return _coerce_numeric(row[col_idx])

    raise AssertionError(f"Row {from_label} not found in fixture")


def test_gdp_partial_quarters_use_available_data(caplog):
    # Validate FY aggregation and warning behavior when the target FY is incomplete.
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
    # Missing target year should fail fast with a DataSourceError.
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


@pytest.mark.parametrize(
    ("from_year", "from_label"),
    [
        ("2024", "FROM 2024"),
        (2024, "FROM 2024"),
        (datetime(2024, 1, 1), "FROM 2024"),
    ],
)
def test_nnsi_calc_matches_fixture(
    nnsi_2025: NNSI,
    nnsi_fixture_path: Path,
    from_year,
    from_label,
):
    # Ensure calc matches the raw fixture values for multiple input types.
    expected = _fixture_multiplier(nnsi_fixture_path, from_label, 2025)
    assert nnsi_2025.calc(from_year, 100) == pytest.approx(expected * 100)


def test_nnsi_tq_aliases(nnsi_2025: NNSI, nnsi_fixture_path: Path):
    # Transition Quarter inputs should use the same multiplier.
    expected = _fixture_multiplier(nnsi_fixture_path, "FROM TQ", 2025)
    assert nnsi_2025.calc("TQ", 100) == pytest.approx(expected * 100)
    assert nnsi_2025.calc("1976 TQ", 100) == pytest.approx(expected * 100)


def test_nnsi_unknown_year_is_identity(nnsi_2025: NNSI):
    # Unknown years fall back to identity instead of raising.
    assert nnsi_2025.calc("1899", 100) == pytest.approx(100.0)


def test_nnsi_missing_target_year_raises(nnsi_fixture_path: Path):
    # If the target year column is absent, the loader must raise.
    with pytest.raises(DataSourceError):
        NNSI(year="1800", source=nnsi_fixture_path)


def test_nnsi_percent_values_parsed():
    # Percent strings in FROM rows should be converted to multipliers.
    nnsi = _nnsi_from_rows(
        [
            ["YEAR", "2024", "2025"],
            ["FROM 2024", "100%", "110%"],
            ["FROM TQ", "105%", "115%"],
        ],
        year="2025",
    )
    assert nnsi.calc("2024", 100) == pytest.approx(110.0)
    assert nnsi.calc("TQ", 100) == pytest.approx(115.0)


def test_nnsi_header_missing_raises():
    # A missing YEAR header should be treated as an invalid table.
    with pytest.raises(DataSourceError):
        _nnsi_from_rows(
            [
                ["HEADER", "2024", "2025"],
                ["FROM 2024", "100%", "110%"],
            ],
            year="2025",
        )


def test_gdp_q4_rolls_into_next_fiscal_year():
    # Q4 should roll into the next fiscal year for deflator averages.
    df = pd.DataFrame(
        {
            "observation_date": [
                "2024-07-01",  # FY 2024 (Q3)
                "2024-10-01",  # FY 2025 (Q4)
            ],
            "GDPDEF": [100, 200],
        }
    )
    gdp = DummyGDP(year="2025", df=df)
    assert gdp.calc("2024", 1.0) == pytest.approx(2.0)
    assert gdp.calc("2025", 1.0) == pytest.approx(1.0)
