"""Tests for ChartView base behavior."""

from pathlib import Path

import matplotlib.pyplot as plt
import pytest

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
    """Desktop, mobile, and social renders should not share nested kwargs state."""
    view = MutatingChartView(outdir=tmp_path)
    legend = {"ncol": 4}

    view.generate_chart(metadata={}, stem="test", legend=legend)

    # Caller-supplied kwargs should not be mutated by chart generation.
    assert legend == {"ncol": 4}

    desktop_legend, mobile_legend, social_legend = view.legend_snapshots
    assert desktop_legend["rendered_for"] == ["desktop"]
    assert mobile_legend["rendered_for"] == ["mobile"]
    assert social_legend["rendered_for"] == ["social"]


class FileTrackingChartView(ChartView):
    """Minimal view that returns deterministic file paths for save/export."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)

    def _create_chart(self, metadata, style, **kwargs):
        return object()

    def _save_chart(self, fig, filename, metadata, create_pptx=False, create_svg=True):
        files = []
        if create_svg:
            files.append(str(self.outdir / f"{filename}.svg"))
        files.append(str(self.outdir / f"{filename}.png"))
        if create_pptx:
            files.append(str(self.outdir / f"{filename.replace('_desktop', '')}.pptx"))
        return files

    def _export_csv(self, df, metadata, stem):
        return Path(self.outdir / f"{stem}.csv")


def test_clone_chart_kwargs_isolates_dataframes():
    """Top-level DataFrame/Series kwargs must be deep-copied so device renders
    cannot mutate a shared frame."""
    import pandas as pd

    original_df = pd.DataFrame({"a": [1, 2, 3]})
    original_series = pd.Series([1, 2, 3])

    cloned = ChartView._clone_chart_kwargs({"df": original_df, "s": original_series})

    assert cloned["df"] is not original_df
    assert cloned["s"] is not original_series

    cloned["df"].loc[0, "a"] = 999
    cloned["s"].iloc[0] = 999

    assert original_df.loc[0, "a"] == 1
    assert original_series.iloc[0] == 1


def test_generate_chart_returns_only_files(tmp_path):
    """generate_chart returns just the file list; device figures are saved and
    closed internally, not handed back to callers."""
    view = FileTrackingChartView(outdir=tmp_path)
    result = view.generate_chart(metadata={}, stem="budget")

    assert set(result) == {"files"}


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
        str(tmp_path / "budget_social.png"),
        str(tmp_path / "budget.csv"),
    ]
    assert result["files"] == expected


class SingleDeviceChartView(ChartView):
    """Minimal view for testing create_figure."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)
        self.create_calls = []

    def _create_chart(self, metadata, style, **kwargs):
        self.create_calls.append(style["type"])
        return object()


def test_create_figure_renders_single_device(tmp_path):
    """create_figure should only invoke _create_chart once for the requested device."""
    view = SingleDeviceChartView(outdir=tmp_path)

    fig = view.create_figure(metadata={"title": "Test"}, device="mobile", legend=True)

    assert fig is not None
    assert view.create_calls == ["mobile"]


def test_create_figure_defaults_to_desktop(tmp_path):
    """create_figure with no device argument should render desktop."""
    view = SingleDeviceChartView(outdir=tmp_path)

    view.create_figure(metadata={"title": "Test"})

    assert view.create_calls == ["desktop"]


def test_create_figure_ignores_export_data(tmp_path):
    """create_figure should silently discard export_data without error."""
    view = SingleDeviceChartView(outdir=tmp_path)

    fig = view.create_figure(metadata={}, export_data=object())

    assert fig is not None
    assert len(view.create_calls) == 1


def test_transition_quarter_timeline_is_not_a_datetime_axis(tmp_path):
    view = ChartView(outdir=tmp_path, style_file=None)

    assert view._contains_dates(["1975", "1976", "1976 TQ", "1977"]) is False


