"""CSV file data controller for YAML-driven chart generation."""

from __future__ import annotations

import pandas as pd

from tpsplots.controllers.tabular_data_controller import TabularDataController
from tpsplots.data_sources.csv_source import CSVSource


class CSVController(TabularDataController):
    """Controller for processing CSV file data sources.

    Delegates all data loading and processing to
    :class:`~tpsplots.data_sources.csv_source.CSVSource`, providing a
    standard controller interface for the YAML chart generation system.
    """

    def __init__(self, csv_path: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.csv_path = csv_path

    def _validate_input(self) -> None:
        if not self.csv_path:
            raise ValueError("csv_path must be provided to load CSV data")

    def _create_source(self) -> CSVSource:
        return CSVSource(csv_path=self.csv_path, **self._build_source_kwargs())

    def _source_description(self) -> str:
        return f"CSV file {self.csv_path}"

    def _load_summary_df(self) -> pd.DataFrame:
        return pd.read_csv(self.csv_path)
