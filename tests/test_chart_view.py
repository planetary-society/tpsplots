"""Tests for ChartView base behavior."""

from pathlib import Path

from tpsplots.views.chart_view import ChartView


class MutatingChartView(ChartView):
    """Minimal view that intentionally mutates nested kwargs in _create_chart."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)
        self.legend_snapshots = []

    def _create_chart(self, metadata, style, **kwargs):
        legend = kwargs["legend"]
        legend["fontsize"] = style["legend_size"]
        legend.setdefault("rendered_for", []).append(style["type"])
        self.legend_snapshots.append(legend)
        return object()

    def _save_chart(self, *_args, **_kwargs):
        return []


def test_generate_chart_isolates_nested_kwargs_between_renders(tmp_path):
    """Desktop and mobile renders should not share nested kwargs state."""
    view = MutatingChartView(outdir=tmp_path)
    legend = {"ncol": 4}

    view.generate_chart(metadata={}, stem="test", legend=legend)

    # Caller-supplied kwargs should not be mutated by chart generation.
    assert legend == {"ncol": 4}

    desktop_legend, mobile_legend = view.legend_snapshots
    assert desktop_legend["rendered_for"] == ["desktop"]
    assert mobile_legend["rendered_for"] == ["mobile"]


class FileTrackingChartView(ChartView):
    """Minimal view that returns deterministic file paths for save/export."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)

    def _create_chart(self, metadata, style, **kwargs):
        return object()

    def _save_chart(self, fig, filename, metadata, create_pptx=False):
        files = [
            str(self.outdir / f"{filename}.svg"),
            str(self.outdir / f"{filename}.png"),
        ]
        if create_pptx:
            files.append(str(self.outdir / f"{filename.replace('_desktop', '')}.pptx"))
        return files

    def _export_csv(self, df, metadata, stem):
        return Path(self.outdir / f"{stem}.csv")


def test_generate_chart_reports_generated_files(tmp_path):
    """generate_chart should include all output file paths in result['files']."""
    view = FileTrackingChartView(outdir=tmp_path)
    result = view.generate_chart(metadata={}, stem="budget", export_data=object())

    expected = [
        str(tmp_path / "budget_desktop.svg"),
        str(tmp_path / "budget_desktop.png"),
        str(tmp_path / "budget.pptx"),
        str(tmp_path / "budget_mobile.svg"),
        str(tmp_path / "budget_mobile.png"),
        str(tmp_path / "budget.csv"),
    ]
    assert result["files"] == expected
