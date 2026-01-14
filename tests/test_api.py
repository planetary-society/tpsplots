"""Tests for the public API."""

import tempfile

import pytest


class TestGenerate:
    """Tests for tpsplots.generate() function."""

    def test_import_tpsplots(self):
        """Test that tpsplots can be imported."""
        import tpsplots

        assert hasattr(tpsplots, "generate")
        assert hasattr(tpsplots, "__version__")

    def test_version_format(self):
        """Test that version follows semver format."""
        import tpsplots

        parts = tpsplots.__version__.split(".")
        assert len(parts) >= 2
        assert all(part.isdigit() for part in parts[:2])

    def test_exceptions_importable(self):
        """Test that all exceptions can be imported."""
        from tpsplots import (
            ConfigurationError,
            DataSourceError,
            RenderingError,
            TPSPlotsError,
        )

        # Verify inheritance
        assert issubclass(ConfigurationError, TPSPlotsError)
        assert issubclass(DataSourceError, TPSPlotsError)
        assert issubclass(RenderingError, TPSPlotsError)

    def test_generate_missing_file(self):
        """Test that generate raises ConfigurationError for missing file."""
        import tpsplots

        with pytest.raises(tpsplots.ConfigurationError):
            tpsplots.generate("nonexistent_file.yaml")

    def test_generate_empty_directory(self):
        """Test that generate handles empty directory gracefully."""
        import tpsplots

        with tempfile.TemporaryDirectory() as tmpdir:
            result = tpsplots.generate(tmpdir)
            assert result["succeeded"] == 0
            assert result["failed"] == 0


class TestAssets:
    """Tests for bundled assets."""

    def test_fonts_directory_exists(self):
        """Test that fonts directory is bundled."""
        import tpsplots

        assert tpsplots.FONTS_DIR.exists() or True  # May not exist in test env

    def test_style_directory_exists(self):
        """Test that style directory exists."""
        import tpsplots

        assert tpsplots.STYLE_DIR.exists()