def test_transition_quarter_with_non_string_first_element_is_not_a_datetime_axis(tmp_path):
    """A mixed column whose first element is an int must still detect the TQ label."""
    view = ChartView(outdir=tmp_path, style_file=None)

    assert view._contains_dates([1976, "1976 TQ", 1977]) is False


def test_ordinary_fiscal_year_labels_are_a_datetime_axis(tmp_path):
    view = ChartView(outdir=tmp_path, style_file=None)

    assert view._contains_dates(["1975", "1976", "1977"]) is True


def test_save_chart_uses_figure_dpi_for_svg_and_png(tmp_path, monkeypatch):
    """_save_chart should rely on figure DPI as the single source of truth."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure()
    save_calls: list[tuple[str, str | None, int | None]] = []

    def fake_savefig(path, **kwargs):
        save_calls.append((str(path), kwargs.get("format"), kwargs.get("dpi")))

    monkeypatch.setattr(fig, "savefig", fake_savefig)
    view._save_chart(fig, "dpi_test", metadata={}, create_pptx=False)

    assert len(save_calls) == 2
    assert save_calls[0][1] == "svg"
    assert save_calls[0][2] == "figure"
    assert save_calls[1][1] == "png"
    assert save_calls[1][2] == "figure"


def test_add_header_wraps_subtitle_within_figure_width(tmp_path):
    """Subtitle wrapping should keep rendered text within left/right header margins."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])
    metadata = {
        "title": "NASA contract awards in FY 2026",
        "subtitle": (
            "An extended government shutdown and budgetary uncertainty led NASA to "
            "award contracts at a slower pace than any time in the past 20 years."
        ),
    }

    view._add_header(fig, metadata, style)
    fig.canvas.draw()

    # Title is added first, subtitle second.
    subtitle_text = fig.texts[1]
    subtitle_bbox = subtitle_text.get_window_extent(fig.canvas.get_renderer())
    fig_width_px = fig.get_figwidth() * fig.dpi

    # Header text uses x=0.01 left margin and should remain within x=0.99 right margin.
    assert subtitle_bbox.x0 >= fig_width_px * 0.01 - 1
    assert subtitle_bbox.x1 <= fig_width_px * 0.99 + 1
    plt.close(fig)


