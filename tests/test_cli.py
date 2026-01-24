"""Tests for the CLI module."""

import json

from typer.testing import CliRunner

from tpsplots.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for tpsplots CLI."""

    def test_cli_import(self):
        """Test that CLI module can be imported."""
        from tpsplots.cli import cli_main

        assert callable(cli_main)

    def test_cli_help(self):
        """Test that --help works."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "tpsplots" in result.stdout
        # Check subcommands are listed
        assert "generate" in result.stdout
        assert "validate" in result.stdout
        assert "s3-sync" in result.stdout

    def test_cli_version(self):
        """Test that --version works."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "tpsplots" in result.stdout

    def test_cli_list_types(self):
        """Test that --list-types works (v2.0 type names)."""
        result = runner.invoke(app, ["--list-types"])
        assert result.exit_code == 0
        # v2.0 uses simplified type names
        assert "line" in result.stdout
        assert "bar" in result.stdout

    def test_cli_schema(self):
        """Test that --schema outputs valid JSON."""
        result = runner.invoke(app, ["--schema"])
        assert result.exit_code == 0
        schema = json.loads(result.stdout)
        assert "properties" in schema or "$defs" in schema

    def test_cli_no_args(self):
        """Test that CLI with no args shows help and subcommands."""
        result = runner.invoke(app, [])
        # Typer's no_args_is_help shows help - exit code may be 0 or 2
        assert "generate" in result.stdout
        assert "validate" in result.stdout

    def test_generate_help(self):
        """Test that generate --help works."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.stdout.lower()
        assert "INPUTS" in result.stdout

    def test_generate_missing_file(self):
        """Test that generate handles missing file with proper exit code."""
        result = runner.invoke(app, ["generate", "nonexistent.yaml"])
        assert result.exit_code == 2

    def test_validate_help(self):
        """Test that validate --help works."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()

    def test_validate_missing_file(self):
        """Test that validate handles missing file."""
        result = runner.invoke(app, ["validate", "nonexistent.yaml"])
        assert result.exit_code == 2

    def test_s3_sync_help(self):
        """Test that s3-sync subcommand help works."""
        result = runner.invoke(app, ["s3-sync", "--help"])
        assert result.exit_code == 0
        assert "s3-sync" in result.stdout or "Upload" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--bucket" in result.stdout

    def test_s3_sync_dry_run_missing_dir(self):
        """Test that s3-sync fails gracefully with missing directory."""
        result = runner.invoke(app, ["s3-sync", "--local-dir", "nonexistent_dir", "--dry-run"])
        assert result.exit_code == 1
        assert "does not exist" in result.stdout


class TestLegacyMainFunction:
    """Tests for backwards-compatible main() function."""

    def test_main_returns_int(self):
        """Test that legacy main() returns an integer exit code."""
        from tpsplots.cli import main

        exit_code = main(["--list-types"])
        assert isinstance(exit_code, int)
        assert exit_code == 0

    def test_main_help_exits_zero(self):
        """Test that --help returns 0."""
        from tpsplots.cli import main

        exit_code = main(["--help"])
        assert exit_code == 0

    def test_main_version_exits_zero(self):
        """Test that --version returns 0."""
        from tpsplots.cli import main

        exit_code = main(["--version"])
        assert exit_code == 0

    def test_main_generate_missing_file_exits_nonzero(self):
        """Test that generate with missing file returns non-zero."""
        from tpsplots.cli import main

        exit_code = main(["generate", "nonexistent.yaml"])
        assert exit_code == 2
