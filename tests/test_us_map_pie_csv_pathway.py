"""Tests for the column-oriented (CSV-driven) us_map_pie pathway.

Covers ``USMapPieChartView._build_pie_data_from_columns``: assembly,
blank-map-key dropping, log output, and validation errors.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from tpsplots.views.us_map_pie_charts import USMapPieChartView


@pytest.fixture
def fy2025_drp_df() -> pd.DataFrame:
    """Match yaml/examples/data/2025_NASA_DRP_cuts_by_center.csv."""
    rows = [
        ("HQ", "NASA Headquarters", 1841, 1382, 459, 0.2493),
        ("ARC", "Ames Research Center", 1225, 942, 283, 0.2310),
        ("AFRC", "Armstrong Flight Research Center", 500, 385, 115, 0.2300),
        ("GRC", "Glenn Research Center", 1391, 1071, 320, 0.2300),
        ("GSFC", "Goddard Space Flight Center", 2884, 2221, 663, 0.2299),
        ("JSC", "Johnson Space Center", 3292, 2535, 757, 0.2300),
        ("KSC", "Kennedy Space Center", 2016, 1553, 463, 0.2297),
        ("LaRC", "Langley Research Center", 1730, 1332, 398, 0.2300),
        ("MSFC", "Marshall Space Flight Center", 2240, 1725, 515, 0.2299),
        ("SSC", "Stennis Space Center", 274, 211, 63, 0.2299),
        ("", "Shared Services", 205, 158, 47, 0.2293),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Map Key",
            "NASA Center",
            "Starting Population",
            "Estimated Final Population",
            "Total Civil Servants Departing Agency",
            "Departure Share",
        ],
    )


VALUE_COLS = ["Estimated Final Population", "Total Civil Servants Departing Agency"]
LABELS = ["Remaining", "Departing"]
COLORS = ["#037CC2", "#FF5D47"]


class TestPieDataAssembly:
    def test_builds_ten_plotted_pies(self, fy2025_drp_df):
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            fy2025_drp_df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        assert len(pie_data) == 10
        assert set(pie_data.keys()) == {
            "HQ",
            "ARC",
            "AFRC",
            "GRC",
            "GSFC",
            "JSC",
            "KSC",
            "LaRC",
            "MSFC",
            "SSC",
        }

    def test_arc_values_match_expected(self, fy2025_drp_df):
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            fy2025_drp_df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        assert pie_data["ARC"]["values"] == [942.0, 283.0]
        assert pie_data["ARC"]["labels"] == LABELS
        assert pie_data["ARC"]["colors"] == COLORS

    def test_hq_values_match_expected(self, fy2025_drp_df):
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            fy2025_drp_df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        assert pie_data["HQ"]["values"] == [1382.0, 459.0]

    def test_blank_map_key_row_dropped_and_logged(self, fy2025_drp_df, caplog):
        with caplog.at_level(logging.INFO, logger="tpsplots.views.us_map_pie_charts"):
            pie_data = USMapPieChartView._build_pie_data_from_columns(
                fy2025_drp_df, "Map Key", VALUE_COLS, LABELS, COLORS
            )
        assert "" not in pie_data  # empty key not present
        assert "Shared Services" not in pie_data
        # Log mentions the dropped row's display name
        assert "Shared Services" in caplog.text
        assert "1" in caplog.text  # count of dropped rows

    def test_labels_and_colors_are_copied_per_row(self, fy2025_drp_df):
        """Mutating one center's labels list must not affect another's."""
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            fy2025_drp_df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        pie_data["ARC"]["labels"].append("Mutated")
        assert "Mutated" not in pie_data["HQ"]["labels"]


class TestValidation:
    def test_rejects_non_dataframe(self):
        with pytest.raises(ValueError, match="DataFrame"):
            USMapPieChartView._build_pie_data_from_columns(
                {"not": "a df"}, "Map Key", VALUE_COLS, LABELS, COLORS
            )

    def test_rejects_missing_location_column(self, fy2025_drp_df):
        with pytest.raises(ValueError, match="location_column 'Center' not in"):
            USMapPieChartView._build_pie_data_from_columns(
                fy2025_drp_df, "Center", VALUE_COLS, LABELS, COLORS
            )

    def test_rejects_missing_value_column(self, fy2025_drp_df):
        with pytest.raises(ValueError, match="value_columns not found"):
            USMapPieChartView._build_pie_data_from_columns(
                fy2025_drp_df, "Map Key", ["Bogus Column"], ["X"], ["#000"]
            )

    def test_rejects_null_value_in_mapped_row(self):
        df = pd.DataFrame(
            [("ARC", "Ames", 942, None), ("HQ", "HQ", 1382, 459)],
            columns=["Map Key", "Name", "Estimated Final Population", "Departing"],
        )
        with pytest.raises(ValueError, match=r"ARC.*null"):
            USMapPieChartView._build_pie_data_from_columns(
                df,
                "Map Key",
                ["Estimated Final Population", "Departing"],
                ["A", "B"],
                ["#000", "#fff"],
            )

    def test_rejects_non_numeric_value_in_mapped_row(self):
        df = pd.DataFrame(
            [("ARC", "Ames", 942, "abc")],
            columns=["Map Key", "Name", "Estimated Final Population", "Departing"],
        )
        with pytest.raises(ValueError, match=r"ARC.*non-numeric"):
            USMapPieChartView._build_pie_data_from_columns(
                df,
                "Map Key",
                ["Estimated Final Population", "Departing"],
                ["A", "B"],
                ["#000", "#fff"],
            )


class TestEdgeCases:
    def test_empty_dataframe(self):
        df = pd.DataFrame(
            columns=[
                "Map Key",
                "Estimated Final Population",
                "Total Civil Servants Departing Agency",
            ]
        )
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        assert pie_data == {}

    def test_single_row(self):
        df = pd.DataFrame(
            [("ARC", 942, 283)],
            columns=[
                "Map Key",
                "Estimated Final Population",
                "Total Civil Servants Departing Agency",
            ],
        )
        pie_data = USMapPieChartView._build_pie_data_from_columns(
            df, "Map Key", VALUE_COLS, LABELS, COLORS
        )
        assert list(pie_data.keys()) == ["ARC"]
        assert pie_data["ARC"]["values"] == [942.0, 283.0]

    def test_all_rows_unmapped(self, caplog):
        df = pd.DataFrame(
            [("", "A", 100, 50), ("", "B", 200, 75)],
            columns=[
                "Map Key",
                "Name",
                "Estimated Final Population",
                "Total Civil Servants Departing Agency",
            ],
        )
        with caplog.at_level(logging.INFO, logger="tpsplots.views.us_map_pie_charts"):
            pie_data = USMapPieChartView._build_pie_data_from_columns(
                df, "Map Key", VALUE_COLS, LABELS, COLORS
            )
        assert pie_data == {}
        assert "2" in caplog.text  # both dropped
