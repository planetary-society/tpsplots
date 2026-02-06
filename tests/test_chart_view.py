"""Tests for ChartView base behavior."""

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
        return None


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
