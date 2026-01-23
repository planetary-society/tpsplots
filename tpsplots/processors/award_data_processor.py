"""Processor for fiscal year award data analysis and comparison."""

from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd


@dataclass
class FiscalYearConfig:
    """Configuration for fiscal year range processing."""

    prior_years: list[int]
    current_year: int
    comparison_year: int | None = None

    def __post_init__(self):
        if self.comparison_year is None:
            # Default to the last prior year if not specified
            self.comparison_year = self.prior_years[-1] if self.prior_years else None

    @property
    def all_years(self) -> list[int]:
        """Return all years including current year."""
        return [*self.prior_years, self.current_year]

    @property
    def prior_year_range_label(self) -> str:
        """Generate label like '2020-24' for average line."""
        if len(self.prior_years) < 2:
            return str(self.prior_years[0]) if self.prior_years else ""
        start = str(self.prior_years[0])
        end = str(self.prior_years[-1])[-2:]  # Last two digits
        return f"{start}-{end}"


class AwardDataProcessor:
    """
    Processes fiscal year award data for historical comparison charts.

    This processor transforms raw award data into cumulative time series
    suitable for line chart visualization, including prior year trends,
    averages, current year tracking, and projections.
    """

    # Fiscal year months in order (Oct-Sep)
    MONTHS: ClassVar[list[str]] = [
        "Oct",
        "Nov",
        "Dec",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
    ]

    def __init__(
        self,
        fy_config: FiscalYearConfig,
        award_type: str = "Grant",
        auto_detect_current_month: bool = True,
        current_month_override: int | None = None,
        projection_months: int = 2,
    ):
        """
        Initialize the award data processor.

        Args:
            fy_config: Configuration defining the fiscal year range
            award_type: Either "Grant" or "Contract"
            auto_detect_current_month: If True, determine current month from system date
            current_month_override: Override for testing (1-12, fiscal month count)
            projection_months: Number of recent months to average for projection
        """
        self.fy_config = fy_config
        self.award_type = award_type
        self.auto_detect_current_month = auto_detect_current_month
        self.current_month_override = current_month_override
        self.projection_months = projection_months

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process award data and return a DataFrame with chart metadata in attrs.

        Args:
            df: DataFrame with columns "Month" and "FY {year} New {award_type} Awards"

        Returns:
            DataFrame suitable for CSV export, with chart metadata stored in attrs.
            The attrs include:
            - months: List of fiscal year month labels
            - y_series: List of data series for plotting
            - labels: List of labels for each series (None for unlabeled)
            - series_types: List of semantic types ("prior", "average", "current")
              that views can use to apply appropriate styling
            - shortfall_pct: Projected shortfall percentage vs comparison year
        """
        # Filter out the "Total" row if present
        df = df[df["Month"] != "Total"].copy()

        # Build award columns dictionary
        award_columns = self._build_award_columns()

        # Calculate cumulative data for all years
        cumulative_data = self._calculate_cumulative_data(df, award_columns)

        # Process prior years and build series data
        y_series, labels, series_types = self._process_prior_years(cumulative_data)

        # Calculate and add mean of prior years
        mean_cumulative = self._calculate_prior_year_mean(cumulative_data)
        if mean_cumulative:
            y_series.append(mean_cumulative)
            labels.append(self._generate_average_label())
            series_types.append("average")

        # Process current year
        last_full_month = self._get_current_fiscal_month()
        fy_current_data = self._process_current_year(df, award_columns, last_full_month)

        if fy_current_data:
            y_series.append(fy_current_data["padded_cumulative"])
            labels.append(self._generate_current_year_label())
            series_types.append("current")

        # Calculate shortfall projection
        shortfall_pct = self._calculate_shortfall(
            cumulative_data,
            fy_current_data,
            last_full_month,
        )

        # Build export DataFrame and attach chart metadata in attrs
        export_df = self._build_export_dataframe(y_series, labels)
        export_df.attrs.update(
            {
                "months": self.MONTHS,
                "y_series": y_series,
                "labels": labels,
                "series_types": series_types,
                "shortfall_pct": shortfall_pct,
            }
        )

        return export_df

    def _build_award_columns(self) -> dict[int, str]:
        """Build mapping of year to column name."""
        return {
            year: f"FY {year} New {self.award_type} Awards" for year in self.fy_config.all_years
        }

    def _calculate_cumulative_data(
        self, df: pd.DataFrame, award_columns: dict[int, str]
    ) -> dict[int, list]:
        """Calculate cumulative sums for each year."""
        cumulative_data = {}
        for year in self.fy_config.prior_years:
            if award_columns[year] in df.columns:
                year_awards = df[award_columns[year]].tolist()
                year_cumulative = np.rint(np.cumsum(year_awards)).astype(int).tolist()
                cumulative_data[year] = year_cumulative
        return cumulative_data

    def _process_prior_years(self, cumulative_data: dict[int, list]) -> tuple[list, list, list]:
        """
        Process prior years into chart series data.

        Returns:
            Tuple of (y_series, labels, series_types) where:
            - y_series: List of cumulative data arrays
            - labels: List of labels (None for individual prior years)
            - series_types: List of semantic types ("prior" for all prior years)
        """
        y_series = []
        labels = []
        series_types = []

        for year in self.fy_config.prior_years:
            if year in cumulative_data:
                y_series.append(cumulative_data[year])
                labels.append(None)  # No label for individual prior years
                series_types.append("prior")

        return y_series, labels, series_types

    def _calculate_prior_year_mean(self, cumulative_data: dict[int, list]) -> list:
        """Calculate mean of all prior years' cumulative data."""
        if not cumulative_data:
            return []
        prior_years_array = np.array(list(cumulative_data.values()))
        return np.rint(np.mean(prior_years_array, axis=0)).astype(int).tolist()

    def _get_current_fiscal_month(self) -> int:
        """
        Determine the current fiscal month count (1-12, where Oct=1, Sep=12).

        Returns:
            int: Number of months with complete data
        """
        if self.current_month_override is not None:
            return self.current_month_override

        if not self.auto_detect_current_month:
            return 12  # Assume full year if auto-detection disabled

        now = pd.Timestamp.now()
        fiscal_year_end = pd.Timestamp(year=self.fy_config.current_year, month=9, day=30)

        if now > fiscal_year_end:
            return 12  # Full fiscal year complete

        # Convert calendar month to fiscal month count
        # The last FULL month is the prior month
        # Oct(10)->1, Nov(11)->2, Dec(12)->3, Jan(1)->4, ..., Sep(9)->12
        calendar_month = now.month
        fiscal_month = calendar_month - 9 if calendar_month >= 10 else calendar_month + 3

        # Subtract 1 because we want completed months, not current month
        return max(0, fiscal_month - 1)

    def _process_current_year(
        self,
        df: pd.DataFrame,
        award_columns: dict[int, str],
        last_full_month: int,
    ) -> dict | None:
        """Process current year data with padding for incomplete months."""
        current_year = self.fy_config.current_year
        if award_columns[current_year] not in df.columns:
            return None

        # Get awards for completed months
        current_awards = df[award_columns[current_year]].tolist()[:last_full_month]
        if not current_awards:
            return None

        current_cumulative = np.rint(np.cumsum(current_awards)).astype(int).tolist()

        # Pad with None for incomplete months
        total_months = 12
        none_tail = [None] * max(0, total_months - last_full_month)
        padded_cumulative = current_cumulative + none_tail

        return {
            "awards": current_awards,
            "cumulative": current_cumulative,
            "padded_cumulative": padded_cumulative,
        }

    def _calculate_shortfall(
        self,
        cumulative_data: dict[int, list],
        fy_current_data: dict | None,
        last_full_month: int,
    ) -> float:
        """Calculate projected shortfall percentage vs comparison year."""
        if not fy_current_data or not cumulative_data:
            return 0

        comparison_year = self.fy_config.comparison_year
        if comparison_year not in cumulative_data:
            return 0

        current_cumulative = list(fy_current_data["cumulative"])
        current_awards = fy_current_data["awards"]

        # Project remaining months using average of recent months
        if last_full_month >= self.projection_months:
            recent_months_total = sum(
                current_awards[last_full_month - i - 1] for i in range(self.projection_months)
            )
            avg_monthly_rate = recent_months_total / self.projection_months

            for month in range(last_full_month, 12):
                current_cumulative.append(avg_monthly_rate + current_cumulative[month - 1])

        if len(current_cumulative) != 12:
            return 0

        projected_total = current_cumulative[-1]
        comparison_total = cumulative_data[comparison_year][-1]

        if comparison_total == 0:
            return 0

        return ((comparison_total - projected_total) / comparison_total) * 100

    def _generate_average_label(self) -> str:
        """Generate dynamic label for the average line."""
        range_str = self.fy_config.prior_year_range_label
        return f"{range_str}\nAverage"

    def _generate_current_year_label(self) -> str:
        """Generate label for current year line."""
        return f"FY {self.fy_config.current_year}"

    def _build_export_dataframe(self, y_series: list, labels: list) -> pd.DataFrame:
        """Build DataFrame suitable for CSV export."""
        export_data = {"Month": self.MONTHS}
        for label, series in zip(labels, y_series, strict=False):
            if label is not None:
                export_data[f"{label} Cumulative"] = series

        export_df = pd.DataFrame(export_data)

        # Convert numeric columns to nullable integer type
        for col in export_df.columns:
            if col != "Month":
                export_df[col] = pd.array(export_df[col], dtype=pd.Int64Dtype())

        return export_df
