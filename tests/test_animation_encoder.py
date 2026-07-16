"""Tests for the ffmpeg encoder (no real ffmpeg — everything monkeypatched).

The venv has neither system ffmpeg nor imageio-ffmpeg, so ``resolve_ffmpeg`` is
exercised with fake modules and a patched ``FFMpegWriter.isAvailable``, and
``write_mp4`` is exercised with a stub writer + a minimal fake animator.
"""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager

import matplotlib
import matplotlib.animation
import matplotlib.pyplot as plt
import pytest

from tpsplots.animation.encoder import (
    BT709_ARGS,
    QUALITY_ARGS,
    FFmpegUnavailableError,
    resolve_ffmpeg,
    write_mp4,
)


def _fake_imageio(monkeypatch, *, exe=None, error=None):
    """Inject a fake ``imageio_ffmpeg`` module into ``sys.modules``."""
    module = types.ModuleType("imageio_ffmpeg")

    def get_ffmpeg_exe():
        if error is not None:
            raise error
        return exe

    module.get_ffmpeg_exe = get_ffmpeg_exe
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", module)
    return module


class TestResolveFfmpeg:
    def test_uses_imageio_binary_and_sets_rcparams(self, monkeypatch):
        _fake_imageio(monkeypatch, exe="/fake/bin/ffmpeg")
        # Baseline so monkeypatch restores rcParams after the function mutates it.
        monkeypatch.setitem(matplotlib.rcParams, "animation.ffmpeg_path", "")

        path = resolve_ffmpeg()

        assert path == "/fake/bin/ffmpeg"
        assert matplotlib.rcParams["animation.ffmpeg_path"] == "/fake/bin/ffmpeg"

    def test_falls_back_to_system_ffmpeg(self, monkeypatch):
        # imageio installed but has no usable binary -> RuntimeError.
        _fake_imageio(monkeypatch, error=RuntimeError("no binary"))
        monkeypatch.setattr(matplotlib.animation.FFMpegWriter, "isAvailable", lambda: True)
        monkeypatch.setitem(matplotlib.rcParams, "animation.ffmpeg_path", "/usr/bin/ffmpeg")

        assert resolve_ffmpeg() == "/usr/bin/ffmpeg"

    def test_system_ffmpeg_default_name(self, monkeypatch):
        _fake_imageio(monkeypatch, error=RuntimeError("no binary"))
        monkeypatch.setattr(matplotlib.animation.FFMpegWriter, "isAvailable", lambda: True)
        monkeypatch.setitem(matplotlib.rcParams, "animation.ffmpeg_path", "")

        assert resolve_ffmpeg() == "ffmpeg"

    def test_missing_raises_with_both_install_hints(self, monkeypatch):
        # Environment-independent: imageio_ffmpeg may or may not be installed,
        # so fake one whose binary lookup fails, and force isAvailable False.
        _fake_imageio(monkeypatch, error=RuntimeError("no binary"))
        monkeypatch.setattr(matplotlib.animation.FFMpegWriter, "isAvailable", lambda: False)
        monkeypatch.setitem(matplotlib.rcParams, "animation.ffmpeg_path", "")

        with pytest.raises(FFmpegUnavailableError) as exc:
            resolve_ffmpeg()

        message = str(exc.value)
        assert "pip install 'tpsplots[animate]'" in message
        assert "brew install ffmpeg" in message


class _StubWriter:
    """Records init kwargs, provides a context-manager saving(), counts frames."""

    last: _StubWriter | None = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.grab_count = 0
        self.saving_args = None
        _StubWriter.last = self

    @contextmanager
    def saving(self, fig, path, dpi):
        self.saving_args = (fig, path, dpi)
        yield self

    def grab_frame(self, **kwargs):
        self.grab_count += 1


class _FakeAnimator:
    total_duration = 1.0

    def __init__(self):
        self.ts: list[float] = []

    def apply_global(self, t):
        self.ts.append(t)


class TestWriteMp4:
    def _run(self, tmp_path, monkeypatch, *, quality="high", on_frame=None):
        monkeypatch.setattr(matplotlib.animation, "FFMpegWriter", _StubWriter)
        _StubWriter.last = None
        fig = plt.figure()
        animator = _FakeAnimator()
        out_path = tmp_path / "sub" / "clip.mp4"
        try:
            result = write_mp4(fig, animator, out_path, fps=10, quality=quality, on_frame=on_frame)
        finally:
            plt.close(fig)
        return result, animator, _StubWriter.last, out_path

    def test_frame_count_matches_duration(self, tmp_path, monkeypatch):
        _result, animator, writer, _out = self._run(tmp_path, monkeypatch)
        # total = round(1.0 * 10) = 10 -> 11 frames (inclusive endpoint).
        assert writer.grab_count == 11
        assert len(animator.ts) == 11
        assert animator.ts[0] == pytest.approx(0.0)
        assert animator.ts[-1] == pytest.approx(1.0)

    def test_creates_output_directory(self, tmp_path, monkeypatch):
        result, _animator, _writer, out_path = self._run(tmp_path, monkeypatch)
        assert out_path.parent.is_dir()
        assert result == out_path

    def test_extra_args_carry_bt709_and_quality_no_codec(self, tmp_path, monkeypatch):
        _result, _animator, writer, _out = self._run(tmp_path, monkeypatch, quality="high")
        extra_args = writer.kwargs["extra_args"]

        assert "-crf" in extra_args
        assert "18" in extra_args  # high preset crf
        assert "yuv420p" in extra_args
        assert "+faststart" in extra_args
        assert any("bt709" in arg for arg in extra_args)
        # Default codec ("h264") must be used — never pass codec explicitly.
        assert "codec" not in writer.kwargs
        assert writer.kwargs["fps"] == 10
        # Ordering: BT.709 tagging first, then the quality preset.
        assert extra_args == [*BT709_ARGS, *QUALITY_ARGS["high"]]

    def test_draft_quality_args(self, tmp_path, monkeypatch):
        _result, _animator, writer, _out = self._run(tmp_path, monkeypatch, quality="draft")
        assert writer.kwargs["extra_args"] == [*BT709_ARGS, *QUALITY_ARGS["draft"]]

    def test_on_frame_progress_callback(self, tmp_path, monkeypatch):
        calls: list[tuple[int, int]] = []
        self._run(tmp_path, monkeypatch, on_frame=lambda cur, total: calls.append((cur, total)))
        assert len(calls) == 11
        assert calls[0] == (1, 11)
        assert calls[-1] == (11, 11)
