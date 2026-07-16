"""Tests for the chart-panel-only VIDEO device style dicts on ChartView.

The ``video_square`` / ``video_landscape`` / ``video_portrait`` devices render
the chart panel with no header/footer/logo (branding is composited later by
``tpsplots animate``) at exact, even pixel dimensions for MP4 encoding.
"""

import pytest

from tpsplots.views.chart_view import ChartView

VIDEO_DICTS = {
    "video_square": ChartView.VIDEO_SQUARE,
    "video_landscape": ChartView.VIDEO_LANDSCAPE,
    "video_portrait": ChartView.VIDEO_PORTRAIT,
}

EXPECTED_PX = {
    "video_square": (1080, 1080),
    "video_landscape": (1920, 1080),
    "video_portrait": (1080, 1920),
}


@pytest.mark.parametrize("device, expected_px", EXPECTED_PX.items())
def test_video_pixel_dimensions_exact_and_even(make_video_figure, device, expected_px):
    """Each video device must render at its exact pixel size, both dims even."""
    fig = make_video_figure(device)
    px = tuple(round(v) for v in fig.get_size_inches() * fig.dpi)
    assert px == expected_px
    assert px[0] % 2 == 0
    assert px[1] % 2 == 0


@pytest.mark.parametrize("device", VIDEO_DICTS)
def test_video_dict_key_parity_with_desktop(device):
    """Every key present in DESKTOP must be present in each video dict."""
    assert set(VIDEO_DICTS[device]) == set(ChartView.DESKTOP)


@pytest.mark.parametrize("device", VIDEO_DICTS)
def test_video_dict_chrome_flags_off(device):
    """Video panels draw no header, footer, or logo."""
    style = VIDEO_DICTS[device]
    assert style["header"] is False
    assert style["footer"] is False
    assert style["add_logo"] is False


def test_create_figure_unknown_device_falls_back_to_desktop(make_video_figure):
    """An unrecognized device string still resolves to the DESKTOP style."""
    fig = make_video_figure("nonexistent_device")
    # DESKTOP is 16x10 @ 300 dpi.
    assert fig.dpi == ChartView.DESKTOP["dpi"]
    assert tuple(fig.get_size_inches()) == ChartView.DESKTOP["figsize"]


def test_create_figure_video_square_uses_150_dpi(make_video_figure):
    """device='video_square' routes to VIDEO_SQUARE (dpi 150)."""
    fig = make_video_figure("video_square")
    assert fig.dpi == 150


def test_video_square_draws_no_title_text(make_video_figure):
    """With the header off, no figure-level text artist is drawn for the title."""
    fig = make_video_figure("video_square", title="Secret Title")
    assert not any("Secret Title" in text.get_text() for text in fig.texts)
