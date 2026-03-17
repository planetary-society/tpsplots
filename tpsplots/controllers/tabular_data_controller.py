"""Base controller for tabular data sources (CSV, Google Sheets, etc.)."""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.tabular_data_source import TabularDataSource
from tpsplots.exceptions import DataSourceError

logger = logging.getLogger(__name__)


class TabularDataController(ChartController):
    """Base for controllers that load from TabularDataSource subclasses.

    Extracts shared init, source-kwargs construction, load_data template, and
    get_data_summary from CSVController and GoogleSheetsController.  Subclasses
    override :meth:`_create_source`, :meth:`_validate_input`, and
    :meth:`_source_description`.
    """

    def __init__(
        self,
        *,
        cast: dict[str, str] | None = None,
        columns: list[str] | None = None,
        renames: dict[str, str] | None = None,
        auto_clean_currency: bool | dict | None = None,
        fiscal_year_column: str | bool | None = None,
        truncate_at: bool | str | None = None,
    ) -> None:
        self.cast = cast
        self.columns = columns
        self.renames = renames
        self.auto_clean_currency = auto_clean_currency if auto_clean_currency is not None else True
        self.fiscal_year_column = fiscal_year_column
        self.truncate_at = truncate_at
        self._source: TabularDataSource | None = None

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def _create_source(self) -> TabularDataSource:
        """Create the concrete data source instance."""

    @abstractmethod
    def _validate_input(self) -> None:
        """Validate that required input (path, url, etc.) is provided.

        Raises:
            ValueError: If required input is missing.
        """

    @abstractmethod
    def _source_description(self) -> str:
        """Human-readable description for logging and error messages."""

    def _load_summary_df(self) -> pd.DataFrame:
        """Load a DataFrame for :meth:`get_data_summary`.

        Default implementation uses the existing source.  Subclasses can
        override to provide a lighter-weight summary (e.g. raw CSV read).
        """
        if not self._source:
            self._validate_input()
            self._source = self._create_source()
        return self._source.data()

    # ------------------------------------------------------------------
    # Shared logic
    # ------------------------------------------------------------------

    def _build_source_kwargs(self) -> dict[str, Any]:
        """Build kwargs dict for the TabularDataSource subclass constructor."""
        kwargs: dict[str, Any] = {"auto_clean_currency": self.auto_clean_currency}
        if self.cast:
            kwargs["cast"] = self.cast
        if self.columns:
            kwargs["columns"] = self.columns
        if self.renames:
            kwargs["renames"] = self.renames
        if self.fiscal_year_column is not None:
            kwargs["fiscal_year_column"] = self.fiscal_year_column
        if self.truncate_at is not None:
            kwargs["truncate_at"] = self.truncate_at
        return kwargs

    def load_data(self) -> dict[str, Any]:
        """Load data and return as dict for YAML processing.

        Returns:
            dict with 'data' (DataFrame), per-column arrays, and 'metadata'.

        Raises:
            ValueError: If required input is not provided.
            DataSourceError: If data cannot be loaded.
        """
        self._validate_input()
        try:
            self._source = self._create_source()
            df = self._source.data()
            logger.info(
                f"Loaded data from {self._source_description()} "
                f"({len(df)} rows, {len(df.columns)} columns)"
            )
            return self._build_load_result(df, self.fiscal_year_column)
        except DataSourceError:
            raise
        except Exception as e:  # Boundary: wrap as DataSourceError
            raise DataSourceError(f"Error loading from {self._source_description()}: {e}") from e

    def get_data_summary(self) -> dict:
        """Get a summary of the loaded data for debugging purposes."""
        try:
            df = self._load_summary_df()
            return {
                "source": self._source_description(),
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict("records"),
                "configuration": {
                    "cast": self.cast,
                    "columns": self.columns,
                    "renames": self.renames,
                    "auto_clean_currency": self.auto_clean_currency,
                    "fiscal_year_column": self.fiscal_year_column,
                    "truncate_at": self.truncate_at,
                },
            }
        except Exception as e:
            return {"error": f"Could not analyze data: {e}"}
