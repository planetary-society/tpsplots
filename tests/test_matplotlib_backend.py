"""Tests for Matplotlib backend initialization."""

import sys
from unittest.mock import Mock

import matplotlib

import tpsplots


def test_configure_matplotlib_forces_agg_even_when_display_is_available(monkeypatch):
    """Rendering should always use the non-interactive Agg backend."""
    use_mock = Mock()

    monkeypatch.setenv("TPSPLOTS_HEADLESS", "0")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(sys, "platform", "darwin", raising=False)
    monkeypatch.setattr(matplotlib, "use", use_mock)

    tpsplots._configure_matplotlib()

    use_mock.assert_called_once_with("Agg")