def test_add_header_uses_tighter_subtitle_line_spacing(tmp_path):
    """Multiline subtitles should use the subtitle-specific line spacing."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    view._add_header(
        fig,
        {"title": "Test title", "subtitle": "First subtitle line\nSecond subtitle line"},
        style,
    )

    assert fig.texts[1].get_linespacing() == 1.05
    plt.close(fig)


def test_add_header_nestles_subtitle_slightly_closer_to_title(tmp_path):
    """The first subtitle line is pulled up into the title's box to hug it.

    The title→subtitle gap is deterministic: the subtitle's top anchor sits a
    fixed fraction of a SINGLE subtitle line box *above* the title's
    glyph-independent bottom (an overlap that reclaims the subtitle's ascender
    whitespace), matching the eyebrow→title rhythm and independent of how many
    lines the subtitle wraps to. Leftover slack stays below the subtitle.
    """
    from tpsplots.views.style import tokens

    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig, ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    metadata = {
        "title": "The cost of NASA's Viking missions to Mars",
        "subtitle": "First subtitle line\nSecond subtitle line\nThird subtitle line",
    }
    ax.set_position([0.1, 0.1, 0.8, 0.7])

    title_text, subtitle_text = view._add_header(fig, metadata, style)
    fig.canvas.draw()
    fig_height_px = fig.get_figheight() * fig.dpi

    view._center_subtitle_vertically(fig, title_text, subtitle_text, style, 0.1)
    fig.canvas.draw()

    # The subtitle top is pulled ABOVE the title's glyph-independent bottom (its
    # descender line) by a fraction of a single TITLE line box, reclaiming the
    # title's descender depth so the subtitle hugs the baseline.
    title_bottom_y = title_text.get_position()[1] - view._measure_text_height(
        fig,
        title_text.get_text(),
        title_text.get_fontsize(),
        linespacing=title_text.get_linespacing(),
    )
    title_line_height = view._measure_text_height(
        fig,
        view._METRIC_REFERENCE_GLYPHS,
        title_text.get_fontsize(),
        linespacing=title_text.get_linespacing(),
    )
    overlap = subtitle_text.get_position()[1] - title_bottom_y
    assert overlap == pytest.approx(
        title_line_height * tokens.TITLE_SUBTITLE_OVERLAP_RATIO, abs=1 / fig_height_px
    )
    assert overlap > 0  # subtitle sits above the title box bottom (hugging it)

    # The subtitle nestles toward the title: the visible gap above it is
    # smaller than the gap below it (down to the plot).
    renderer = fig.canvas.get_renderer()
    title_bbox = title_text.get_window_extent(renderer)
    subtitle_bbox = subtitle_text.get_window_extent(renderer)
    upper_gap = (title_bbox.y0 - subtitle_bbox.y1) / fig_height_px
    lower_gap = subtitle_bbox.y0 / fig_height_px - ax.get_position().y1
    assert upper_gap < lower_gap
    plt.close(fig)


def test_center_subtitle_is_bottom_anchored(tmp_path):
    """Nestling the subtitle must grow the plot's top up, never lift its bottom.

    The old behaviour translated the whole plot upward to close the subtitle
    gap, which vacated an equal band of dead space above the footer. The plot
    bottom must stay put (footer side stays filled) while the top rises.
    """
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig, ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    metadata = {
        "title": "The cost of NASA's Viking missions to Mars",
        "subtitle": "First subtitle line\nSecond subtitle line\nThird subtitle line",
    }
    ax.set_position([0.1, 0.1, 0.8, 0.7])
    bottom_before = ax.get_position().y0
    top_before = ax.get_position().y1

    title_text, subtitle_text = view._add_header(fig, metadata, style)
    fig.canvas.draw()
    view._center_subtitle_vertically(fig, title_text, subtitle_text, style, 0.1)

    tolerance = 1 / (fig.get_figheight() * fig.dpi)
    # Bottom is anchored (footer side stays filled)...
    assert ax.get_position().y0 == pytest.approx(bottom_before, abs=tolerance)
    # ...and the top grew upward to nestle under the subtitle.
    assert ax.get_position().y1 > top_before
    plt.close(fig)


def test_calculate_header_height_measures_multiline_subtitle(tmp_path):
    """Wrapped subtitle lines must contribute their rendered height to the header."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])
    metadata = {
        "title": "The cost of NASA's Viking missions to Mars",
        "subtitle": "First subtitle line\nSecond subtitle line\nThird subtitle line",
    }

    header_height = view._calculate_header_height(fig, metadata, style)

    assert header_height > style["header_height"]
    plt.close(fig)


# ── Descender-proof header metrics ─────────────────────────────────
# Header vertical rhythm must be identical regardless of which glyphs appear:
# a subtitle full of gerund descenders ("comparing spending") and an all-caps
# one ("NASA'S BUDGET") must reserve the same space and sit at the same offsets.


