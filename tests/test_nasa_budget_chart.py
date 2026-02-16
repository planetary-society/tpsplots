"""Tests for NASABudgetChart percent-of-spending preparation helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from tpsplots.controllers.nasa_budget_chart import NASABudgetChart


class _DummyHistorical:
    """Minimal Historical() replacement for deterministic tests."""

    def data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Fiscal Year": pd.to_datetime(["2022-01-01", "2023-01-01", "2024-01-01"]),
                "Appropriation": [24_000_000_000, 25_000_000_000, 26_000_000_000],
                "% of U.S. Spending": [0.70, 0.65, pd.NA],
                "% of U.S. Discretionary Spending": [1.90, None, 2.00],
            }
        )


class _NoOpInflationProcessor:
    """No-op processor used to avoid inflation dependency in unit tests."""

    def __init__(self, config):
        self._config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Appropriation_adjusted_nnsi"] = df["Appropriation"]
        df.attrs["inflation_target_year"] = self._config.target_year
        return df


class _DummyInflationConfig:
    def __init__(self, **kwargs):
        self.target_year = 2025
        self.nnsi_columns = kwargs.get("nnsi_columns", [])


class _DummyDirectorates:
    def data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "Fiscal Year": pd.to_datetime(["2022-01-01", "2023-01-01"]),
                "Aeronautics": [1_000_000_000, 1_100_000_000],
                "Deep Space Exploration Systems": [7_000_000_000, 7_100_000_000],
                "Space Operations": [4_000_000_000, 4_100_000_000],
                "Space Technology": [1_200_000_000, 1_300_000_000],
                "Science": [7_800_000_000, 8_000_000_000],
                "STEM Education": [120_000_000, 130_000_000],
                "Facilities, IT, & Salaries": [3_500_000_000, 3_600_000_000],
            }
        )


class _NoOpDirectorateInflationProcessor:
    def __init__(self, config):
        self._config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in self._config.nnsi_columns:
            df[f"{col}_adjusted_nnsi"] = df[col]
        df.attrs["inflation_target_year"] = self._config.target_year
        return df


def test_nasa_spending_share_by_year_returns_clean_numeric_percent_columns(monkeypatch):
    monkeypatch.setattr(
        "tpsplots.controllers.nasa_budget_chart.Historical",
        _DummyHistorical,
    )
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentConfig",
        _DummyInflationConfig,
    )
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentProcessor",
        _NoOpInflationProcessor,
    )

    controller = NASABudgetChart()
    result = controller.nasa_spending_share_by_year()

    assert list(result["fiscal_year"]) == list(pd.to_datetime(["2022-01-01", "2023-01-01"]))
    assert list(result["appropriation_adjusted"]) == [24_000_000_000, 25_000_000_000]
    assert list(result["us_spending_percent"]) == [0.70, 0.65]
    assert result["us_spending_share"].tolist() == pytest.approx([0.007, 0.0065])
    assert result["us_discretionary_spending_percent"].iloc[0] == 1.90
    assert pd.isna(result["us_discretionary_spending_percent"].iloc[1])
    assert result["us_discretionary_spending_share"].iloc[0] == pytest.approx(0.019)
    assert pd.isna(result["us_discretionary_spending_share"].iloc[1])

    export_df = result["export_df"]
    assert list(export_df.columns) == [
        "Fiscal Year",
        "Appropriation_adjusted_nnsi",
        "% of U.S. Spending",
        "% of U.S. Discretionary Spending",
    ]
    assert result["metadata"]["inflation_adjusted_year"] == 2025


def test_nasa_major_programs_metadata_includes_inflation_adjusted_year(monkeypatch):
    monkeypatch.setattr(
        "tpsplots.controllers.nasa_budget_chart.Directorates",
        _DummyDirectorates,
    )
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentConfig",
        _DummyInflationConfig,
    )
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentProcessor",
        _NoOpDirectorateInflationProcessor,
    )

    controller = NASABudgetChart()
    result = controller.nasa_major_programs_by_year_inflation_adjusted()

    assert result["metadata"]["inflation_adjusted_year"] == 2025
