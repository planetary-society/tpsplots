"""Tests for AwardDataProcessor."""

import pandas as pd
import pytest

from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig


class TestFiscalYearConfig:
    """Tests for FiscalYearConfig helpers."""

    def test_default_comparison_year(self):
        """comparison_year should default to last prior year."""
        config = FiscalYearConfig(prior_years=[2022, 2023, 2024], current_year=2025)
        assert config.comparison_year == 2024

    def test_all_years_property(self):
        """all_years should include prior years and current year."""
        config = FiscalYearConfig(prior_years=[2023, 2024], current_year=2025)
        assert config.all_years == [2023, 2024, 2025]

    def test_prior_year_range_label(self):
        """prior_year_range_label should format ranges correctly."""
        config = FiscalYearConfig(prior_years=[2020, 2021, 2022], current_year=2023)
        assert config.prior_year_range_label == "2020-22"


class TestAwardDataProcessor:
    """Tests for AwardDataProcessor core behavior."""

    @pytest.fixture
    def award_df(self):
        """Create sample award data with a Total row."""
        months = AwardDataProcessor.MONTHS + ["Total"]
        data = {
            "Month": months,
            "FY 2024 New Grant Awards": [10] * 12 + [120],
            "FY 2025 New Grant Awards": [20] * 12 + [240],
            "FY 2026 New Grant Awards": [5] * 12 + [60],
        }
        return pd.DataFrame(data)

    def test_process_builds_series_and_metadata(self, award_df):
        """Processor should build series, labels, and metadata attrs."""
        config = FiscalYearConfig(prior_years=[2024, 2025], current_year=2026)
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(award_df)

        assert export_df["Month"].tolist() == AwardDataProcessor.MONTHS
        assert export_df.attrs["months"] == AwardDataProcessor.MONTHS
        assert export_df.attrs["series_types"] == ["prior", "prior", "average", "current"]

        labels = export_df.attrs["labels"]
        assert labels[0] is None
        assert labels[1] is None
        assert labels[2] == "2024-25\nAverage"
        assert labels[3] == "FY 2026"

        # Export includes only labeled series
        assert "2024-25\nAverage Cumulative" in export_df.columns
        assert "FY 2026 Cumulative" in export_df.columns

    def test_average_series_values(self, award_df):
        """Average series should be mean of prior year cumulative totals."""
        config = FiscalYearConfig(prior_years=[2024, 2025], current_year=2026)
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(award_df)

        avg_series = export_df["2024-25\nAverage Cumulative"].tolist()
        assert avg_series[0] == 15
        assert avg_series[1] == 30
        assert avg_series[-1] == 180

    def test_current_year_padding(self, award_df):
        """Current year series should be padded with None for incomplete months."""
        config = FiscalYearConfig(prior_years=[2024, 2025], current_year=2026)
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(award_df)

        current_series = export_df["FY 2026 Cumulative"].tolist()
        assert current_series[5] == 30
        assert pd.isna(current_series[6])
        assert pd.isna(current_series[-1])

    def test_shortfall_projection(self, award_df):
        """Projected shortfall should be computed against comparison year."""
        config = FiscalYearConfig(prior_years=[2024, 2025], current_year=2026)
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(award_df)

        assert export_df.attrs["shortfall_pct"] == pytest.approx(75.0)

    def test_missing_current_year_column(self, award_df):
        """If current year column is missing, no current series is added."""
        df = award_df.drop(columns=["FY 2026 New Grant Awards"])
        config = FiscalYearConfig(prior_years=[2024, 2025], current_year=2026)
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(df)

        assert export_df.attrs["series_types"] == ["prior", "prior", "average"]
        assert "FY 2026 Cumulative" not in export_df.columns
        assert export_df.attrs["shortfall_pct"] == 0

    def test_missing_comparison_year(self, award_df):
        """Shortfall should be 0 when comparison year data is unavailable."""
        config = FiscalYearConfig(
            prior_years=[2024, 2025],
            current_year=2026,
            comparison_year=2023,
        )
        processor = AwardDataProcessor(config, current_month_override=6)

        export_df = processor.process(award_df)

        assert export_df.attrs["shortfall_pct"] == 0