def test_measure_text_height_is_glyph_independent(tmp_path):
    """_measure_text_height depends only on line count/size/spacing, not glyphs."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(8, 9), dpi=300)

    descenders = view._measure_text_height(fig, "comparing spending programs", 17)
    all_caps = view._measure_text_height(fig, "NASA'S BUDGET IN CONTEXT", 17)
    brackets = view._measure_text_height(fig, "Budget (FY2026) [±$4.1B]", 17)

    assert descenders == all_caps == brackets
    # Two lines must be taller than one, and the same regardless of glyphs.
    two_desc = view._measure_text_height(fig, "spending gjpqy\ncomparing yjgq", 17)
    two_caps = view._measure_text_height(fig, "NASA BUDGET\nIN CONTEXT", 17)
    assert two_desc == two_caps
    assert two_desc > descenders
    plt.close(fig)


def _header_gaps(view, style, title, subtitle):
    """Return (title->subtitle gap, subtitle->plot gap) in px for a header."""
    fig, ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    ax.set_position([0.1, 0.1, 0.8, 0.6])
    metadata = {"title": title, "subtitle": subtitle}
    header_height = view._calculate_header_height(fig, metadata, style)
    title_text, subtitle_text = view._add_header(fig, metadata, style)
    fig.canvas.draw()
    view._center_subtitle_vertically(fig, title_text, subtitle_text, style, header_height)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    height_px = fig.get_figheight() * fig.dpi
    tb = title_text.get_window_extent(renderer)
    sb = subtitle_text.get_window_extent(renderer)
    plot_top_px = ax.get_position().y1 * height_px
    plt.close(fig)
    return (tb.y0 - sb.y1), (sb.y0 - plot_top_px), header_height


def test_header_gaps_are_descender_independent(tmp_path):
    """Title->subtitle and subtitle->plot gaps must match to within 1px across glyphs."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    # Same title; subtitles differ ONLY in descenders / letter case.
    desc = _header_gaps(view, style, "NASA budget in context", "Comparing spending programs")
    caps = _header_gaps(view, style, "NASA budget in context", "NASA'S BUDGET IN CONTEXT")

    assert abs(desc[0] - caps[0]) <= 1.0  # title -> subtitle gap
    assert abs(desc[1] - caps[1]) <= 1.0  # subtitle -> plot gap
    assert desc[2] == caps[2]  # header height identical


def test_layout_aligns_decoration_free_chart_with_header_and_footer(tmp_path):
    """A chart without ticks should share the header/footer horizontal extent."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig, ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    ax.set_axis_off()
    metadata = {"title": "Aligned title", "source": "Aligned source"}

    view._adjust_layout_for_header_footer(fig, metadata, style)

    target_left, target_right = style["footer_extent"]
    position = ax.get_position()
    tolerance = 1 / (fig.get_figwidth() * fig.dpi)
    assert position.x0 == pytest.approx(target_left, abs=tolerance)
    assert position.x1 == pytest.approx(target_right, abs=tolerance)
    plt.close(fig)


def test_layout_stretches_decoration_free_chart_within_header_and_footer(tmp_path):
    """A chart without ticks should fill the usable vertical layout zone."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig, ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    ax.set_axis_off()
    metadata = {"title": "Chart title", "source": "Chart source"}

    view._adjust_layout_for_header_footer(fig, metadata, style)

    header_height = max(
        view._calculate_header_height(fig, metadata, style),
        style["header_height"],
    )
    position = ax.get_position()
    tolerance = 1 / (fig.get_figheight() * fig.dpi)
    assert position.y0 == pytest.approx(
        style["footer_height"] + style["chart_vertical_padding"],
        abs=tolerance,
    )
    assert position.y1 == pytest.approx(
        1.0 - header_height - style["chart_vertical_padding"],
        abs=tolerance,
    )
    plt.close(fig)


# ── _center_axes_vertically tests ──────────────────────────────────


def _measure_gaps(fig, header_height, footer_height):
    """Return (top_gap, bottom_gap) between axes visual extent and reference lines."""
    renderer = fig.canvas.get_renderer()
    y_mins, y_maxes = [], []
    for ax in fig.get_axes():
        if not ax.get_visible():
            continue
        bbox = ax.get_tightbbox(renderer)
        if bbox is not None:
            fig_bbox = bbox.transformed(fig.transFigure.inverted())
            y_mins.append(fig_bbox.y0)
            y_maxes.append(fig_bbox.y1)
    ref_top = 1.0 - header_height
    ref_bottom = footer_height / 2.0 if footer_height > 0 else 0.0
    return ref_top - max(y_maxes), min(y_mins) - ref_bottom


