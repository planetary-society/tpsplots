"""Google Sheets data controller for YAML-driven chart generation."""

from __future__ import annotations

import re

from tpsplots.controllers.tabular_data_controller import TabularDataController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource


class GoogleSheetsController(TabularDataController):
    """Controller for processing Google Sheets data sources.

    Wraps :class:`~tpsplots.data_sources.google_sheets_source.GoogleSheetsSource`
    to provide a standard controller interface for the YAML chart generation
    system.
    """

    def __init__(self, url: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.url = url

    def _validate_input(self) -> None:
        if not self.url:
            raise ValueError("url must be provided to load Google Sheets data")

    def _create_source(self) -> GoogleSheetsSource:
        normalized_url = self.normalize_google_sheets_url(self.url)
        return GoogleSheetsSource(url=normalized_url, **self._build_source_kwargs())

    def _source_description(self) -> str:
        return f"Google Sheets URL {self.url}"

    def get_column_data(self, column_name: str):
        """Get data from a specific column using GoogleSheetsSource's attribute access.

        Args:
            column_name: Name of the column to retrieve

        Returns:
            List of values from the specified column
        """
        if not self._source:
            self.load_data()

        return getattr(self._source, column_name.lower().replace(" ", "_"))

    @staticmethod
    def normalize_google_sheets_url(url: str) -> str:
        """Convert a regular Google Sheets URL to CSV export format.

        Preserves the ``gid`` parameter (tab selector) when present in the
        original URL's fragment (``#gid=…``) or query string (``?gid=…``).

        Args:
            url: Google Sheets URL (regular or export format)

        Returns:
            str: CSV export URL
        """
        if "docs.google.com/spreadsheets" in url and "export?format=csv" not in url:
            sheet_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
            if sheet_id_match:
                sheet_id = sheet_id_match.group(1)
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

                gid_match = re.search(r"[#?&]gid=(\d+)", url)
                if gid_match:
                    export_url += f"&gid={gid_match.group(1)}"

                return export_url

        return url
