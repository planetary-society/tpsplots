from functools import cached_property
from typing import ClassVar

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.nasa_budget_data_source import (
    Directorates,
    Historical,
    Science,
    ScienceDivisions,
)
from tpsplots.data_sources.nasa_budget_detail_data_source import NASABudgetDetailSource
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig
from tpsplots.processors.budget_projection_processor import (
    BudgetProjectionConfig,
    BudgetProjectionProcessor,
)
from tpsplots.processors.calculated_column_processor import (
    CalculatedColumnConfig,
    CalculatedColumnProcessor,
)
from tpsplots.processors.dataframe_to_yaml_processor import DataFrameToYAMLProcessor
from tpsplots.processors.inflation_adjustment_processor import (
    InflationAdjustmentConfig,
    InflationAdjustmentProcessor,
)


class NASAFYChartsController(ChartController):
    # The four NASA Science Mission Directorate divisions
    SCIENCE_DIVISIONS: ClassVar[list[str]] = [
        "Astrophysics",
        "Planetary Science",
        "Earth Science",
        "Heliophysics",
    ]

    # Column name emitted by BudgetProjectionProcessor before per-series renaming.
    _WH_PROJECTION_COL: ClassVar[str] = "White House Budget Projection"

    # TODO: This map exists because Directorates.RENAMES uses different names
    # than the budget_detail row names used as ACCOUNTS keys. Ideally the two
    # naming systems would be aligned so this bridge isn't needed.
    # Maps ACCOUNTS/budget_detail source name → Directorates renamed column name.
    DIRECTORATES_COLUMN_MAP: ClassVar[dict[str, str]] = {
        "Exploration": "Deep Space Exploration Systems",
        "STEM Engagement": "STEM Education",
    }

    def __init__(self):
        if not hasattr(self, "FISCAL_YEAR"):
            raise ValueError("FISCAL_YEAR must be defined in the subclass")

        self.budget_detail: pd.DataFrame = NASABudgetDetailSource(self.FISCAL_YEAR).data()

    @cached_property
    def historical(self) -> pd.DataFrame:
        return Historical().data()

    @cached_property
    def new_awards(self) -> pd.DataFrame:
        return NewNASAAwards().data()

    @cached_property
    def directorates(self) -> pd.DataFrame:
        return Directorates().data()

    def _accounts_to_map(self) -> dict[str, str]:
        """Convert ACCOUNTS (dict or list) to a source→display mapping.

        Returns an empty dict if ACCOUNTS is not defined on the subclass.
        """
        if not hasattr(self, "ACCOUNTS"):
            return {}
        if isinstance(self.ACCOUNTS, dict):
            return dict(self.ACCOUNTS)
        return {a: a for a in self.ACCOUNTS}

    # Methods for award tracking
    def _get_award_data(self, award_type: str = "Grant") -> dict:
        """Get processed award data using the generalized processor."""
        fy = self.FISCAL_YEAR
        fy_config = FiscalYearConfig(
            prior_years=[fy - 5, fy - 4, fy - 3, fy - 2, fy - 1],
            current_year=fy,
            comparison_year=fy - 1,
        )
        processor = AwardDataProcessor(
            fy_config=fy_config,
            award_type=award_type,
        )
        df = self.new_awards
        award_df = processor.process(df)
        result = DataFrameToYAMLProcessor().process(award_df)
        result["metadata"] = self._build_metadata(award_df, fiscal_year_col=None)
        return result

    def new_grants_awards_comparison_to_prior_year(self) -> dict:
        """Return new NASA grant award data compared to prior fiscal years.

        Compares cumulative monthly grant award values for the current
        fiscal year against the five prior years.

        Returns:
            dict with chart-ready series and metadata for YAML variable references.
        """
        return self._get_award_data(award_type="Grant")

    def new_contract_awards_comparison_to_prior_years(self) -> dict:
        """Return new NASA contract award data compared to prior fiscal years.

        Compares cumulative monthly contract award values for the current
        fiscal year against the five prior years.

        Returns:
            dict with chart-ready series and metadata for YAML variable references.
        """
        return self._get_award_data(award_type="Contract")

    def major_accounts_context(self) -> pd.DataFrame:
        """Return NASA major accounts data from 2006 to the controller's fiscal year.

        Filters budget detail rows to the accounts defined in the subclass's
        ACCOUNTS class variable, applies aliases, and renames the first column
        to "Account".

        Returns:
            DataFrame with one row per major account and columns for each
            fiscal year's enacted/requested values.
        """
        from tpsplots.processors.accounts_filter_processor import (
            AccountsFilterConfig,
            AccountsFilterProcessor,
        )

        data = self.budget_detail.copy()
        account_col = data.columns[0]

        # Filter rows for matching major accounts names in first column
        if hasattr(self, "ACCOUNTS"):
            filter_config = AccountsFilterConfig(
                accounts=self.ACCOUNTS,
                aliases=getattr(self, "ACCOUNT_ALIASES", {}),
                account_column=account_col,
                use_short_names=False,
            )
            data = AccountsFilterProcessor(filter_config).process(data)
        # Rename first column header to "Account"
        data = data.rename(columns={account_col: "Account"})

        return data

    def _directorates_comparison(self) -> pd.DataFrame:
        """Private: Prepare directorate data with filtering and short names.

        Returns DataFrame with:
        - Filtered to ACCOUNTS (with short names if ACCOUNTS is a dict)
        - Sorted by request descending

        This is the shared data preparation logic used by both
        directorates_comparison_raw() and directorates_comparison_grouped().
        """
        from tpsplots.processors.accounts_filter_processor import (
            AccountsFilterConfig,
            AccountsFilterProcessor,
        )

        df = self.budget_detail.copy()

        # Step 1: Filter to accounts (using AccountsFilterProcessor)
        if hasattr(self, "ACCOUNTS"):
            configured_accounts = list(self._accounts_to_map().keys())
            account_aliases = getattr(self, "ACCOUNT_ALIASES", {})
            filter_config = AccountsFilterConfig(
                accounts=self.ACCOUNTS,
                aliases=account_aliases,
                use_short_names=isinstance(self.ACCOUNTS, dict),
            )
            df = AccountsFilterProcessor(filter_config).process(df)

            if df.empty:
                source_account_col = self.budget_detail.columns[0]
                available_accounts = (
                    self.budget_detail[source_account_col]
                    .dropna()
                    .astype(str)
                    .drop_duplicates()
                    .tolist()
                )
                sample_accounts = (
                    ", ".join(available_accounts[:10]) if available_accounts else "none"
                )
                raise ValueError(
                    "No directorate rows matched configured accounts after normalization. "
                    f"Configured accounts: {configured_accounts}. "
                    f"Available source labels (sample): {sample_accounts}"
                )

        # Step 2: Sort by request descending
        request_col = f"FY {self.FISCAL_YEAR} Request"
        if request_col in df.columns:
            df = df.sort_values(request_col, ascending=False)

        return df.reset_index(drop=True)

    def directorates_comparison_raw(self) -> dict:
        """Return directorate data as raw table for flexible charting/export.

        Use for: tables, heatmaps, custom chart types, data export.

        Returns:
            dict with columns as keys, including Account and all FY columns.
        """
        df = self._directorates_comparison()
        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(df, fiscal_year_col=None)
        return result

    def directorates_comparison_grouped(self) -> dict:
        """Return directorate data formatted for grouped bar charts.

        Creates pre-configured group sets for different chart variants:
        - groups_pbr: Prior year enacted vs current year request
        - groups_enacted_vs_approp: Prior year enacted vs current appropriation
        - groups_all: All three columns

        Returns:
            dict with categories, groups, and group sets ready for YAML templates.
        """
        from tpsplots.processors.grouped_bar_transform_processor import (
            GroupedBarTransformConfig,
            GroupedBarTransformProcessor,
        )

        df = self._directorates_comparison()

        # Define the columns for comparison
        prior_fy = self.FISCAL_YEAR - 1
        prior_enacted_candidates = [
            f"FY {prior_fy} Enacted",
            f"FY {prior_fy}",
            f"FY{prior_fy} Enacted",
            f"FY{prior_fy}",
        ]
        prior_enacted = next(
            (col for col in prior_enacted_candidates if col in df.columns),
            None,
        )
        current_request = f"FY {self.FISCAL_YEAR} Request"
        appropriated = "Appropriated"

        # Build value columns list based on what's available
        value_columns = []
        group_labels = []

        if prior_enacted is not None:
            value_columns.append(prior_enacted)
            group_labels.append(f"FY {prior_fy} Enacted")

        if current_request in df.columns:
            value_columns.append(current_request)
            group_labels.append(f"FY {self.FISCAL_YEAR} Request")

        if appropriated in df.columns:
            value_columns.append(appropriated)
            group_labels.append("Appropriated")

        # Transform to grouped bar format (values stay raw - view handles scaling/colors)
        transform_config = GroupedBarTransformConfig(
            category_column="Account",
            value_columns=value_columns,
            group_labels=group_labels,
        )
        df = GroupedBarTransformProcessor(transform_config).process(df)

        # Convert to YAML-ready dict
        result = DataFrameToYAMLProcessor().process(df)

        # Build specific group sets for chart variants
        groups = result.get("groups", [])

        # groups_pbr: Prior year enacted vs current year request (indices 0, 1)
        if len(groups) >= 2:
            result["groups_pbr"] = [groups[0], groups[1]]

        # groups_enacted_vs_approp: Prior year enacted vs appropriated (indices 0, 2)
        if len(groups) >= 3:
            result["groups_enacted_vs_approp"] = [groups[0], groups[2]]

        # groups_pbr_vs_approp: Prior year enacted vs appropriated (indices 1, 2)
        if len(groups) >= 3:
            result["groups_pbr_vs_approp"] = [groups[1], groups[2]]

        # groups_all is already set by the processor as 'groups'
        result["groups_all"] = groups

        result["metadata"] = self._build_metadata(df, fiscal_year_col=None)

        return result

    def directorates_comparison(self) -> dict:
        """Return directorate comparison data (grouped bar format by default).

        This method delegates to directorates_comparison_grouped() for
        backwards compatibility with existing YAML files.

        For raw table data, use directorates_comparison_raw() instead.
        """
        return self.directorates_comparison_grouped()

    def _directorates_data(self) -> pd.DataFrame:
        """Prepare directorate data with multi-year history and WH projections.

        Mirrors _science_divisions_data() for top-level directorates.
        Uses Directorates().data() for multi-year enacted history, then chains
        BudgetProjectionProcessor for each matched account to graft the current
        FY request and runout projections from budget_detail.

        Only directorates present in both ACCOUNTS (or its keys) AND the
        Directorates historical sheet are processed; others are silently skipped.

        Returns:
            DataFrame with Fiscal Year + per-directorate enacted and projection columns:
            - {display_name} - enacted historical values (NaN for current FY+)
            - {display_name} White House Budget Projection - PBR request + runouts
        """
        account_map = self._accounts_to_map()
        hist_df = self.directorates

        col_lookup = {c.strip().casefold(): c for c in hist_df.columns if c != "Fiscal Year"}

        # Select only the relevant historical columns
        relevant_cols = ["Fiscal Year"]
        matched_accounts: dict[str, tuple[str, str]] = {}  # source -> (hist_col, display_name)
        for source_name, display_name in account_map.items():
            normalized = source_name.strip().casefold()
            if normalized in col_lookup:
                hist_col = col_lookup[normalized]
            else:
                # Fall back to explicit column alias (e.g. "Exploration" → "Deep Space Exploration Systems")
                alias = self.DIRECTORATES_COLUMN_MAP.get(source_name)
                if alias is None:
                    continue  # silently skip accounts with no Directorates history
                alias_key = alias.strip().casefold()
                if alias_key not in col_lookup:
                    continue
                hist_col = col_lookup[alias_key]
            relevant_cols.append(hist_col)
            matched_accounts[source_name] = (hist_col, display_name)

        df = hist_df[relevant_cols].copy()

        for source_name, (hist_col, display_name) in matched_accounts.items():
            # Rename historical column to display_name before processing
            if hist_col != display_name:
                df = df.rename(columns={hist_col: display_name})

            # Graft PBR request and runout projections from budget_detail
            config = BudgetProjectionConfig(
                fiscal_year=self.FISCAL_YEAR,
                budget_detail_row_name=source_name,
                appropriation_column=display_name,
                pbr_column=display_name,
            )
            df = BudgetProjectionProcessor(config).process(df, self.budget_detail)

            # Rename generic projection column to directorate-specific
            df = df.rename(
                columns={self._WH_PROJECTION_COL: f"{display_name} {self._WH_PROJECTION_COL}"}
            )

        df = df.sort_values("Fiscal Year").reset_index(drop=True)
        df.attrs["fiscal_year"] = self.FISCAL_YEAR

        return df

    def directorates_context(self) -> dict:
        """Return historical budget data for each NASA directorate with WH projections.

        Uses ACCOUNTS from the subclass to determine which directorates to include.
        Mirrors science_division_context() but for top-level directorates.

        Each matched directorate includes:
        - Multi-year enacted history from the Directorates Google Sheet
        - Current FY PBR request and runout projections via BudgetProjectionProcessor

        Returns:
            dict with columns for each matched directorate:
            - {display_name} - enacted historical values
            - {display_name} White House Budget Projection - PBR + runouts
        """
        df = self._directorates_data()
        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(df, fiscal_year_col=None)
        return result

    def _science_divisions_data(self) -> pd.DataFrame:
        """Prepare science division data with inflation adjustment and PBR projection.

        For each division, chains processors directly on the DataFrame:
        1. BudgetProjectionProcessor - grafts PBR and runouts from budget_detail
        2. InflationAdjustmentProcessor - applies NNSI adjustment

        Returns:
            DataFrame with columns for each division's historical and projection data:
            - Fiscal Year
            - {Division} - raw historical values
            - {Division}_adjusted_nnsi - inflation-adjusted values
            - {Division} White House Budget Projection - PBR + runouts
        """
        # Load historical science division data
        df = ScienceDivisions().data()

        # Chain processors for each division directly on df
        for division in self.SCIENCE_DIVISIONS:
            # Step 1: Run projection processor (adds runout year rows on first division)
            config = BudgetProjectionConfig(
                fiscal_year=self.FISCAL_YEAR,
                budget_detail_row_name=division,
                appropriation_column=division,
                pbr_column=division,
            )
            df = BudgetProjectionProcessor(config).process(df, self.budget_detail)

            # Rename generic projection column to division-specific
            df = df.rename(
                columns={self._WH_PROJECTION_COL: f"{division} {self._WH_PROJECTION_COL}"}
            )

            # Step 2: Apply inflation adjustment
            inflation_config = InflationAdjustmentConfig(
                target_year=self.FISCAL_YEAR - 1,
                nnsi_columns=[division],
            )
            df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Ensure sorted by fiscal year
        df = df.sort_values("Fiscal Year").reset_index(drop=True)

        # Store metadata
        df.attrs["fiscal_year"] = self.FISCAL_YEAR
        df.attrs["inflation_target_year"] = self.FISCAL_YEAR - 1

        return df

    def science_division_context(self) -> dict:
        """Return historical budget data for each NASA science division.

        Includes FY PBR division requests and runout projections.
        Returns raw columnar data for flexible chart use - YAML defines presentation.

        Returns:
            dict with columns for each division:
            - {Division} - raw historical values
            - {Division}_adjusted_nnsi - inflation-adjusted values
            - {Division} White House Budget Projection - PBR + runouts
        """
        df = self._science_divisions_data()
        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(df)
        return result

    def science_context(self) -> dict:
        """Return historical budget data for NASA Science Mission Directorate (SMD).

        Uses a pipeline of processors:
        1. BudgetProjectionProcessor: Merge historical data with PBR and runout
        2. InflationAdjustmentProcessor: Apply NNSI adjustment to monetary columns
        3. CalculatedColumnProcessor: Add YoY change calculations
        4. DataFrameToYAMLProcessor: Convert to YAML-ready dict

        Inflation adjustment uses FISCAL_YEAR - 1 as target year.

        Returns:
            dict with chart-ready series and metadata for YAML variable references
        """

        # Step 1: Budget projection (returns DataFrame)
        budget_config = BudgetProjectionConfig(
            fiscal_year=self.FISCAL_YEAR,
            budget_detail_row_name="Science",
            appropriation_column="NASA Science",
            pbr_column="Science",
        )
        df = BudgetProjectionProcessor(budget_config).process(Science().data(), self.budget_detail)

        # Step 2: Apply inflation adjustment explicitly
        inflation_config = InflationAdjustmentConfig(
            target_year=self.FISCAL_YEAR - 1,
            nnsi_columns=["NASA Science"],
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Step 3: Add calculated columns (YoY change from prior appropriation to PBR)
        calc_config = CalculatedColumnConfig()
        calc_config.add(
            "Year-over-Year Change $",
            "delta_from_prior",
            "NASA Science",
            "NASA Science",
        )
        calc_config.add(
            "Year-over-Year Change %",
            "percent_delta_from_prior",
            "NASA Science",
            "NASA Science",
        )
        df = CalculatedColumnProcessor(calc_config).process(df)

        # Step 4: Convert to YAML-ready dict
        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(
            df,
            value_columns={"science": "NASA Science"},
        )
        return result

    def pbr_historical_context(self) -> dict:
        """Return historical budget data with current FY PBR and runout projections.

        Uses a pipeline of processors:
        1. BudgetProjectionProcessor: Merge historical data with PBR and runout
        2. InflationAdjustmentProcessor: Apply NNSI adjustment to monetary columns
        3. CalculatedColumnProcessor: Add YoY change calculations
        4. DataFrameToYAMLProcessor: Convert to YAML-ready dict

        Inflation adjustment uses FISCAL_YEAR - 1 as target year.

        Returns:
            dict with keys: fiscal_year, presidential_administration, pbr,
            appropriation, white_house_projection, pbr_adjusted_nnsi,
            appropriation_adjusted_nnsi, export_df, max_fiscal_year,
            prior_appropriation_to_pbr_change_dollars,
            prior_appropriation_to_pbr_change_percent, etc.
        """
        from tpsplots.processors.inflation_adjustment_processor import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        # Step 1: Budget projection (returns DataFrame)
        budget_config = BudgetProjectionConfig(
            fiscal_year=self.FISCAL_YEAR,
            budget_detail_row_name="Total",
            appropriation_column="Appropriation",
            pbr_column="PBR",
        )
        df = BudgetProjectionProcessor(budget_config).process(self.historical, self.budget_detail)

        # Step 2: Apply inflation adjustment explicitly
        inflation_config = InflationAdjustmentConfig(
            target_year=self.FISCAL_YEAR - 1,
            nnsi_columns=["PBR", "Appropriation"],
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Step 3: Add calculated columns (YoY change from prior appropriation to PBR)
        calc_config = CalculatedColumnConfig()
        calc_config.add(
            "Prior Appropriation to PBR Change $",
            "delta_from_prior",
            "PBR",
            "Appropriation",
        )
        calc_config.add(
            "Prior Appropriation to PBR Change %",
            "percent_delta_from_prior",
            "PBR",
            "Appropriation",
        )
        df = CalculatedColumnProcessor(calc_config).process(df)

        # Step 4: Convert to YAML-ready dict
        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(
            df,
            value_columns={
                "pbr": "PBR",
                "appropriation": "Appropriation",
            },
        )
        return result

    def workforce_projections(self) -> dict:
        """Return historical workforce data with optional FY projection.

        If WORKFORCE_PROJECTION is defined in the subclass, creates a projection
        series that overrides the actual FY value. Otherwise, returns workforce
        data as-is through the current fiscal year.

        Uses a pipeline of processors:
        1. WorkforceProjectionProcessor: Filter data and optionally add projection

        Returns:
            dict with chart-ready series and metadata for YAML variable references
        """
        from tpsplots.data_sources.nasa_budget_data_source import Workforce
        from tpsplots.processors.workforce_projection_processor import (
            WorkforceProjectionConfig,
            WorkforceProjectionProcessor,
        )

        df = Workforce().data()

        # Get optional projection value (None means show data as-is)
        projection_value = getattr(self, "WORKFORCE_PROJECTION", None)

        config = WorkforceProjectionConfig(
            fiscal_year=self.FISCAL_YEAR,
            projection_value=projection_value,
        )
        df = WorkforceProjectionProcessor(config).process(df)

        result = DataFrameToYAMLProcessor().process(df)
        result["metadata"] = self._build_metadata(df)
        return result
