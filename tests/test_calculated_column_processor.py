"""Tests for CalculatedColumnProcessor.

Tests focus on:
- Registry pattern (built-in calculations registered, unknown raises error)
- Delta calculation (current - prior, first row is NaN)
- Percent delta calculation (handles division by zero)
- Same column comparison (YoY within single column)
- Multiple calculations applied in sequence
- Error handling for missing columns
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from tpsplots.processors.calculated_column_processor import (
    CALCULATION_REGISTRY,
    CalculatedColumnConfig,
    CalculatedColumnProcessor,
)


class TestCalculationRegistry:
    """Tests for the calculation registry."""

    def test_builtin_calculations_registered(self):
        """Built-in calculations should be in the registry."""
        assert "delta_from_prior" in CALCULATION_REGISTRY
        assert "percent_delta_from_prior" in CALCULATION_REGISTRY

    def test_unknown_calculation_raises_error(self):
        """Unknown calculation should raise ValueError."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "Value": [100, 110],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Result", "nonexistent_calculation", "Value", "Value")

        processor = CalculatedColumnProcessor(config)

        with pytest.raises(ValueError, match="Unknown calculation: 'nonexistent_calculation'"):
            processor.process(df)


class TestDeltaFromPrior:
    """Tests for delta_from_prior calculation."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with fiscal year data."""
        return pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2022, 2027)],
                "PBR": [100, 110, 120, 130, 150],
                "Appropriation": [95, 105, 115, 125, 130],
            }
        )

    def test_delta_calculation_correct(self, sample_df):
        """Delta should be current - prior (shifted by 1 row)."""
        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "PBR", "Appropriation")

        processor = CalculatedColumnProcessor(config)
        result = processor.process(sample_df)

        # First row should be NaN (no prior year)
        assert pd.isna(result.loc[0, "Delta"])

        # FY2023: PBR(110) - Appropriation[FY2022](95) = 15
        assert result.loc[1, "Delta"] == 15

        # FY2024: PBR(120) - Appropriation[FY2023](105) = 15
        assert result.loc[2, "Delta"] == 15

        # FY2025: PBR(130) - Appropriation[FY2024](115) = 15
        assert result.loc[3, "Delta"] == 15

        # FY2026: PBR(150) - Appropriation[FY2025](125) = 25
        assert result.loc[4, "Delta"] == 25

    def test_delta_with_nan_in_source(self):
        """Delta should propagate NaN from source columns."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2024, 2027)],
                "PBR": [100, 110, np.nan],
                "Appropriation": [90, np.nan, 105],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "PBR", "Appropriation")

        result = CalculatedColumnProcessor(config).process(df)

        # FY2024: No prior, should be NaN
        assert pd.isna(result.loc[0, "Delta"])

        # FY2025: PBR(110) - Appropriation[FY2024](90) = 20
        assert result.loc[1, "Delta"] == 20

        # FY2026: PBR is NaN, result should be NaN
        assert pd.isna(result.loc[2, "Delta"])


class TestPercentDeltaFromPrior:
    """Tests for percent_delta_from_prior calculation."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with known values for percent calculation."""
        return pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2024, 2027)],
                "Current": [100, 125, 90],
                "Prior": [80, 100, 100],
            }
        )

    def test_percent_calculation_correct(self, sample_df):
        """Percent change should be ((current - prior) / prior) * 100."""
        config = CalculatedColumnConfig()
        config.add("Change %", "percent_delta_from_prior", "Current", "Prior")

        result = CalculatedColumnProcessor(config).process(sample_df)

        # First row: NaN (no prior year)
        assert pd.isna(result.loc[0, "Change %"])

        # FY2025: (125 - 80) / 80 * 100 = 56.25%
        assert result.loc[1, "Change %"] == pytest.approx(56.25)

        # FY2026: (90 - 100) / 100 * 100 = -10%
        assert result.loc[2, "Change %"] == pytest.approx(-10.0)

    def test_percent_division_by_zero_returns_nan(self):
        """Division by zero should return NaN, not raise error."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "Current": [100, 110],
                "Prior": [0, 100],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Change %", "percent_delta_from_prior", "Current", "Prior")

        result = CalculatedColumnProcessor(config).process(df)

        # FY2025: Prior[FY2024] is 0, should be NaN
        assert pd.isna(result.loc[1, "Change %"])

    def test_percent_with_nan_prior_returns_nan(self):
        """NaN in prior column should produce NaN result."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "Current": [100, 110],
                "Prior": [np.nan, 100],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Change %", "percent_delta_from_prior", "Current", "Prior")

        result = CalculatedColumnProcessor(config).process(df)

        # FY2025: Prior[FY2024] is NaN, should be NaN
        assert pd.isna(result.loc[1, "Change %"])


