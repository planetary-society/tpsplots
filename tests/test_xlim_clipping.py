"""Tests for clipping plotted data to configured xlim bounds.

When a YAML sets xlim tighter than the data range, out-of-range points used
to render as partially clipped markers at the axes edges and inflate the y
autoscale. LineChartView._clip_to_xlim drops those points before plotting.
"""

from datetime import date

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

matplotlib.use("Agg")


@pytest.fixture
def numeric_df():
    return pd.DataFrame(
        {
            "Year": list(range(2000, 2011)),
            "Budget": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200],
            "Share": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0],
        }
    )


@pytest.fixture
def datetime_df():
    return pd.DataFrame(
        {
            "Date": pd.date_range("2000-01-01", periods=11, freq="YS"),
            "Budget": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200],
        }
    )


def _line_xdata(fig):
    return fig.get_axes()[0].get_lines()[0].get_xdata()


class TestNumericXlim:
    def test_points_outside_bounds_dropped(self, line_view, numeric_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            xlim=[2003, 2008],
        )
        xdata = _line_xdata(fig)
        assert len(xdata) == 6
        assert min(xdata) == 2003
        assert max(xdata) == 2008
        plt.close(fig)

    def test_wider_bounds_are_noop(self, line_view, numeric_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            xlim=[1990, 2030],
        )
        assert len(_line_xdata(fig)) == len(numeric_df)
        plt.close(fig)

    def test_dict_xlim_clips(self, line_view, numeric_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            xlim={"left": 2005, "right": 2009},
        )
        xdata = _line_xdata(fig)
        assert len(xdata) == 5
        assert min(xdata) == 2005
        plt.close(fig)

    def test_y_autoscale_ignores_hidden_points(self, line_view, desktop_style):
        df = pd.DataFrame(
            {
                "Year": [2000, 2001, 2002, 2003, 2004],
                "Budget": [100, 110, 120, 130, 5000],
            }
        )
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=df,
            x="Year",
            y="Budget",
            xlim=[2000, 2003],
        )
        assert fig.get_axes()[0].get_ylim()[1] < 1000
        plt.close(fig)

    def test_inverted_limits_clip_by_ordered_bounds_and_preserve_direction(
        self, line_view, numeric_df, desktop_style
    ):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            xlim=[2008, 2003],
        )
        xdata = _line_xdata(fig)
        assert len(xdata) == 6
        assert min(xdata) == 2003
        assert max(xdata) == 2008
        assert fig.get_axes()[0].get_xlim() == pytest.approx((2008, 2003))
        plt.close(fig)


class TestDatetimeXlim:
    def test_date_bounds_clip_datetime_x(self, line_view, datetime_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=datetime_df,
            x="Date",
            y="Budget",
            xlim=[date(2003, 1, 1), date(2008, 1, 1)],
        )
        assert len(_line_xdata(fig)) == 6
        plt.close(fig)

    def test_integer_year_bounds_clip_datetime_x(self, line_view, datetime_df, desktop_style):
        """Year-like xlim values are converted to datetimes before comparison."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=datetime_df,
            x="Date",
            y="Budget",
            xlim=[2003, 2008],
        )
        assert len(_line_xdata(fig)) == 6
        plt.close(fig)


class TestFailOpen:
    def test_incomparable_bounds_leave_data_untouched(self, line_view, desktop_style):
        """Categorical x with numeric xlim cannot be compared; nothing is dropped."""
        df = pd.DataFrame({"Label": ["A", "B", "C", "D"], "Value": [1, 2, 3, 4]})
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=df,
            x="Label",
            y="Value",
            xlim=[1, 2],
        )
        assert len(_line_xdata(fig)) == 4
        plt.close(fig)

    def test_no_xlim_is_noop(self, line_view, numeric_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
        )
        assert len(_line_xdata(fig)) == len(numeric_df)
        plt.close(fig)


class TestClipPropagation:
    def test_right_axis_series_clipped_with_same_mask(self, line_view, numeric_df, desktop_style):
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            y_right="Share",
            xlim=[2003, 2008],
        )
        left_ax, right_ax = fig.get_axes()
        assert len(left_ax.get_lines()[0].get_xdata()) == 6
        assert len(right_ax.get_lines()[0].get_xdata()) == 6
        plt.close(fig)

    def test_scatter_view_clips(self, scatter_view, numeric_df, desktop_style):
        fig = scatter_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=numeric_df,
            x="Year",
            y="Budget",
            xlim=[2003, 2008],
        )
        assert len(_line_xdata(fig)) == 6
        plt.close(fig)
