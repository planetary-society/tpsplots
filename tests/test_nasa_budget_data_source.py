"""Tests for NASABudget data source module.

Tests focus on:
- Bug 1: FY column detection should work regardless of column position
- Bug 2: M/B suffix handling - billions should be 1000x millions
"""

from typing import ClassVar
from unittest.mock import patch

import pandas as pd
import pytest


# Mock the inflation module's network calls before importing NASABudget
# This prevents module-level network requests during import
@pytest.fixture(scope="module", autouse=True)
def mock_inflation_data():
    """Mock inflation data to prevent network calls on module import."""
    # Create mock table data
    mock_nnsi_table = {"2024": 1.0, "2025": 1.1}
    mock_gdp_table = {"2024": 1.0, "2025": 1.05}

    with (
        patch(
            "tpsplots.data_sources.inflation.NNSI._load_table",
            return_value=mock_nnsi_table,
        ),
        patch(
            "tpsplots.data_sources.inflation.GDP._load_table",
            return_value=mock_gdp_table,
        ),
    ):
        yield


# Import after mocking is set up in conftest or via the fixture
# For simplicity, we'll import inside the test functions to ensure mocking is active
def get_nasa_budget_class():
    """Import NASABudget with mocked dependencies."""
    with (
        patch(
            "tpsplots.data_sources.inflation.NNSI._load_table",
            return_value={"2024": 1.0, "2025": 1.1},
        ),
        patch(
            "tpsplots.data_sources.inflation.GDP._load_table",
            return_value={"2024": 1.0, "2025": 1.05},
        ),
    ):
        from tpsplots.data_sources.nasa_budget_data_source import NASABudget

        return NASABudget


class TestDetectFY:
    """Tests for _detect_fy() static method - Bug 1 fix."""

    @pytest.fixture(autouse=True)
    def setup_nasa_budget(self):
        """Get NASABudget class with mocked dependencies."""
        self.NASABudget = get_nasa_budget_class()

    def test_detect_fy_first_column(self):
        """FY column in first position should be detected."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022],
                "Budget": [1.0, 2.0, 3.0],
            }
        )
        assert self.NASABudget._detect_fy(df) == "Fiscal Year"

    def test_detect_fy_second_column(self):
        """FY column in second position should be detected (Bug 1 regression)."""
        df = pd.DataFrame(
            {
                "Budget": [1.0, 2.0, 3.0],
                "Fiscal Year": [2020, 2021, 2022],
            }
        )
        assert self.NASABudget._detect_fy(df) == "Fiscal Year"

    def test_detect_fy_last_column(self):
        """FY column in last position should be detected."""
        df = pd.DataFrame(
            {
                "Budget": [1.0, 2.0, 3.0],
                "Notes": ["a", "b", "c"],
                "year": [2020, 2021, 2022],
            }
        )
        assert self.NASABudget._detect_fy(df) == "year"

    def test_detect_fy_pattern_FY2024(self):
        """Column named 'FY2024' should be detected."""
        df = pd.DataFrame(
            {
                "Category": ["A", "B"],
                "FY2024": [100, 200],
            }
        )
        assert self.NASABudget._detect_fy(df) == "FY2024"

    def test_detect_fy_pattern_fy(self):
        """Column named 'fy' (lowercase) should be detected."""
        df = pd.DataFrame(
            {
                "Amount": [100, 200],
                "fy": [2020, 2021],
            }
        )
        assert self.NASABudget._detect_fy(df) == "fy"

    def test_detect_fy_no_match_returns_none(self):
        """When no FY column exists, should return None."""
        df = pd.DataFrame(
            {
                "Budget": [1.0, 2.0, 3.0],
                "Notes": ["a", "b", "c"],
            }
        )
        assert self.NASABudget._detect_fy(df) is None


class TestCleanCurrencyColumn:
    """Tests for currency cleaning and millions conversion."""

    @pytest.fixture(autouse=True)
    def setup_nasa_budget(self):
        """Get NASABudget class with mocked dependencies."""
        self.NASABudget = get_nasa_budget_class()

    def _make_test_budget(self):
        """Create a minimal NASABudget subclass for testing."""

        class TestBudget(self.NASABudget):
            MONETARY_COLUMNS: ClassVar[list[str]] = ["Amount"]

            def __init__(self):
                pass  # Skip CSV loading for tests

        return TestBudget()

    def test_millions_suffix_M(self):
        """Values with M suffix should multiply by 1,000,000."""
        budget = self._make_test_budget()
        series = pd.Series(["$50M", "$100M"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(50_000_000)
        assert result[1] == pytest.approx(100_000_000)

    def test_handles_na_values(self):
        """NA values should pass through as NA."""
        budget = self._make_test_budget()
        series = pd.Series(["$50M", pd.NA, "$100M"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(50_000_000)
        assert pd.isna(result[1])
        assert result[2] == pytest.approx(100_000_000)


class TestCleanPercentageColumn:
    """Tests for percentage cleaning in NASABudget data source."""

    @pytest.fixture(autouse=True)
    def setup_nasa_budget(self):
        """Get NASABudget class with mocked dependencies."""
        self.NASABudget = get_nasa_budget_class()

    def _make_test_budget(self):
        """Create a minimal NASABudget subclass for percentage cleaning tests."""

        class TestBudget(self.NASABudget):
            PERCENTAGE_COLUMNS: ClassVar[list[str]] = [
                "% of U.S. Spending",
                "% of U.S. Discretionary Spending",
            ]

            def __init__(self):
                pass  # Skip CSV loading for tests

        return TestBudget()

    def test_clean_percentage_column_parses_percent_strings(self):
        """Percentage strings should be converted to numeric percent values."""
        budget = self._make_test_budget()
        series = pd.Series(["0.55%", "0.40", 0.30, "", "n/a", None, "--", "1,200%"])
        result = budget._clean_percentage_column(series)

        assert result.iloc[0] == pytest.approx(0.55)
        assert result.iloc[1] == pytest.approx(0.40)
        assert result.iloc[2] == pytest.approx(0.30)
        assert pd.isna(result.iloc[3])
        assert pd.isna(result.iloc[4])
        assert pd.isna(result.iloc[5])
        assert pd.isna(result.iloc[6])
        assert result.iloc[7] == pytest.approx(1200.0)

    def test_clean_applies_percentage_cleaning_for_configured_columns(self):
        """_clean should normalize known percentage columns by default."""
        budget = self._make_test_budget()
        df = pd.DataFrame(
            {
                "Fiscal Year": [2022, 2023, 2024],
                "% of U.S. Spending": ["0.70%", "0.65", "bad"],
                "% of U.S. Discretionary Spending": ["1.90%", None, "2.00%"],
            }
        )

        cleaned = budget._clean(df)

        assert cleaned["% of U.S. Spending"].iloc[0] == pytest.approx(0.70)
        assert cleaned["% of U.S. Spending"].iloc[1] == pytest.approx(0.65)
        assert pd.isna(cleaned["% of U.S. Spending"].iloc[2])
        assert cleaned["% of U.S. Discretionary Spending"].iloc[0] == pytest.approx(1.90)
        assert pd.isna(cleaned["% of U.S. Discretionary Spending"].iloc[1])
        assert cleaned["% of U.S. Discretionary Spending"].iloc[2] == pytest.approx(2.00)
