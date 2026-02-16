"""Tests for BudgetProjectionProcessor.

Tests focus on:
- Config defaults (inflation_target = FY-1)
- Column name patterns (pbr_request_column, runout_columns)
- DataFrame return type with correct columns
- Projection series connects at FY-1 appropriation
- DataFrame attrs contain metadata for downstream processors

Note: BudgetProjectionProcessor does NOT apply inflation adjustment.
Use InflationAdjustmentProcessor explicitly in controllers for that.
"""

from datetime import datetime

import pandas as pd
import pytest

from tpsplots.processors.budget_projection_processor import (
    BudgetProjectionConfig,
    BudgetProjectionProcessor,
)


class TestBudgetProjectionConfig:
    """Tests for BudgetProjectionConfig dataclass."""

    def test_default_inflation_target_is_fy_minus_one(self):
        """Inflation target year should default to fiscal_year - 1."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        assert config.inflation_target_year == 2025

    def test_explicit_inflation_target_overrides_default(self):
        """Explicit inflation_target_year should override the default."""
        config = BudgetProjectionConfig(fiscal_year=2026, inflation_target_year=2024)
        assert config.inflation_target_year == 2024

    def test_pbr_request_column_pattern(self):
        """pbr_request_column should follow 'FY {year} Request' pattern."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        assert config.pbr_request_column == "FY 2026 Request"

        config2 = BudgetProjectionConfig(fiscal_year=2027)
        assert config2.pbr_request_column == "FY 2027 Request"

    def test_runout_columns_default_four_years(self):
        """runout_columns should return 4 years by default."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        assert config.runout_columns == ["FY 2027", "FY 2028", "FY 2029", "FY 2030"]

    def test_runout_columns_custom_years(self):
        """runout_columns should respect custom runout_years."""
        config = BudgetProjectionConfig(fiscal_year=2026, runout_years=2)
        assert config.runout_columns == ["FY 2027", "FY 2028"]

    def test_default_budget_detail_row_name(self):
        """budget_detail_row_name should default to 'Total'."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        assert config.budget_detail_row_name == "Total"

    def test_default_column_names(self):
        """Default column names should match top-line Historical data."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        assert config.appropriation_column == "Appropriation"
        assert config.pbr_column == "PBR"


class TestBudgetProjectionProcessor:
    """Tests for BudgetProjectionProcessor."""

    @pytest.fixture
    def sample_historical_df(self):
        """Create sample historical data similar to Historical().data().

        Note: For fiscal_year=2026 tests, FY2025 must have appropriation value
        since it's the prior year with actual enacted budget.
        """
        data = {
            # FY2020 through FY2025 (FY2026 will be added by processor)
            "Fiscal Year": [datetime(y, 1, 1) for y in range(2020, 2026)],
            "Presidential Administration": [
                "Trump",
                "Trump",
                "Biden",
                "Biden",
                "Biden",
                "Biden",
            ],
            "PBR": [
                22_629_000_000,  # FY2020
                25_246_000_000,  # FY2021
                24_800_000_000,  # FY2022
                26_000_000_000,  # FY2023
                27_200_000_000,  # FY2024
                25_400_000_000,  # FY2025 (prior year PBR)
            ],
            "Appropriation": [
                22_629_000_000,  # FY2020
                23_271_000_000,  # FY2021
                24_041_000_000,  # FY2022
                25_384_000_000,  # FY2023
                24_500_000_000,  # FY2024
                24_875_000_000,  # FY2025 (prior year appropriation)
            ],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def sample_budget_detail_df(self):
        """Create sample budget detail data similar to GoogleSheetsSource data."""
        data = {
            "Account": ["Total", "Science", "Exploration"],
            "FY 2026 Request": [25_000_000_000, 7_300_000_000, 8_500_000_000],
            "FY 2027": [25_500_000_000, 7_400_000_000, 8_600_000_000],
            "FY 2028": [26_000_000_000, 7_500_000_000, 8_700_000_000],
            "FY 2029": [26_500_000_000, 7_600_000_000, 8_800_000_000],
            "FY 2030": [27_000_000_000, 7_700_000_000, 8_900_000_000],
        }
        return pd.DataFrame(data)

    def test_returns_dataframe(self, sample_historical_df, sample_budget_detail_df):
        """Processor should return a DataFrame."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_required_columns(self, sample_historical_df, sample_budget_detail_df):
        """Returned DataFrame should have expected columns.

        Note: Adjusted columns (PBR_adjusted_nnsi, etc.) are NOT created by
        BudgetProjectionProcessor. Use InflationAdjustmentProcessor for that.
        """
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        assert "Fiscal Year" in result.columns
        assert "PBR" in result.columns
        assert "Appropriation" in result.columns
        assert "White House Budget Projection" in result.columns

    def test_dataframe_attrs_contain_metadata(self, sample_historical_df, sample_budget_detail_df):
        """DataFrame attrs should contain config metadata for downstream processors."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        assert result.attrs["fiscal_year"] == 2026
        assert result.attrs["inflation_target_year"] == 2025
        assert result.attrs["pbr_column"] == "PBR"
        assert result.attrs["appropriation_column"] == "Appropriation"
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_pbr_value_grafted_at_current_fy(self, sample_historical_df, sample_budget_detail_df):
        """PBR value should be grafted onto current FY row."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        assert fy2026_mask.any(), "FY2026 row should exist"
        assert result.loc[fy2026_mask, "PBR"].values[0] == 25_000_000_000

    def test_extract_science_pbr_value(self, sample_historical_df, sample_budget_detail_df):
        """Processor should extract PBR for Science directorate."""
        config = BudgetProjectionConfig(
            fiscal_year=2026,
            budget_detail_row_name="Science",
            appropriation_column="Appropriation",  # Would use "Science" in real usage
            pbr_column="PBR",
        )
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        # Should extract Science row value
        assert result.attrs["current_pbr_request"] == 7_300_000_000

    def test_projection_connects_at_fy_minus_one(
        self, sample_historical_df, sample_budget_detail_df
    ):
        """White House Projection should connect to FY-1 appropriation."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        # Find FY2025 (prior year) projection value
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        fy2025_projection = result.loc[fy2025_mask, "White House Budget Projection"].values[0]

        # Should equal FY2025 appropriation (connection point)
        assert fy2025_projection == 24_875_000_000

    def test_projection_shows_pbr_at_current_fy(
        self, sample_historical_df, sample_budget_detail_df
    ):
        """White House Projection should show PBR at current FY."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        # Find FY2026 projection value
        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        fy2026_projection = result.loc[fy2026_mask, "White House Budget Projection"].values[0]

        # Should equal PBR request
        assert fy2026_projection == 25_000_000_000

    def test_projection_includes_runout_years(self, sample_historical_df, sample_budget_detail_df):
        """White House Projection should include runout year values."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        # Check runout years
        for runout_year, expected_value in [
            (2027, 25_500_000_000),
            (2028, 26_000_000_000),
            (2029, 26_500_000_000),
            (2030, 27_000_000_000),
        ]:
            fy_mask = result["Fiscal Year"] == datetime(runout_year, 1, 1)
            assert fy_mask.any(), f"FY{runout_year} should be in output"
            runout_value = result.loc[fy_mask, "White House Budget Projection"].values[0]
            assert runout_value == expected_value, f"FY{runout_year} runout mismatch"

    def test_appropriation_cleared_for_current_and_future_fy(
        self, sample_historical_df, sample_budget_detail_df
    ):
        """Appropriation should be NaN for FY >= current FY."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        # FY2025 should have appropriation
        fy2025_mask = result["Fiscal Year"] == datetime(2025, 1, 1)
        assert not pd.isna(result.loc[fy2025_mask, "Appropriation"].values[0])

        # FY2026+ should have NaN appropriation
        fy2026_mask = result["Fiscal Year"] == datetime(2026, 1, 1)
        assert pd.isna(result.loc[fy2026_mask, "Appropriation"].values[0])

    def test_max_fiscal_year_in_dataframe(self, sample_historical_df, sample_budget_detail_df):
        """DataFrame should extend to final runout year."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        result = processor.process(sample_historical_df, sample_budget_detail_df)

        max_fy = int(result["Fiscal Year"].max().strftime("%Y"))
        assert max_fy == 2030

    def test_missing_budget_detail_row_raises_error(
        self, sample_historical_df, sample_budget_detail_df
    ):
        """Should raise ValueError if budget_detail_row_name not found."""
        config = BudgetProjectionConfig(fiscal_year=2026, budget_detail_row_name="NonExistent")
        processor = BudgetProjectionProcessor(config)

        with pytest.raises(ValueError, match="No 'NonExistent' row found"):
            processor.process(sample_historical_df, sample_budget_detail_df)

    def test_missing_pbr_column_raises_error(self, sample_historical_df):
        """Should raise ValueError if PBR request column not found."""
        # Budget detail without the expected FY 2026 Request column
        bad_budget_detail = pd.DataFrame(
            {"Account": ["Total"], "FY 2025 Request": [24_000_000_000]}
        )

        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)

        with pytest.raises(ValueError, match="Column 'FY 2026 Request' not found"):
            processor.process(sample_historical_df, bad_budget_detail)


class TestBudgetDetailRowLookup:
    """Tests for case-insensitive and alias row matching in _find_detail_row."""

    @pytest.fixture
    def historical_df(self):
        """Minimal historical data for row lookup tests."""
        return pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1)],
                "PBR": [25_000_000_000],
                "Appropriation": [24_875_000_000],
            }
        )

    def _make_budget_detail(self, row_label):
        """Helper to create budget detail with a single row."""
        return pd.DataFrame(
            {
                "Account": [row_label],
                "FY 2026 Request": [25_000_000_000],
                "FY 2027": [25_500_000_000],
            }
        )

    def test_exact_match(self, historical_df):
        """Exact case match should work as before."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("Total"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_case_insensitive_lowercase(self, historical_df):
        """Lowercase 'total' should match config's 'Total'."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("total"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_case_insensitive_uppercase(self, historical_df):
        """Uppercase 'TOTAL' should match config's 'Total'."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("TOTAL"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_alias_nasa_total(self, historical_df):
        """'NASA Total' should match config's 'Total' via alias."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("NASA Total"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_alias_case_insensitive(self, historical_df):
        """'nasa total' (all lowercase) should match via alias + case folding."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("nasa total"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_whitespace_stripping(self, historical_df):
        """Leading/trailing whitespace should be stripped before comparison."""
        config = BudgetProjectionConfig(fiscal_year=2026)
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("  Total  "))
        assert result.attrs["current_pbr_request"] == 25_000_000_000

    def test_no_match_raises_with_available_rows(self, historical_df):
        """Should raise ValueError listing available rows when no match."""
        budget_detail = pd.DataFrame(
            {
                "Account": ["Exploration", "Science"],
                "FY 2026 Request": [8_500_000_000, 7_300_000_000],
            }
        )
        config = BudgetProjectionConfig(fiscal_year=2026, budget_detail_row_name="Total")
        processor = BudgetProjectionProcessor(config)
        with pytest.raises(ValueError, match="Available rows"):
            processor.process(historical_df, budget_detail)

    def test_science_case_insensitive(self, historical_df):
        """'SCIENCE' should match config's 'Science'."""
        config = BudgetProjectionConfig(
            fiscal_year=2026,
            budget_detail_row_name="Science",
        )
        processor = BudgetProjectionProcessor(config)
        result = processor.process(historical_df, self._make_budget_detail("SCIENCE"))
        assert result.attrs["current_pbr_request"] == 25_000_000_000