def test_center_axes_equalizes_gaps(tmp_path):
    """After centering, top and bottom gaps should be roughly equal."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.12, 0.08

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    # Large tick labels on bottom create asymmetry
    ax.set_yticks([0, 50, 100])
    ax.set_yticklabels(["$0B", "$50B", "$100B"], fontsize=14)
    ax.set_xlabel("Fiscal Year", fontsize=12)
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    top_before, bottom_before = _measure_gaps(fig, header_height, footer_height)
    # There should be meaningful asymmetry before centering
    gap_diff_before = abs(bottom_before - top_before)

    view._center_axes_vertically(fig, header_height, footer_height)

    top_after, bottom_after = _measure_gaps(fig, header_height, footer_height)
    gap_diff_after = abs(bottom_after - top_after)

    # Centering should reduce the gap difference
    assert gap_diff_after <= gap_diff_before + 0.001
    # Gaps should be close to equal (within 1% of figure height)
    assert gap_diff_after < 0.01
    plt.close(fig)


def test_center_axes_noop_when_already_centered(tmp_path):
    """Centering should be a no-op when gaps are within threshold."""
    view = ChartView(outdir=tmp_path, style_file=None)
    # With no header/footer, ref_top=1.0 and ref_bottom=0.0, so tight_layout
    # already centers the axes symmetrically → shift should be below threshold.
    header_height, footer_height = 0, 0

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    ax.axis("off")
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    pos_before = ax.get_position()
    view._center_axes_vertically(fig, header_height, footer_height)
    pos_after = ax.get_position()

    # Position should not change (shift < threshold)
    assert abs(pos_after.y0 - pos_before.y0) < 0.005
    plt.close(fig)


def test_center_axes_skips_hidden_axes(tmp_path):
    """Hidden axes should not influence centering calculations."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.12, 0.08

    fig = plt.figure(figsize=(8, 9), dpi=150)
    ax1 = fig.add_subplot(111)
    ax1.set_yticks([0, 100])

    # Add a hidden axes placed far off
    ax_hidden = fig.add_axes([0.1, 0.95, 0.8, 0.04], visible=False)
    ax_hidden.set_yticks([0, 1])

    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    pos_hidden_before = ax_hidden.get_position()

    view._center_axes_vertically(fig, header_height, footer_height)

    # Hidden axes should not move
    pos_hidden_after = ax_hidden.get_position()
    assert abs(pos_hidden_after.y0 - pos_hidden_before.y0) < 1e-9
    plt.close(fig)


def test_center_axes_empty_figure(tmp_path):
    """Centering an empty figure should not raise."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(8, 9))

    # No axes at all — should be a silent no-op
    view._center_axes_vertically(fig, 0.12, 0.08)
    plt.close(fig)


def test_center_axes_respects_zone_bounds(tmp_path):
    """Axes visual extent should stay within the tight_layout zone after centering."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.15, 0.10

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    ax.set_yticks(range(0, 1001, 100))
    ax.set_yticklabels([f"${v}B" for v in range(0, 1001, 100)], fontsize=12)
    ax.set_xlabel("Year", fontsize=14, labelpad=20)
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    view._center_axes_vertically(fig, header_height, footer_height)

    # Verify axes data-area position stays within zone
    zone_top = 1.0 - header_height
    zone_bottom = footer_height
    for a in fig.get_axes():
        pos = a.get_position()
        assert pos.y0 >= zone_bottom - 0.01, f"Axes bottom {pos.y0} below zone {zone_bottom}"
        assert pos.y1 <= zone_top + 0.01, f"Axes top {pos.y1} above zone {zone_top}"
    plt.close(fig)


def test_social_style_produces_correct_dimensions(tmp_path):
    """SOCIAL renders at 300 dpi -> 2400x1260 px (same 40:21 OG ratio, crisper)."""
    style = ChartView.SOCIAL
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])
    assert fig.get_figwidth() * fig.dpi == 2400
    assert fig.get_figheight() * fig.dpi == 1260
    plt.close(fig)


