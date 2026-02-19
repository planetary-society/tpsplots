"""Tests for dual y-axis (left + right) rendering on line and scatter charts.

Covers:
- Twin axes creation and patch visibility
- Left/right axis limits, labels, and scaling
- Combined legend across both axes
- Grid on left axis only
- Backward compatibility (no y_right = single axis, unchanged behavior)
- Series offset for override key lookup
- Line artists remain clipped to axis bounds
- Scatter dual axis inheritance
"""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from tpsplots.views.line_chart import LineChartView
from tpsplots.views.scatter_chart import ScatterChartView

matplotlib.use("Agg")


@pytest.fixture
def line_view(tmp_path):
    return LineChartView(outdir=tmp_path, style_file=None)


@pytest.fixture
def scatter_view(tmp_path):
    return ScatterChartView(outdir=tmp_path, style_file=None)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "Year": [2020, 2021, 2022, 2023],
            "Budget": [100, 120, 130, 150],
            "Spending": [95, 115, 125, 140],
            "GDP_Pct": [3.2, 3.5, 3.1, 3.8],
        }
    )


@pytest.fixture
def desktop_style():
    return {
        "type": "desktop",
        "figsize": (16, 9),
        "dpi": 100,
        "title_size": 20,
        "subtitle_size": 14,
        "tick_size": 12,
        "label_size": 14,
        "legend_size": 12,
        "line_width": 2,
        "marker_size": 6,
        "tick_rotation": 0,
        "grid": True,
        "grid_axis": "y",
        "header_height": 0.15,
        "footer_height": 0.05,
    }


class TestDualAxisCreation:
    def test_creates_twin_axes(self, line_view, sample_df, desktop_style):
        """y_right produces a second axes on the figure via twinx()."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            y_right="GDP_Pct",
        )
        axes = fig.get_axes()
        assert len(axes) == 2
        plt.close(fig)

    def test_ax2_patch_not_visible(self, line_view, sample_df, desktop_style):
        """Right-axis background must be invisible to not hide left-axis content."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
        )
        axes = fig.get_axes()
        ax2 = axes[1]
        assert ax2.patch.get_visible() is False
        plt.close(fig)

    def test_no_y_right_is_single_axis(self, line_view, sample_df, desktop_style):
        """Without y_right, only one axes exists (backward compatibility)."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
        )
        axes = fig.get_axes()
        assert len(axes) == 1
        plt.close(fig)


class TestAxisStyling:
    def test_right_axis_label(self, line_view, sample_df, desktop_style):
        """ylabel_right is rendered on the right y-axis."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            ylabel_right="% of GDP",
        )
        ax2 = fig.get_axes()[1]
        assert ax2.get_ylabel() == "% of GDP"
        plt.close(fig)

    def test_left_axis_limits(self, line_view, sample_df, desktop_style):
        """ylim applies to the left axis only."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            ylim=[0, 200],
        )
        ax = fig.get_axes()[0]
        assert ax.get_ylim() == (0, 200)
        plt.close(fig)

    def test_right_axis_limits(self, line_view, sample_df, desktop_style):
        """ylim_right applies to the right axis."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            ylim_right=[0, 10],
        )
        ax2 = fig.get_axes()[1]
        assert ax2.get_ylim() == (0, 10)
        plt.close(fig)

    def test_no_grid_on_right_axis(self, line_view, sample_df, desktop_style):
        """Right axis grid is explicitly disabled to prevent double gridlines."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            grid=True,
        )
        ax2 = fig.get_axes()[1]
        # matplotlib stores grid visibility per axis; check that y-axis grid is off
        assert not ax2.yaxis.get_gridlines()[0].get_visible()
        plt.close(fig)


class TestSeriesStyling:
    def test_combined_legend(self, line_view, sample_df, desktop_style):
        """Legend includes series from both axes."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            y_right="GDP_Pct",
            labels=["Budget", "Spending", "% GDP"],
            color=["blue", "red", "green"],
            legend=True,
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "Budget" in legend_texts
        assert "Spending" in legend_texts
        assert "% GDP" in legend_texts
        plt.close(fig)

    def test_colors_span_both_axes(self, line_view, sample_df, desktop_style):
        """Colors array spans [left..., right...] order."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            color=["blue", "red"],
        )
        ax = fig.get_axes()[0]
        ax2 = fig.get_axes()[1]
        # Left axis line should be blue
        left_line = ax.get_lines()[0]
        assert left_line.get_color() == "blue"
        # Right axis line should be red
        right_line = ax2.get_lines()[0]
        assert right_line.get_color() == "red"
        plt.close(fig)

    def test_series_offset_override(self, line_view, sample_df, desktop_style):
        """series_2 override applies to the first right-axis series when left has 2."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            y_right="GDP_Pct",
            series_2={"linewidth": 5},
        )
        ax2 = fig.get_axes()[1]
        right_line = ax2.get_lines()[0]
        assert right_line.get_linewidth() == 5
        plt.close(fig)

    def test_backward_compat_series_overrides(self, line_view, sample_df, desktop_style):
        """series_0/series_1 work identically without y_right."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            series_0={"linewidth": 4},
            series_1={"linewidth": 6},
        )
        ax = fig.get_axes()[0]
        lines = ax.get_lines()
        assert lines[0].get_linewidth() == 4
        assert lines[1].get_linewidth() == 6
        plt.close(fig)


class TestScaleFormatting:
    def test_scale_right(self, line_view, sample_df, desktop_style):
        """Right axis scale formatting works via scale_right."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            scale_right="percentage",
        )
        # Just verify no error — scale formatting is tested via formatter existence
        ax2 = fig.get_axes()[1]
        formatter = ax2.yaxis.get_major_formatter()
        assert formatter is not None
        plt.close(fig)

    def test_y_tick_format_right(self, line_view, sample_df, desktop_style):
        """y_tick_format_right applies a custom format to right axis ticks."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            y_tick_format_right=".1f",
        )
        ax2 = fig.get_axes()[1]
        # Verify the formatter produces expected output
        formatter = ax2.yaxis.get_major_formatter()
        assert formatter(3.14159, 0) == "3.1"
        plt.close(fig)


class TestClipping:
    def test_clip_on_true_both_axes(self, line_view, sample_df, desktop_style):
        """Line artists stay clipped so out-of-range segments do not render outside bounds."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
            marker="o",
            xlim=[2020, 2022],
        )
        ax = fig.get_axes()[0]
        ax2 = fig.get_axes()[1]
        for line in ax.get_lines():
            assert line.get_clip_on() is True
        for line in ax2.get_lines():
            assert line.get_clip_on() is True
        plt.close(fig)