class TestDirectorateLevelConfig:
    """Tests for directorate-level (e.g., Science) configuration."""

    def test_science_config_pattern(self):
        """Config for Science directorate should use correct columns."""
        config = BudgetProjectionConfig(
            fiscal_year=2026,
            budget_detail_row_name="Science",
            appropriation_column="Science",
            pbr_column="Science",
        )

        assert config.budget_detail_row_name == "Science"
        assert config.appropriation_column == "Science"
        assert config.pbr_request_column == "FY 2026 Request"


class TestPriorEnactedColumnDetection:
    """Tests for tolerant prior-year enacted column name matching.

    Verifies the candidate-list pattern used in
    nasa_fy_charts_controller.directorates_comparison_grouped.
    """

    def _find_prior_enacted(self, columns, fiscal_year=2026):
        """Simulate the candidate search logic from the controller."""
        prior_fy = fiscal_year - 1
        candidates = [
            f"FY {prior_fy} Enacted",
            f"FY {prior_fy}",
            f"FY{prior_fy} Enacted",
            f"FY{prior_fy}",
        ]
        return next((c for c in candidates if c in columns), None)

    def test_fy_space_enacted(self):
        """'FY 2025 Enacted' (standard format) should match."""
        assert self._find_prior_enacted(["FY 2025 Enacted", "FY 2026 Request"]) == "FY 2025 Enacted"

    def test_fy_space_only(self):
        """'FY 2025' (without Enacted) should match as fallback."""
        assert self._find_prior_enacted(["FY 2025", "FY 2026 Request"]) == "FY 2025"

    def test_fy_nospace_enacted(self):
        """'FY2025 Enacted' (no space) should match."""
        assert self._find_prior_enacted(["FY2025 Enacted", "FY 2026 Request"]) == "FY2025 Enacted"

    def test_fy_nospace_only(self):
        """'FY2025' (no space, no Enacted) should match."""
        assert self._find_prior_enacted(["FY2025", "FY 2026 Request"]) == "FY2025"

    def test_no_match_returns_none(self):
        """When no candidate matches, result should be None."""
        assert self._find_prior_enacted(["FY 2024 Enacted", "FY 2026 Request"]) is None

    def test_priority_prefers_enacted(self):
        """When both 'FY 2025 Enacted' and 'FY 2025' exist, prefer Enacted."""
        assert self._find_prior_enacted(["FY 2025", "FY 2025 Enacted"]) == "FY 2025 Enacted"


class TestDivisionLevelConfig:
    """Tests for division-level (e.g., Astrophysics) configuration."""

    def test_astrophysics_config_pattern(self):
        """Config for Astrophysics division should use correct columns."""
        config = BudgetProjectionConfig(
            fiscal_year=2026,
            budget_detail_row_name="Astrophysics",
            appropriation_column="Astrophysics",
            pbr_column="Astrophysics Proposed",
        )

        assert config.budget_detail_row_name == "Astrophysics"
        assert config.appropriation_column == "Astrophysics"
        assert config.pbr_column == "Astrophysics Proposed"
