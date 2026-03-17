"""Controller for Project Apollo spending charts."""

from __future__ import annotations

import logging

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.apollo_data_source import (
    ApolloSpending,
    FacilitiesConstructionSpending,
    ProjectGemini,
    RoboticLunarProgramSpending,
    SaturnLaunchVehicles,
    _ApolloBase,
)

logger = logging.getLogger(__name__)


class Apollo(ChartController):
    """Controller for Project Apollo program spending charts."""

    def program_spending(self) -> dict:
        """Return Apollo program spending data with NNSI inflation adjustment.

        Provides the full dataset (FY 1960-1973) with nominal and
        inflation-adjusted values for all 25 monetary columns, plus
        column sums for both nominal and adjusted values.

        Returns:
            dict with keys:
                - data: Full DataFrame with all columns including adjusted
                - Fiscal Year: Series of fiscal year datetimes
                - Lunar effort % of NASA: Percentage series
                - {col}: Nominal series for each monetary column (original name)
                - {col}_adjusted_nnsi: Adjusted series for each monetary column
                - {col}_sum: int sum of nominal values for each monetary column
                - {col}_adjusted_nnsi_sum: int sum of adjusted values
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys (min/max FY, inflation year, source)
        """
        result = self._spending_result(
            ApolloSpending,
            fiscal_year_col="Fiscal Year",
            source_label="NASA Historical Data Book, Project Apollo costs",
        )
        # Apollo-specific: expose the percentage series
        result["Lunar effort % of NASA"] = result["data"]["Lunar effort % of NASA"]
        return result

    def _spending_result(
        self,
        source_cls: type[_ApolloBase],
        fiscal_year_col: str,
        source_label: str,
        *,
        columns: list[str] | None = None,
        monetary_columns: list[str] | None = None,
    ) -> dict:
        """Build a standard spending result dict for an Apollo-era data source."""
        from tpsplots.processors import (
            InflationAdjustmentConfig,
            InflationAdjustmentProcessor,
        )

        df = source_cls().data()
        if columns is not None:
            df = df[columns].copy()
        monetary_columns = monetary_columns or source_cls.MONETARY_COLUMNS

        inflation_config = InflationAdjustmentConfig(
            nnsi_columns=monetary_columns,
        )
        df = InflationAdjustmentProcessor(inflation_config).process(df)

        result: dict = {"data": df}
        result[fiscal_year_col] = df[fiscal_year_col]

        export_cols = [fiscal_year_col]
        for col in monetary_columns:
            adjusted_col = f"{col}_adjusted_nnsi"
            has_adjusted = adjusted_col in df.columns

            result[col] = df[col]
            result[f"{col}_sum"] = int(df[col].sum(skipna=True))
            export_cols.append(col)

            if has_adjusted:
                result[adjusted_col] = df[adjusted_col]
                result[f"{adjusted_col}_sum"] = int(df[adjusted_col].sum(skipna=True))
                export_cols.append(adjusted_col)

        result["export_df"] = self._export_helper(df, export_cols)

        result["metadata"] = self._build_metadata(
            df,
            fiscal_year_col=fiscal_year_col,
            source=source_label,
        )

        return result

    def robotic_lunar_spending(self) -> dict:
        """Return Robotic Lunar Programs spending with NNSI inflation adjustment.

        Covers Ranger, Surveyor, and Lunar Orbiter programs.

        Returns:
            dict with keys:
                - data: Full DataFrame with all columns including adjusted
                - Year: Series of fiscal year datetimes
                - {col}: Nominal series for each monetary column
                - {col}_adjusted_nnsi: Adjusted series for each monetary column
                - {col}_sum: int sum of nominal values
                - {col}_adjusted_nnsi_sum: int sum of adjusted values
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys (min/max FY, inflation year, source)
        """
        return self._spending_result(
            RoboticLunarProgramSpending,
            fiscal_year_col="Year",
            source_label="NASA Historical Data Book, Robotic Lunar Programs",
        )

    def gemini_spending(self) -> dict:
        """Return Project Gemini spending with NNSI inflation adjustment.

        Returns:
            dict with keys:
                - data: Full DataFrame with all columns including adjusted
                - Fiscal Year: Series of fiscal year datetimes
                - {col}: Nominal series for each monetary column
                - {col}_adjusted_nnsi: Adjusted series for each monetary column
                - {col}_sum: int sum of nominal values
                - {col}_adjusted_nnsi_sum: int sum of adjusted values
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys (min/max FY, inflation year, source)
        """
        return self._spending_result(
            ProjectGemini,
            fiscal_year_col="Fiscal Year",
            source_label="NASA Historical Data Book, Project Gemini costs",
        )

    def facilities_construction_spending(self) -> dict:
        """Return Apollo Facilities Construction spending with NNSI inflation adjustment.

        Returns:
            dict with keys:
                - data: Full DataFrame with all columns including adjusted
                - Year: Series of fiscal year datetimes
                - {col}: Nominal series for each monetary column
                - {col}_adjusted_nnsi: Adjusted series for each monetary column
                - {col}_sum: int sum of nominal values
                - {col}_adjusted_nnsi_sum: int sum of adjusted values
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys (min/max FY, inflation year, source)
        """
        return self._spending_result(
            FacilitiesConstructionSpending,
            fiscal_year_col="Year",
            source_label="NASA Historical Data Book, Apollo Facilities Construction",
        )

    def launch_vehicles_spending(self) -> dict:
        """Return Saturn-family launch vehicle development costs with NNSI adjustment.

        Covers Saturn I, Saturn IB, and Saturn V development spending
        extracted from the full Apollo program dataset.

        Returns:
            dict with keys:
                - data: Full DataFrame with all columns including adjusted
                - Fiscal Year: Series of fiscal year datetimes
                - {col}: Nominal series for each monetary column
                - {col}_adjusted_nnsi: Adjusted series for each monetary column
                - {col}_sum: int sum of nominal values
                - {col}_adjusted_nnsi_sum: int sum of adjusted values
                - export_df: DataFrame for CSV export
                - metadata: dict with standard keys (min/max FY, inflation year, source)
        """
        return self._spending_result(
            ApolloSpending,
            fiscal_year_col="Fiscal Year",
            source_label="NASA Historical Data Book, Saturn-family launch vehicle development costs",
            columns=["Fiscal Year", *SaturnLaunchVehicles.MONETARY_COLUMNS],
            monetary_columns=SaturnLaunchVehicles.MONETARY_COLUMNS,
        )