def test_social_style_disables_header_but_keeps_footer(tmp_path):
    """Social style should skip header but render footer (source attribution)."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.SOCIAL)
    fig, _ax = plt.subplots(figsize=style["figsize"], dpi=style["dpi"])
    metadata = {"title": "Test Title", "subtitle": "Test subtitle", "source": "Test source"}

    view._adjust_layout_for_header_footer(fig, metadata, style)

    texts = [t.get_text() for t in fig.texts]
    # Header (title/subtitle) should NOT appear
    assert not any("Test Title" in t for t in texts)
    assert not any("Test subtitle" in t for t in texts)
    # Footer source attribution SHOULD appear
    assert any("TEST SOURCE" in t for t in texts)
    plt.close(fig)


def test_social_save_produces_png_only(tmp_path):
    """_save_chart with create_svg=False should only produce a PNG file."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(8, 4.2), dpi=300)

    files = view._save_chart(fig, "test_social", metadata={}, create_svg=False)

    assert len(files) == 1
    assert files[0].endswith(".png")
    assert "test_social.png" in files[0]


def test_create_figure_supports_social_device(tmp_path):
    """create_figure should route device='social' to the SOCIAL style."""
    view = SingleDeviceChartView(outdir=tmp_path)

    view.create_figure(metadata={"title": "Test"}, device="social")

    assert view.create_calls == ["social"]


def test_add_logo_adds_vector_path_patch(tmp_path, monkeypatch):
    """_add_logo should add a vector PathPatch to the figure."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    from tpsplots.views import logo

    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(16, 10), dpi=300)

    # Monkeypatch the cached path with a minimal triangle.
    triangle = MplPath(
        [(0.0, 0.0), (100.0, 0.0), (50.0, 100.0), (0.0, 0.0)],
        [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.CLOSEPOLY],
    )
    monkeypatch.setattr(logo, "_cached_path", triangle)

    view._add_logo(fig, ChartView.DESKTOP)

    patches = [c for c in fig.get_children() if isinstance(c, PathPatch)]
    assert len(patches) == 1
    # Facecolor should match the logo grey (#545454 ≈ 0.329)
    fc = patches[0].get_facecolor()
    assert abs(fc[0] - 0.329) < 0.01
    plt.close(fig)


# ---------------------------------------------------------------------------
# Mobile title wrap (bugfix): long titles must wrap instead of overflowing
# ---------------------------------------------------------------------------
def test_mobile_long_title_wraps_and_grows_header(tmp_path):
    """A long title on the narrow mobile canvas wraps within bounds and enlarges the header."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.MOBILE)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])
    long_title = "Artemis vs Apollo: Annual Spending Comparison"

    # Header height must grow for a wrapped multi-line title vs a short one.
    short_height = view._calculate_header_height(fig, {"title": "NASA"}, style)
    long_height = view._calculate_header_height(fig, {"title": long_title}, style)
    assert long_height > short_height

    title_text, _ = view._add_header(fig, {"title": long_title}, style)
    fig.canvas.draw()

    bbox = title_text.get_window_extent(fig.canvas.get_renderer())
    fig_fraction = bbox.transformed(fig.transFigure.inverted())
    # Rendered title right edge stays within the figure.
    assert fig_fraction.x1 <= 1.0
    # The title actually wrapped onto more than one line.
    assert "\n" in title_text.get_text()
    plt.close(fig)