class TestSameColumnComparison:
    """Tests for comparing a column with itself (YoY growth)."""

    def test_same_column_yoy_change(self):
        """Should calculate YoY change within a single column."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2023, 2027)],
                "PBR": [100, 110, 115, 130],
            }
        )

        config = CalculatedColumnConfig()
        config.add("PBR YoY %", "percent_delta_from_prior", "PBR", "PBR")

        result = CalculatedColumnProcessor(config).process(df)

        # FY2023: No prior, NaN
        assert pd.isna(result.loc[0, "PBR YoY %"])

        # FY2024: (110 - 100) / 100 * 100 = 10%
        assert result.loc[1, "PBR YoY %"] == pytest.approx(10.0)

        # FY2025: (115 - 110) / 110 * 100 = 4.545...%
        assert result.loc[2, "PBR YoY %"] == pytest.approx(100 * 5 / 110)

        # FY2026: (130 - 115) / 115 * 100 = 13.04...%
        assert result.loc[3, "PBR YoY %"] == pytest.approx(100 * 15 / 115)


class TestMultipleCalculations:
    """Tests for applying multiple calculations."""

    def test_multiple_calculations_applied(self):
        """Config with multiple calculations should apply all."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "PBR": [100, 120],
                "Appropriation": [90, 95],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Delta $", "delta_from_prior", "PBR", "Appropriation")
        config.add("Delta %", "percent_delta_from_prior", "PBR", "Appropriation")
        config.add("PBR Growth %", "percent_delta_from_prior", "PBR", "PBR")

        result = CalculatedColumnProcessor(config).process(df)

        # All three columns should exist
        assert "Delta $" in result.columns
        assert "Delta %" in result.columns
        assert "PBR Growth %" in result.columns

        # FY2025 values:
        # Delta $: 120 - 90 = 30
        assert result.loc[1, "Delta $"] == 30

        # Delta %: (120 - 90) / 90 * 100 = 33.33...%
        assert result.loc[1, "Delta %"] == pytest.approx(100 * 30 / 90)

        # PBR Growth %: (120 - 100) / 100 * 100 = 20%
        assert result.loc[1, "PBR Growth %"] == pytest.approx(20.0)


class TestFluentAPI:
    """Tests for the fluent config API."""

    def test_add_returns_self(self):
        """add() should return self for chaining."""
        config = CalculatedColumnConfig()
        result = config.add("A", "delta_from_prior", "X", "Y")
        assert result is config

    def test_chained_adds(self):
        """Multiple add() calls can be chained."""
        config = (
            CalculatedColumnConfig()
            .add("A", "delta_from_prior", "X", "Y")
            .add("B", "percent_delta_from_prior", "X", "Y")
        )

        assert len(config.calculations) == 2
        assert config.calculations[0].output_column == "A"
        assert config.calculations[1].output_column == "B"


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_current_column_raises_error(self):
        """Missing current_fy_column should raise KeyError."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1)],
                "Appropriation": [100],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "NonExistent", "Appropriation")

        with pytest.raises(KeyError, match="Column 'NonExistent' not found"):
            CalculatedColumnProcessor(config).process(df)

    def test_missing_prior_column_raises_error(self):
        """Missing prior_fy_column should raise KeyError."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1)],
                "PBR": [100],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "PBR", "NonExistent")

        with pytest.raises(KeyError, match="Column 'NonExistent' not found"):
            CalculatedColumnProcessor(config).process(df)


class TestDataFrameOrdering:
    """Tests for DataFrame sorting behavior."""

    def test_sorts_by_fiscal_year(self):
        """Processor should sort by fiscal year before calculating."""
        # Data in reverse order
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2026, 1, 1), datetime(2025, 1, 1), datetime(2024, 1, 1)],
                "Value": [130, 120, 100],
            }
        )

        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "Value", "Value")

        result = CalculatedColumnProcessor(config).process(df)

        # After sorting: 2024, 2025, 2026
        assert result.loc[0, "Fiscal Year"] == datetime(2024, 1, 1)
        assert result.loc[1, "Fiscal Year"] == datetime(2025, 1, 1)
        assert result.loc[2, "Fiscal Year"] == datetime(2026, 1, 1)

        # Delta calculations should be correct after sorting
        assert pd.isna(result.loc[0, "Delta"])  # FY2024: no prior
        assert result.loc[1, "Delta"] == 20  # FY2025: 120 - 100
        assert result.loc[2, "Delta"] == 10  # FY2026: 130 - 120

    def test_preserves_attrs(self):
        """Processor should preserve DataFrame attrs."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "Value": [100, 110],
            }
        )
        df.attrs["test_key"] = "test_value"
        df.attrs["fiscal_year"] = 2025

        config = CalculatedColumnConfig()
        config.add("Delta", "delta_from_prior", "Value", "Value")

        result = CalculatedColumnProcessor(config).process(df)

        # Note: DataFrame.copy() preserves attrs
        assert result.attrs.get("test_key") == "test_value"
        assert result.attrs.get("fiscal_year") == 2025
