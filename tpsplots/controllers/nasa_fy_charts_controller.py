import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.data_sources.nasa_budget_data_source import Directorates, Historical
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


class NASAFYChartsController(ChartController):
    def __init__(self):
        self.historical: pd.DataFrame = Historical().data()
        self.new_awards: pd.DataFrame = NewNASAAwards().data()
        if not hasattr(self, "FISCAL_YEAR"):
            raise ValueError("FISCAL_YEAR must be defined in the subclass")
        if not hasattr(self, "BUDGET_DETAIL_URL"):
            raise ValueError("BUDGET_DETAIL_URL must be defined in the subclass")
        self.budget_detail: pd.DataFrame = GoogleSheetsSource(self.BUDGET_DETAIL_URL).data()

        # Convert all columns except the first column to numeric, stripping any non-numeric characters
        for col in self.budget_detail.columns[1:]:
            self.budget_detail[col] = pd.to_numeric(
                self.budget_detail[col].astype(str).str.replace(r"[^\d.]", "", regex=True),
                errors="coerce",
            )
            self.budget_detail[col] = self.budget_detail[col] * 1_000_000

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
        df = self.new_awards.data()
        return processor.process(df)

    def new_grants_awards_comparison_to_prior_year(self) -> dict:
        """Process grant award data for historical comparison."""
        return self._get_award_data(award_type="Grant")

    def new_contract_awards_comparison_to_prior_years(self) -> dict:
        """Process contract award data for historical comparison."""
        return self._get_award_data(award_type="Contract")

    def major_accounts(self) -> pd.DataFrame:
        """Returns NASA major accounts data for in-FY comparison."""
        data = self.budget_detail
        # Filter rows for matching major accounts names in first column
        if hasattr(self, "ACCOUNTS"):
            data = data[data.iloc[:, 0].isin(self.ACCOUNTS)]
        # Rename first column header to "Account"
        data = data.rename(columns={data.columns[0]: "Account"})

        return data

    def science_division_context(self) -> dict:
        """Return historical budget data for each NASA science division.

        Includes given FY PBR division requests and runout projections.
        Includes calculated comparison columns for charting purposes.
        """
        pass

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
        from tpsplots.processors.inflation_adjustment_processor import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        # Step 1: Budget projection (returns DataFrame)
        budget_config = BudgetProjectionConfig(
            fiscal_year=self.FISCAL_YEAR,
            budget_detail_row_name="Science",
            appropriation_column="Science",  # Column name after renaming in Directorates
            pbr_column="Science",  # Directorate level uses same column for both
        )
        df = BudgetProjectionProcessor(budget_config).process(
            Directorates().data(), self.budget_detail
        )

        # Step 2: Apply inflation adjustment explicitly
        inflation_config = InflationAdjustmentConfig(
            target_year=self.FISCAL_YEAR - 1,
            nnsi_columns=["Science"],
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        # Step 3: Add calculated columns (YoY change from prior appropriation to PBR)
        calc_config = CalculatedColumnConfig()
        calc_config.add(
            "Prior Appropriation to PBR Change $",
            "delta_from_prior",
            "Science",
            "Science",
        )
        calc_config.add(
            "Prior Appropriation to PBR Change %",
            "percent_delta_from_prior",
            "Science",
            "Science",
        )
        df = CalculatedColumnProcessor(calc_config).process(df)

        # Step 4: Convert to YAML-ready dict
        return DataFrameToYAMLProcessor().process(df)

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
        return DataFrameToYAMLProcessor().process(df)