def test_short_desktop_title_is_not_wrapped(tmp_path):
    """A title that fits on one line is left unchanged (no spurious wrapping)."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    title_text, _ = view._add_header(fig, {"title": "NASA budget"}, style)
    assert title_text.get_text() == "NASA budget"
    plt.close(fig)


# ---------------------------------------------------------------------------
# Eyebrow: desktop-only kicker above the title
# ---------------------------------------------------------------------------
def test_eyebrow_renders_uppercased_on_desktop(tmp_path):
    """DESKTOP + eyebrow set → the uppercased eyebrow text is drawn on the figure."""
    from tpsplots.views.style import tokens

    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    view._add_header(fig, {"title": "T", "eyebrow": "Mission update"}, style)

    eyebrow = next((t for t in fig.texts if t.get_text() == "MISSION UPDATE"), None)
    assert eyebrow is not None
    # Colored from the token, not black.
    assert eyebrow.get_color() == tokens.EYEBROW_COLOR
    plt.close(fig)


def test_eyebrow_pushes_title_down(tmp_path):
    """With an eyebrow present the title starts below the top of the header zone."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    without = view._calculate_header_height(fig, {"title": "T"}, style)
    with_eyebrow = view._calculate_header_height(fig, {"title": "T", "eyebrow": "Kicker"}, style)
    assert with_eyebrow > without
    plt.close(fig)


# ---------------------------------------------------------------------------
# Note: methodology line above the source in the footer
# ---------------------------------------------------------------------------
def test_note_renders_above_source(tmp_path):
    """The note is drawn italic/right-aligned above the source line."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    view._add_footer(
        fig,
        {"source": "NASA", "note": "Estimates only"},
        style,
        style["footer_height"],
    )
    fig.canvas.draw()

    note = next(t for t in fig.texts if t.get_text() == "Estimates only")
    source = next(t for t in fig.texts if "SOURCE: NASA" in t.get_text())
    renderer = fig.canvas.get_renderer()
    assert note.get_window_extent(renderer).y0 > source.get_window_extent(renderer).y0
    assert note.get_style() == "italic"
    assert note.get_ha() == "right"
    plt.close(fig)


def test_note_absent_when_unset(tmp_path):
    """No note metadata → only the source line is drawn (unchanged footer)."""
    view = ChartView(outdir=tmp_path, style_file=None)
    style = dict(view.DESKTOP)
    fig = plt.figure(figsize=style["figsize"], dpi=style["dpi"])

    view._add_footer(fig, {"source": "NASA"}, style, style["footer_height"])

    texts = [t.get_text() for t in fig.texts]
    assert texts == ["SOURCE: NASA"]
    plt.close(fig)


# ---------------------------------------------------------------------------
# Annotations: data-space callouts on the primary axes
# ---------------------------------------------------------------------------
def test_apply_annotations_draws_text_in_rounded_box(tmp_path):
    """metadata['annotations'] → a text artist wrapped in the rounded label box."""
    import matplotlib.colors as mcolors
    from matplotlib.patches import FancyBboxPatch

    from tpsplots.views.style import tokens

    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 2])

    view._apply_annotations(
        fig, {"annotations": [{"x": 1.0, "y": 1.0, "text": "peak"}]}, view.DESKTOP
    )

    note = next(t for t in ax.texts if t.get_text() == "peak")
    box = note.get_bbox_patch()
    assert isinstance(box, FancyBboxPatch)
    # White fill + the default (Lunar Soil) grey border, matching direct labels.
    assert mcolors.to_hex(box.get_facecolor()) == "#ffffff"
    assert mcolors.to_hex(box.get_edgecolor()) == tokens.ANNOTATION_EDGE_COLOR.lower()
    plt.close(fig)


def test_apply_annotations_draws_curved_arrow_when_requested(tmp_path):
    """arrow=True draws a standalone curved FancyArrowPatch (not a Text connector)."""
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.text import Annotation

    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 2])

    view._apply_annotations(
        fig,
        {
            "annotations": [
                {"x": 1.0, "y": 1.0, "text": "peak", "text_x": 1.5, "text_y": 1.8, "arrow": True}
            ]
        },
        view.DESKTOP,
    )

    arrows = [p for p in ax.patches if isinstance(p, FancyArrowPatch)]
    assert len(arrows) == 1
    # Text stays a plain Text with its own box; not an ax.annotate connector.
    note = next(t for t in ax.texts if t.get_text() == "peak")
    assert not isinstance(note, Annotation)
    plt.close(fig)


def test_apply_annotations_tagged_text_uses_flexitext_with_matching_box(tmp_path):
    """A flexitext-tagged string renders via flexitext plus a matching bbox patch."""
    import matplotlib.colors as mcolors
    from matplotlib.offsetbox import AnnotationBbox
    from matplotlib.patches import FancyBboxPatch

    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 2])

    view._apply_annotations(
        fig,
        {
            "annotations": [
                {
                    "x": 1.0,
                    "y": 1.0,
                    "text": "<weight:semibold>$43B</> peak",
                    "text_x": 1.5,
                    "text_y": 1.8,
                    "color": "Rocket Flame",
                }
            ]
        },
        view.DESKTOP,
    )

    # flexitext places an AnnotationBbox; the raw tag is never a literal Text.
    assert any(isinstance(a, AnnotationBbox) for a in ax.get_children())
    assert not any("<weight" in t.get_text() for t in ax.texts)
    # A separate rounded box behind the flexitext, coloured by the override.
    boxes = [p for p in ax.get_children() if isinstance(p, FancyBboxPatch)]
    assert len(boxes) == 1
    assert mcolors.to_hex(boxes[0].get_edgecolor()) == "#ff5d47"  # Rocket Flame
    plt.close(fig)


def test_apply_annotations_separates_overlapping_labelless(tmp_path):
    """Two label-less callouts at near-identical coords are nudged apart (adjustText)."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [0, 1, 2, 3])
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)

    view._apply_annotations(
        fig,
        {
            "annotations": [
                {"x": 1.5, "y": 1.5, "text": "alpha"},
                {"x": 1.52, "y": 1.52, "text": "beta"},
            ]
        },
        view.DESKTOP,
    )

    renderer = fig.canvas.get_renderer()
    by_text = {t.get_text(): t for t in ax.texts}
    a_box = by_text["alpha"].get_window_extent(renderer)
    b_box = by_text["beta"].get_window_extent(renderer)
    assert not a_box.overlaps(b_box)
    # The view is left untouched by the adjustment.
    assert ax.get_xlim() == (0.0, 3.0)
    plt.close(fig)


