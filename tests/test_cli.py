"""Tests for the CLI module."""

import pytest


class TestCLI:
    """Tests for tpsplots CLI."""

    def test_cli_import(self):
        """Test that CLI module can be imported."""
        from tpsplots.cli import main

        assert callable(main)

    def test_cli_help(self, capsys):
        """Test that --help works."""
        from tpsplots.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "tpsplots" in captured.out

    def test_cli_version(self, capsys):
        """Test that --version works."""
        from tpsplots.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "tpsplots" in captured.out

    def test_cli_list_types(self, capsys):
        """Test that --list-types works (v2.0 type names)."""
        from tpsplots.cli import main

        exit_code = main(["--list-types"])
        assert exit_code == 0

        captured = capsys.readouterr()
        # v2.0 uses simplified type names
        assert "line" in captured.out
        assert "bar" in captured.out

    def test_cli_schema(self, capsys):
        """Test that --schema outputs valid JSON."""
        import json

        from tpsplots.cli import main

        exit_code = main(["--schema"])
        assert exit_code == 0

        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "properties" in schema or "$defs" in schema

    def test_cli_no_args(self):
        """Test that CLI with no args returns error code."""
        from tpsplots.cli import main

        exit_code = main([])
        assert exit_code == 2

    def test_cli_missing_file(self):
        """Test that CLI handles missing file."""
        from tpsplots.cli import main

        exit_code = main(["nonexistent.yaml"])
        assert exit_code == 2
