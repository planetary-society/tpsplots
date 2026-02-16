"""Processor for filtering DataFrame rows to specified accounts.

This processor filters a DataFrame to include only rows matching specified account names.
It supports optional renaming of accounts (e.g., from full names to short display names).

Example usage:
    # Filter and rename accounts
    config = AccountsFilterConfig(
        accounts={"Deep Space Exploration Systems": "Exploration", "Science": "Science"},
        use_short_names=True,
    )
    df = AccountsFilterProcessor(config).process(df)

    # Filter only (no renaming)
    config = AccountsFilterConfig(
        accounts=["Science", "Aeronautics", "Space Technology"],
    )
    df = AccountsFilterProcessor(config).process(df)
"""

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AccountsFilterConfig:
    """Configuration for AccountsFilterProcessor.

    Attributes:
        accounts: Either a dict mapping full name → short name, or a list of account names.
            When a dict, keys are matched against the account column; values are used for renaming.
            When a list, accounts are filtered but not renamed.
        aliases: Optional mapping of canonical account name → alias name(s).
            Alias values can be a single string or a list of strings. Aliases are
            matched using the same normalization as canonical names.
        account_column: Name of the column containing account names (default: "Account").
        use_short_names: If True and accounts is a dict, replace full names with short names.
            Ignored if accounts is a list.
    """

    accounts: dict[str, str] | list[str] = field(default_factory=dict)
    aliases: dict[str, str | list[str]] = field(default_factory=dict)
    account_column: str = "Account"
    use_short_names: bool = True


class AccountsFilterProcessor:
    """Filters DataFrame rows to specified accounts with optional renaming.

    This processor is designed for filtering budget data to specific directorates
    or accounts, with support for renaming to shorter display names for charts.

    Returns a DataFrame (not dict) to enable pipeline chaining:
        df = AccountsFilterProcessor(config).process(df)
        df = CalculatedColumnProcessor(calc_config).process(df)
        result = DataFrameToYAMLProcessor().process(df)

    Example:
        # NASA directorate filtering with short names
        config = AccountsFilterConfig(
            accounts={
                "Deep Space Exploration Systems": "Exploration",
                "LEO & Space Ops": "Space Ops",
                "Science": "Science",
            },
            use_short_names=True,
        )
        df = AccountsFilterProcessor(config).process(budget_df)
    """

    def __init__(self, config: AccountsFilterConfig):
        """Initialize the processor with configuration.

        Args:
            config: Configuration specifying accounts to filter and rename options.
        """
        self.config = config

    @staticmethod
    def _normalize_account_name(value: object) -> str:
        """Normalize account labels for robust matching."""
        text = str(value).strip().casefold()
        # Normalize common text variants like '&' vs 'and', punctuation, and spacing.
        text = text.replace("&", " and ")
        text = re.sub(r"[^0-9a-z]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame to specified accounts with optional renaming.

        Args:
            df: DataFrame with an account column to filter.

        Returns:
            DataFrame filtered to specified accounts, optionally with renamed account values.

        Raises:
            KeyError: If the account column doesn't exist in the DataFrame.
        """
        if self.config.account_column not in df.columns:
            raise KeyError(
                f"Column '{self.config.account_column}' not found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

        df = df.copy()

        # Determine canonical account names and output labels
        if isinstance(self.config.accounts, dict):
            canonical_account_names = list(self.config.accounts.keys())
        else:
            canonical_account_names = list(self.config.accounts)

        normalized_to_canonical = {
            self._normalize_account_name(name): name for name in canonical_account_names
        }

        # Add configured aliases to matching lookup
        for canonical_name, alias_values in self.config.aliases.items():
            normalized_canonical = self._normalize_account_name(canonical_name)
            resolved_canonical = normalized_to_canonical.get(normalized_canonical)
            if resolved_canonical is None:
                raise ValueError(
                    f"Alias target '{canonical_name}' is not present in configured accounts."
                )

            if isinstance(alias_values, str):
                aliases = [alias_values]
            else:
                aliases = alias_values

            for alias in aliases:
                normalized_to_canonical[self._normalize_account_name(alias)] = resolved_canonical

        normalized_accounts = df[self.config.account_column].map(self._normalize_account_name)
        matched_canonical = normalized_accounts.map(normalized_to_canonical)

        # Filter rows to matching accounts
        df = df.loc[matched_canonical.notna()].copy()

        # Optionally rename accounts to short names
        if isinstance(self.config.accounts, dict) and self.config.use_short_names:
            df[self.config.account_column] = matched_canonical.loc[df.index].map(self.config.accounts)

        return df.reset_index(drop=True)