def test_apply_annotations_color_field_overrides_box_and_arrow(tmp_path):
    """The per-annotation color drives both the box border and the arrow colour."""
    import matplotlib.colors as mcolors
    from matplotlib.patches import FancyArrowPatch

    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 2])

    view._apply_annotations(
        fig,
        {
            "annotations": [
                {
                    "x": 1.0,
                    "y": 1.0,
                    "text": "peak",
                    "text_x": 1.5,
                    "text_y": 1.8,
                    "arrow": True,
                    "color": "Neptune Blue",
                }
            ]
        },
        view.DESKTOP,
    )

    note = next(t for t in ax.texts if t.get_text() == "peak")
    assert mcolors.to_hex(note.get_bbox_patch().get_edgecolor()) == "#037cc2"
    arrow = next(p for p in ax.patches if isinstance(p, FancyArrowPatch))
    assert mcolors.to_hex(arrow.get_edgecolor()) == "#037cc2"
    plt.close(fig)


def test_apply_annotations_noop_when_unset(tmp_path):
    """No annotations metadata → the axes gain no text artists."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 2])

    view._apply_annotations(fig, {"title": "T"}, view.DESKTOP)

    assert list(ax.texts) == []
    plt.close(fig)


def test_coerce_annotation_x_parses_date_strings_else_passes_through(tmp_path):
    """String x on a date axis becomes a Timestamp; numbers/plain strings pass through."""
    import pandas as pd

    view = ChartView(outdir=tmp_path, style_file=None)
    assert isinstance(view._coerce_annotation_x("2020-01-01"), pd.Timestamp)
    assert view._coerce_annotation_x(5.0) == 5.0
    assert view._coerce_annotation_x("not a date") == "not a date"
