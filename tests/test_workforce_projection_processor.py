"""Tests for WorkforceProjectionProcessor.

Tests focus on:
- Config defaults (source_column, projection_column, projection_value)
- DataFrame return type with correct columns
- Projection series connects at FY-1 actual value
- Source column cleared at target FY when projection provided
- DataFrame attrs contain metadata for downstream processors
- No projection mode when projection_value is None
"""

from datetime import datetime

import pandas as pd
import pytest

from tpsplots.processors.workforce_projection_processor import (
    WorkforceProjectionConfig,
    WorkforceProjectionProcessor,
)


class TestWorkforceProjectionConfig:
    """Tests for WorkforceProjectionConfig dataclass."""

    def test_required_fiscal_year(self):
        """Config requires fiscal_year."""
        config = WorkforceProjectionConfig(fiscal_year=2026)
        assert config.fiscal_year == 2026

    def test_projection_value_defaults_to_none(self):
        """projection_value should default to None."""
        config = WorkforceProjectionConfig(fiscal_year=2026)
        assert config.projection_value is None

    def test_explicit_projection_value(self):
        """Explicit projection_value should be set."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        assert config.projection_value == 11853

    def test_default_source_column(self):
        """source_column should default to 'Full-time Equivalent (FTE)'."""
        config = WorkforceProjectionConfig(fiscal_year=2026)
        assert config.source_column == "Full-time Equivalent (FTE)"

    def test_default_projection_column(self):
        """projection_column should default to 'Workforce Projection'."""
        config = WorkforceProjectionConfig(fiscal_year=2026)
        assert config.projection_column == "Workforce Projection"

    def test_custom_source_column(self):
        """Custom source_column should override default."""
        config = WorkforceProjectionConfig(
            fiscal_year=2026,
            projection_value=11853,
            source_column="Full-time Permanent (FTP)",
        )
        assert config.source_column == "Full-time Permanent (FTP)"

    def test_custom_projection_column(self):
        """Custom projection_column should override default."""
        config = WorkforceProjectionConfig(
            fiscal_year=2026,
            projection_value=11853,
            projection_column="FY2026 Projection",
        )
        assert config.projection_column == "FY2026 Projection"


class TestWorkforceProjectionProcessor:
    """Tests for WorkforceProjectionProcessor with projection value."""

    @pytest.fixture
    def sample_workforce_df(self):
        """Create sample workforce data similar to Workforce().data().

        Contains FY1960-FY2026 to simulate historical workforce data.
        """
        years = list(range(1960, 2027))
        data = {
            "Fiscal Year": [datetime(y, 1, 1) for y in years],
            "Full-time Permanent (FTP)": [10000 + i * 100 for i in range(len(years))],
            "Full-time Equivalent (FTE)": [12000 + i * 100 for i in range(len(years))],
        }
        df = pd.DataFrame(data)
        # Set specific values for FY2025 and FY2026 to match realistic data
        df.loc[df["Fiscal Year"] == datetime(2025, 1, 1), "Full-time Equivalent (FTE)"] = 16986
        df.loc[df["Fiscal Year"] == datetime(2026, 1, 1), "Full-time Equivalent (FTE)"] = 13738
        return df

    def test_returns_dataframe(self, sample_workforce_df):
        """Processor should return a DataFrame."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_required_columns(self, sample_workforce_df):
        """Returned DataFrame should have expected columns."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert "Fiscal Year" in result.columns
        assert "Full-time Equivalent (FTE)" in result.columns
        assert "Workforce Projection" in result.columns

    def test_dataframe_attrs_contain_metadata(self, sample_workforce_df):
        """DataFrame attrs should contain config metadata for downstream processors."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert result.attrs["fiscal_year"] == 2026
        assert result.attrs["projection_value"] == 11853

    def test_dataframe_attrs_contain_xlim(self, sample_workforce_df):
        """DataFrame attrs should contain xlim for chart rendering."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        xlim = result.attrs["xlim"]
        assert xlim == (datetime(1958, 1, 1), datetime(2027, 1, 1))

    def test_dataframe_attrs_contain_ylim(self, sample_workforce_df):
        """DataFrame attrs should contain ylim for chart rendering."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        ylim = result.attrs["ylim"]
        assert ylim == {"bottom": 0, "top": 40_000}

    def test_projection_value_at_target_fy(self, sample_workforce_df):
        """Projection should show config value at target fiscal year."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        assert fy2026_mask.any(), "FY2026 row should exist"
        projection_value = result.loc[fy2026_mask, "Workforce Projection"].values[0]
        assert projection_value == 11853

    def test_source_column_cleared_at_target_fy(self, sample_workforce_df):
        """Source column should be NaN at target FY when projection is set."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        fte_value = result.loc[fy2026_mask, "Full-time Equivalent (FTE)"].values[0]
        assert pd.isna(fte_value), "FTE should be NaN at target FY when projection is set"

    def test_source_column_preserved_at_prior_years(self, sample_workforce_df):
        """Source column should be preserved for years before target FY."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        # FY2025 should still have FTE value
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        fte_value = result.loc[fy2025_mask, "Full-time Equivalent (FTE)"].values[0]
        assert fte_value == 16986

    def test_projection_connects_at_fy_minus_one(self, sample_workforce_df):
        """Projection should connect to FY-1 actual value for clean plotting."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        # FY2025 projection should equal FY2025 FTE (connection point)
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        fy2025_projection = result.loc[fy2025_mask, "Workforce Projection"].values[0]
        fy2025_fte = result.loc[fy2025_mask, "Full-time Equivalent (FTE)"].values[0]

        assert fy2025_projection == fy2025_fte
        assert fy2025_projection == 16986

    def test_projection_nan_for_historical_years(self, sample_workforce_df):
        """Projection should be NaN for years before FY-1."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        # Check that projection is NaN for years before FY2025
        historical_mask = result["Fiscal Year"] < datetime(2025, 1, 1)
        historical_projections = result.loc[historical_mask, "Workforce Projection"]

        assert historical_projections.isna().all()

    def test_filters_data_to_target_fy(self, sample_workforce_df):
        """Data should be filtered to include only years through target FY."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        max_fy = result["Fiscal Year"].max()
        assert max_fy == datetime(2026, 1, 1)

    def test_different_fiscal_year(self, sample_workforce_df):
        """Processor should work with different fiscal years."""
        config = WorkforceProjectionConfig(fiscal_year=2025, projection_value=15000)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        # Check FY2025 has projection value
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        projection = result.loc[fy2025_mask, "Workforce Projection"].values[0]
        assert projection == 15000

        # Check FY2024 is connection point
        fy2024_mask = result["Fiscal Year"] == datetime(2024, 1, 1)
        fy2024_projection = result.loc[fy2024_mask, "Workforce Projection"].values[0]
        fy2024_fte = result.loc[fy2024_mask, "Full-time Equivalent (FTE)"].values[0]
        assert fy2024_projection == fy2024_fte

        # Check xlim updated
        assert result.attrs["xlim"] == (datetime(1958, 1, 1), datetime(2026, 1, 1))

    def test_preserves_original_columns(self, sample_workforce_df):
        """Processor should preserve all original columns."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert "Full-time Permanent (FTP)" in result.columns
        assert "Full-time Equivalent (FTE)" in result.columns

    def test_does_not_modify_input_dataframe(self, sample_workforce_df):
        """Processor should not modify the input DataFrame."""
        original_len = len(sample_workforce_df)
        original_columns = list(sample_workforce_df.columns)
        # Store original FY2026 FTE value
        original_fy2026_fte = sample_workforce_df.loc[
            sample_workforce_df["Fiscal Year"] == datetime(2026, 1, 1),
            "Full-time Equivalent (FTE)",
        ].values[0]

        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        processor.process(sample_workforce_df)

        assert len(sample_workforce_df) == original_len
        assert list(sample_workforce_df.columns) == original_columns
        assert "Workforce Projection" not in sample_workforce_df.columns
        # Original FY2026 FTE should be unchanged
        current_fy2026_fte = sample_workforce_df.loc[
            sample_workforce_df["Fiscal Year"] == datetime(2026, 1, 1),
            "Full-time Equivalent (FTE)",
        ].values[0]
        assert current_fy2026_fte == original_fy2026_fte


class TestWorkforceProjectionNoProjection:
    """Tests for processor behavior when projection_value is None."""

    @pytest.fixture
    def sample_workforce_df(self):
        """Create sample workforce data."""
        years = list(range(2020, 2027))
        data = {
            "Fiscal Year": [datetime(y, 1, 1) for y in years],
            "Full-time Equivalent (FTE)": [17000 + i * 100 for i in range(len(years))],
        }
        df = pd.DataFrame(data)
        df.loc[df["Fiscal Year"] == datetime(2026, 1, 1), "Full-time Equivalent (FTE)"] = 13738
        return df

    def test_no_projection_column_when_value_is_none(self, sample_workforce_df):
        """Should not add projection column when projection_value is None."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=None)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert "Workforce Projection" not in result.columns

    def test_source_column_preserved_when_no_projection(self, sample_workforce_df):
        """Source column should be preserved at target FY when no projection."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=None)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        fte_value = result.loc[fy2026_mask, "Full-time Equivalent (FTE)"].values[0]
        assert fte_value == 13738, "FTE should be preserved when no projection"

    def test_attrs_without_projection_value(self, sample_workforce_df):
        """DataFrame attrs should not contain projection_value when None."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=None)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert result.attrs["fiscal_year"] == 2026
        assert "projection_value" not in result.attrs

    def test_xlim_and_ylim_present_without_projection(self, sample_workforce_df):
        """xlim and ylim should still be set even without projection."""
        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=None)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        assert result.attrs["xlim"] == (datetime(1958, 1, 1), datetime(2027, 1, 1))
        assert result.attrs["ylim"] == {"bottom": 0, "top": 40_000}

    def test_filters_data_without_projection(self, sample_workforce_df):
        """Data should still be filtered to target FY without projection."""
        config = WorkforceProjectionConfig(fiscal_year=2025, projection_value=None)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(sample_workforce_df)

        max_fy = result["Fiscal Year"].max()
        assert max_fy == datetime(2025, 1, 1)


class TestWorkforceProjectionEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_source_column(self):
        """Should handle missing source column gracefully."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1), datetime(2026, 1, 1)],
                "Other Column": [100, 200],
            }
        )

        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(df)

        # Projection should still work, just won't have connection point
        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        projection = result.loc[fy2026_mask, "Workforce Projection"].values[0]
        assert projection == 11853

    def test_missing_prior_year(self):
        """Should handle missing FY-1 data gracefully."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2026, 1, 1)],
                "Full-time Equivalent (FTE)": [13738],
            }
        )

        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(df)

        # Should still set projection at target FY
        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        projection = result.loc[fy2026_mask, "Workforce Projection"].values[0]
        assert projection == 11853

    def test_target_fy_not_in_data(self):
        """Should handle case where target FY is not in input data."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1), datetime(2025, 1, 1)],
                "Full-time Equivalent (FTE)": [17738, 16986],
            }
        )

        config = WorkforceProjectionConfig(fiscal_year=2026, projection_value=11853)
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(df)

        # FY2026 won't be in result since it wasn't in input and processor filters
        max_fy = result["Fiscal Year"].max()
        assert max_fy == datetime(2025, 1, 1)

        # But FY2025 should have connection point set
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        projection = result.loc[fy2025_mask, "Workforce Projection"].values[0]
        assert projection == 16986

    def test_custom_projection_column_name(self):
        """Should use custom projection column name."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1), datetime(2026, 1, 1)],
                "Full-time Equivalent (FTE)": [16986, 13738],
            }
        )

        config = WorkforceProjectionConfig(
            fiscal_year=2026,
            projection_value=11853,
            projection_column="Custom Projection",
        )
        processor = WorkforceProjectionProcessor(config)

        result = processor.process(df)

        assert "Custom Projection" in result.columns
        assert "Workforce Projection" not in result.columns
