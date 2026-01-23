"""Tests for AccountsFilterProcessor."""

import pandas as pd
import pytest

from tpsplots.processors.accounts_filter_processor import (
    AccountsFilterConfig,
    AccountsFilterProcessor,
)


class TestAccountsFilterProcessor:
    """Tests for AccountsFilterProcessor."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with account names."""
        return pd.DataFrame(
            {
                "Account": ["Science", "Exploration", "Space Ops", "Aeronautics"],
                "FY 2026 Request": [7, 8, 5, 2],
            }
        )

    def test_filters_by_account_list(self, sample_df):
        """Filters rows to provided account list without renaming."""
        config = AccountsFilterConfig(accounts=["Science", "Space Ops"])
        result = AccountsFilterProcessor(config).process(sample_df)

        assert result["Account"].tolist() == ["Science", "Space Ops"]
        assert result["FY 2026 Request"].tolist() == [7, 5]

    def test_filters_and_renames_with_dict(self, sample_df):
        """Dict accounts should be renamed to short names by default."""
        config = AccountsFilterConfig(
            accounts={"Science": "Sci", "Exploration": "Exp"},
            use_short_names=True,
        )
        result = AccountsFilterProcessor(config).process(sample_df)

        assert result["Account"].tolist() == ["Sci", "Exp"]

    def test_dict_without_renaming(self, sample_df):
        """When use_short_names is False, keep original names."""
        config = AccountsFilterConfig(
            accounts={"Science": "Sci", "Exploration": "Exp"},
            use_short_names=False,
        )
        result = AccountsFilterProcessor(config).process(sample_df)

        assert result["Account"].tolist() == ["Science", "Exploration"]

    def test_missing_account_column_raises(self, sample_df):
        """Missing account column should raise KeyError."""
        config = AccountsFilterConfig(accounts=["Science"], account_column="Dept")

        with pytest.raises(KeyError, match="Column 'Dept' not found"):
            AccountsFilterProcessor(config).process(sample_df)

    def test_resets_index(self, sample_df):
        """Result should have a clean index after filtering."""
        config = AccountsFilterConfig(accounts=["Space Ops"])
        result = AccountsFilterProcessor(config).process(sample_df)

        assert result.index.tolist() == [0]
