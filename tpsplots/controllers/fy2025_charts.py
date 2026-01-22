"""Concrete NASA budget charts using specialized chart views."""

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.new_awards import NewNASAAwards
from tpsplots.processors.award_data_processor import AwardDataProcessor, FiscalYearConfig


class FY2025Charts(ChartController):
    # Define the fiscal year configuration for FY 2025 tracking.
    FY_CONFIG = FiscalYearConfig(
        prior_years=[2020, 2021, 2022, 2023, 2024],
        current_year=2025,
        comparison_year=2024,
    )

    def _get_award_data(self, award_type: str = "Grant") -> dict:
        """Get processed award data using the generalized processor."""
        processor = AwardDataProcessor(
            fy_config=self.FY_CONFIG,
            award_type=award_type,
        )
        df = NewNASAAwards().data()
        return processor.process(df)

    def new_grants_awards_comparison_to_prior_year(self) -> dict:
        """Process grant award data for historical comparison."""
        return self._get_award_data(award_type="Grant")

    def new_contract_awards_comparison_to_prior_years(self) -> dict:
        """Process contract award data for historical comparison."""
        return self._get_award_data(award_type="Contract")