class TestEdgeCases:
    def test_single_y_right_series(self, line_view, sample_df, desktop_style):
        """y_right as a scalar string (single column) works."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
        )
        ax2 = fig.get_axes()[1]
        assert len(ax2.get_lines()) == 1
        plt.close(fig)

    def test_multiple_y_right_series(self, line_view, sample_df, desktop_style):
        """y_right as a list of columns works."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right=["Spending", "GDP_Pct"],
        )
        ax2 = fig.get_axes()[1]
        assert len(ax2.get_lines()) == 2
        plt.close(fig)

    def test_raw_array_dual_axis(self, line_view, desktop_style):
        """Dual axis works with raw arrays (no DataFrame)."""
        x = [1, 2, 3, 4]
        y_left = [[10, 20, 30, 40]]
        y_right = [[0.1, 0.2, 0.3, 0.4]]
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            x=x,
            y=y_left,
            y_right=y_right,
        )
        axes = fig.get_axes()
        assert len(axes) == 2
        plt.close(fig)


class TestLabelSemantics:
    def test_labels_none_generates_auto_labels(self, line_view, sample_df, desktop_style):
        """Without explicit labels, each series gets a 'Series N' auto-label."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            y_right="GDP_Pct",
            legend=True,
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "Series 1" in legend_texts
        assert "Series 2" in legend_texts
        assert "Series 3" in legend_texts
        plt.close(fig)

    def test_labels_none_single_axis_auto_labels(self, line_view, sample_df, desktop_style):
        """Without y_right, labels=None still produces auto-labels (backward compat)."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            legend=True,
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert "Series 1" in legend_texts
        assert "Series 2" in legend_texts
        plt.close(fig)

    def test_scalar_label_only_first_series(self, line_view, sample_df, desktop_style):
        """Scalar label applies only to the first series, not duplicated to all."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            labels="My Label",
            legend=True,
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert legend_texts.count("My Label") == 1
        plt.close(fig)

    def test_scalar_label_dual_axis_no_duplicate(self, line_view, sample_df, desktop_style):
        """Scalar label in dual-axis mode applies only to the first left-axis series."""
        fig = line_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y=["Budget", "Spending"],
            y_right="GDP_Pct",
            labels="Budget",
            legend=True,
        )
        ax = fig.get_axes()[0]
        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert legend_texts.count("Budget") == 1
        plt.close(fig)


class TestScatterDualAxis:
    def test_scatter_dual_axis(self, scatter_view, sample_df, desktop_style):
        """Scatter chart inherits dual y-axis support from LineChartView."""
        fig = scatter_view._create_chart(
            metadata={"title": "Test"},
            style=desktop_style,
            data=sample_df,
            x="Year",
            y="Budget",
            y_right="GDP_Pct",
        )
        axes = fig.get_axes()
        assert len(axes) == 2
        plt.close(fig)
