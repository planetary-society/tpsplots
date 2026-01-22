"""Tests for InflationAdjustmentProcessor.

Tests focus on:
- Config defaults (target_year auto-calculates to prior FY)
- Prior FY calculation based on current date
- NNSI processing creates correct columns
- GDP processing creates correct columns
- Combined NNSI + GDP processing
- DataFrame attrs contain metadata
- Edge cases (missing columns, NaN values)
"""

from datetime import datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from tpsplots.processors.inflation_adjustment_processor import (
    InflationAdjustmentConfig,
    InflationAdjustmentProcessor,
    _calculate_prior_fy,
)


class TestCalculatePriorFY:
    """Tests for _calculate_prior_fy function."""

    def test_january_returns_prior_calendar_year(self):
        """In Jan-Sep, current FY = current year, prior FY = current year - 1."""
        # January 15, 2026 -> current FY = 2026, prior FY = 2025
        with patch("tpsplots.processors.inflation_adjustment_processor.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15)
            assert _calculate_prior_fy() == 2025

    def test_september_returns_prior_calendar_year(self):
        """In Sep, current FY = current year, prior FY = current year - 1."""
        # September 30, 2026 -> current FY = 2026, prior FY = 2025
        with patch("tpsplots.processors.inflation_adjustment_processor.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 30)
            assert _calculate_prior_fy() == 2025

    def test_october_returns_current_calendar_year(self):
        """In Oct-Dec, current FY = current year + 1, prior FY = current year."""
        # October 1, 2026 -> current FY = 2027, prior FY = 2026
        with patch("tpsplots.processors.inflation_adjustment_processor.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 10, 1)
            assert _calculate_prior_fy() == 2026

    def test_december_returns_current_calendar_year(self):
        """In Dec, current FY = current year + 1, prior FY = current year."""
        # December 15, 2026 -> current FY = 2027, prior FY = 2026
        with patch("tpsplots.processors.inflation_adjustment_processor.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 15)
            assert _calculate_prior_fy() == 2026


class TestInflationAdjustmentConfig:
    """Tests for InflationAdjustmentConfig dataclass."""

    def test_target_year_defaults_to_prior_fy(self):
        """target_year should auto-calculate to prior FY when None."""
        with patch(
            "tpsplots.processors.inflation_adjustment_processor._calculate_prior_fy",
            return_value=2025,
        ):
            config = InflationAdjustmentConfig()
            assert config.target_year == 2025

    def test_explicit_target_year_overrides_default(self):
        """Explicit target_year should override the auto-calculation."""
        config = InflationAdjustmentConfig(target_year=2024)
        assert config.target_year == 2024

    def test_fiscal_year_column_default(self):
        """fiscal_year_column should default to 'Fiscal Year'."""
        config = InflationAdjustmentConfig(target_year=2025)
        assert config.fiscal_year_column == "Fiscal Year"

    def test_nnsi_columns_default_to_empty_list(self):
        """nnsi_columns should default to empty list after __post_init__."""
        config = InflationAdjustmentConfig(target_year=2025)
        assert config.nnsi_columns == []

    def test_gdp_columns_default_to_empty_list(self):
        """gdp_columns should default to empty list after __post_init__."""
        config = InflationAdjustmentConfig(target_year=2025)
        assert config.gdp_columns == []

    def test_nnsi_columns_preserved_when_specified(self):
        """Specified nnsi_columns should be preserved."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR", "Appropriation"])
        assert config.nnsi_columns == ["PBR", "Appropriation"]

    def test_gdp_columns_preserved_when_specified(self):
        """Specified gdp_columns should be preserved."""
        config = InflationAdjustmentConfig(target_year=2025, gdp_columns=["Budget", "Spending"])
        assert config.gdp_columns == ["Budget", "Spending"]


class TestInflationAdjustmentProcessor:
    """Tests for InflationAdjustmentProcessor."""

    @pytest.fixture
    def mock_nnsi(self):
        """Mock NNSI to avoid network calls and return predictable multipliers."""
        # Returns 1.1x multiplier for all years (10% inflation adjustment)
        mock_table = {str(y): 1.1 for y in range(2015, 2031)}
        with patch(
            "tpsplots.processors.inflation_adjustment_processor.NNSI._load_table",
            return_value=mock_table,
        ):
            yield

    @pytest.fixture
    def mock_gdp(self):
        """Mock GDP to avoid network calls and return predictable multipliers."""
        # Returns 1.2x multiplier for all years (20% inflation adjustment)
        mock_table = {str(y): 1.2 for y in range(2015, 2031)}
        with patch(
            "tpsplots.processors.inflation_adjustment_processor.GDP._load_table",
            return_value=mock_table,
        ):
            yield

    @pytest.fixture
    def mock_both_adjusters(self, mock_nnsi, mock_gdp):
        """Mock both NNSI and GDP."""
        yield

    @pytest.fixture
    def sample_df(self):
        """Create sample budget data with fiscal years and monetary columns."""
        data = {
            "Fiscal Year": [datetime(y, 1, 1) for y in range(2020, 2026)],
            "PBR": [
                22_000_000_000.0,
                23_000_000_000.0,
                24_000_000_000.0,
                25_000_000_000.0,
                26_000_000_000.0,
                27_000_000_000.0,
            ],
            "Appropriation": [
                21_000_000_000.0,
                22_000_000_000.0,
                23_000_000_000.0,
                24_000_000_000.0,
                25_000_000_000.0,
                np.nan,  # FY2025 not yet appropriated
            ],
        }
        return pd.DataFrame(data)

    def test_returns_dataframe(self, mock_nnsi, sample_df):
        """Processor should return a DataFrame."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert isinstance(result, pd.DataFrame)

    def test_does_not_modify_original(self, mock_nnsi, sample_df):
        """Processor should not modify the original DataFrame."""
        original_columns = list(sample_df.columns)
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        processor.process(sample_df)

        assert list(sample_df.columns) == original_columns

    def test_nnsi_creates_adjusted_column(self, mock_nnsi, sample_df):
        """NNSI processing should create {col}_adjusted_nnsi column."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert "PBR_adjusted_nnsi" in result.columns

    def test_nnsi_applies_multiplier(self, mock_nnsi, sample_df):
        """NNSI adjusted values should apply the inflation multiplier."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        # Mock returns 1.1x multiplier
        expected_first = 22_000_000_000.0 * 1.1
        assert result["PBR_adjusted_nnsi"].iloc[0] == pytest.approx(expected_first)

    def test_nnsi_multiple_columns(self, mock_nnsi, sample_df):
        """NNSI should process multiple columns."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR", "Appropriation"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert "PBR_adjusted_nnsi" in result.columns
        assert "Appropriation_adjusted_nnsi" in result.columns

    def test_nnsi_handles_nan_values(self, mock_nnsi, sample_df):
        """NaN values in original column should produce NaN in adjusted column."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["Appropriation"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        # FY2025 Appropriation is NaN
        assert pd.isna(result["Appropriation_adjusted_nnsi"].iloc[-1])

    def test_nnsi_skips_missing_column(self, mock_nnsi, sample_df):
        """Missing columns should be silently skipped (no error)."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR", "NonExistent"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert "PBR_adjusted_nnsi" in result.columns
        assert "NonExistent_adjusted_nnsi" not in result.columns

    def test_gdp_creates_adjusted_column(self, mock_gdp, sample_df):
        """GDP processing should create {col}_adjusted_gdp column."""
        config = InflationAdjustmentConfig(target_year=2025, gdp_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert "PBR_adjusted_gdp" in result.columns

    def test_gdp_applies_multiplier(self, mock_gdp, sample_df):
        """GDP adjusted values should apply the inflation multiplier."""
        config = InflationAdjustmentConfig(target_year=2025, gdp_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        # Mock returns 1.2x multiplier
        expected_first = 22_000_000_000.0 * 1.2
        assert result["PBR_adjusted_gdp"].iloc[0] == pytest.approx(expected_first)

    def test_combined_nnsi_and_gdp(self, mock_both_adjusters, sample_df):
        """Both NNSI and GDP adjustments should work together."""
        config = InflationAdjustmentConfig(
            target_year=2025,
            nnsi_columns=["PBR", "Appropriation"],
            gdp_columns=["PBR", "Appropriation"],
        )
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        # Should have 4 new columns (2 NNSI + 2 GDP)
        assert "PBR_adjusted_nnsi" in result.columns
        assert "Appropriation_adjusted_nnsi" in result.columns
        assert "PBR_adjusted_gdp" in result.columns
        assert "Appropriation_adjusted_gdp" in result.columns

    def test_combined_different_columns(self, mock_both_adjusters, sample_df):
        """NNSI and GDP can apply to different column sets."""
        config = InflationAdjustmentConfig(
            target_year=2025,
            nnsi_columns=["PBR"],
            gdp_columns=["Appropriation"],
        )
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert "PBR_adjusted_nnsi" in result.columns
        assert "PBR_adjusted_gdp" not in result.columns
        assert "Appropriation_adjusted_gdp" in result.columns
        assert "Appropriation_adjusted_nnsi" not in result.columns

    def test_attrs_contains_target_year(self, mock_nnsi, sample_df):
        """DataFrame attrs should contain inflation_target_year."""
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert result.attrs["inflation_target_year"] == 2025

    def test_empty_config_produces_no_new_columns(self, sample_df):
        """Config with no columns should produce no new columns."""
        config = InflationAdjustmentConfig(target_year=2025)
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        # Should have same columns as input (plus attrs)
        assert list(result.columns) == list(sample_df.columns)
        assert result.attrs["inflation_target_year"] == 2025

    def test_default_config_no_adjusters_loaded(self):
        """Empty config should not load NNSI or GDP adjusters."""
        config = InflationAdjustmentConfig(target_year=2025)
        processor = InflationAdjustmentProcessor(config)

        assert processor._nnsi is None
        assert processor._gdp is None

    def test_preserves_original_columns(self, mock_nnsi, sample_df):
        """Original columns should be unchanged."""
        original_pbr = sample_df["PBR"].tolist()
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["PBR"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(sample_df)

        assert result["PBR"].tolist() == original_pbr


class TestInflationAdjustmentWithIntegerYears:
    """Tests for handling integer fiscal year values."""

    @pytest.fixture
    def mock_nnsi(self):
        """Mock NNSI to avoid network calls and return predictable multipliers."""
        mock_table = {str(y): 1.1 for y in range(2015, 2031)}
        with patch(
            "tpsplots.processors.inflation_adjustment_processor.NNSI._load_table",
            return_value=mock_table,
        ):
            yield

    def test_handles_integer_fiscal_years(self, mock_nnsi):
        """Processor should work with integer fiscal year values.

        This test verifies the processor works with integer fiscal year
        values (as opposed to datetime) and creates the adjusted column.
        """
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022],
                "Budget": [100.0, 110.0, 120.0],
            }
        )
        config = InflationAdjustmentConfig(target_year=2025, nnsi_columns=["Budget"])
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(df)

        # Verify the adjusted column was created
        assert "Budget_adjusted_nnsi" in result.columns
        # Verify it contains numeric values (not NaN for all)
        assert not result["Budget_adjusted_nnsi"].isna().all()
        # Verify original values are preserved
        assert result["Budget"].tolist() == [100.0, 110.0, 120.0]


class TestInflationAdjustmentCustomFYColumn:
    """Tests for custom fiscal year column name."""

    @pytest.fixture
    def mock_nnsi(self):
        """Mock NNSI."""
        mock_table = {str(y): 1.1 for y in range(2015, 2031)}
        with patch(
            "tpsplots.processors.inflation_adjustment_processor.NNSI._load_table",
            return_value=mock_table,
        ):
            yield

    def test_custom_fiscal_year_column(self, mock_nnsi):
        """Processor should use custom fiscal_year_column."""
        df = pd.DataFrame(
            {
                "Year": [datetime(2020, 1, 1), datetime(2021, 1, 1)],
                "Amount": [100.0, 110.0],
            }
        )
        config = InflationAdjustmentConfig(
            target_year=2025, nnsi_columns=["Amount"], fiscal_year_column="Year"
        )
        processor = InflationAdjustmentProcessor(config)

        result = processor.process(df)

        assert "Amount_adjusted_nnsi" in result.columns
