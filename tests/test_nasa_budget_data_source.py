"""Tests for NASABudget data source module.

Tests focus on:
- Bug 1: FY column detection should work regardless of column position
- Bug 2: M/B suffix handling - billions should be 1000x millions
"""

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
    """Tests for currency cleaning with M/B suffix handling - Bug 2 fix."""

    @pytest.fixture(autouse=True)
    def setup_nasa_budget(self):
        """Get NASABudget class with mocked dependencies."""
        self.NASABudget = get_nasa_budget_class()

    def _make_test_budget(self):
        """Create a minimal NASABudget subclass for testing."""

        class TestBudget(self.NASABudget):
            MONETARY_COLUMNS = ["Amount"]

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

    def test_billions_suffix_B(self):
        """Values with B suffix should multiply by 1,000,000,000 (Bug 2 regression)."""
        budget = self._make_test_budget()
        series = pd.Series(["$50B", "$100B"])
        result = budget._clean_currency_column(series)

        # Bug 2: These should be billions, not millions
        assert result[0] == pytest.approx(50_000_000_000)
        assert result[1] == pytest.approx(100_000_000_000)

    def test_no_suffix_assumes_raw_value(self):
        """Values without M/B suffix should be used as-is."""
        budget = self._make_test_budget()
        series = pd.Series(["$50", "$100.50"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(50)
        assert result[1] == pytest.approx(100.50)

    def test_mixed_suffixes(self):
        """Mixed M and B suffixes should be handled correctly."""
        budget = self._make_test_budget()
        series = pd.Series(["$1B", "$500M", "$1000"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(1_000_000_000)
        assert result[1] == pytest.approx(500_000_000)
        assert result[2] == pytest.approx(1000)

    def test_lowercase_suffixes(self):
        """Lowercase m/b suffixes should work."""
        budget = self._make_test_budget()
        series = pd.Series(["$50m", "$50b"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(50_000_000)
        assert result[1] == pytest.approx(50_000_000_000)

    def test_handles_na_values(self):
        """NA values should pass through as NA."""
        budget = self._make_test_budget()
        series = pd.Series(["$50M", pd.NA, "$100M"])
        result = budget._clean_currency_column(series)

        assert result[0] == pytest.approx(50_000_000)
        assert pd.isna(result[1])
        assert result[2] == pytest.approx(100_000_000)
