"""Tests for the CLI module."""

import json
import logging
from pathlib import Path

from typer.testing import CliRunner

from tpsplots.cli import app
from tpsplots.exceptions import DataSourceError

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
        assert "textedit" in result.stdout

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
        assert "scatter" in result.stdout

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
        result = runner.invoke(
            app,
            ["s3-sync", "-d", "nonexistent_dir", "-b", "test-bucket", "-p", "test/", "--dry-run"],
        )
        assert result.exit_code == 1
        assert "does not exist" in result.stdout

    def test_s3_sync_requires_args(self):
        """Test that s3-sync requires bucket and prefix arguments."""
        result = runner.invoke(app, ["s3-sync", "--dry-run"])
        assert result.exit_code == 2  # Missing required options

    def test_generate_standard_output_is_concise(self, tmp_path, monkeypatch):
        """Default generate output should be easy to scan and summary-first."""
        yaml_1 = tmp_path / "one.yaml"
        yaml_2 = tmp_path / "two.yaml"
        yaml_1.write_text("chart: {}\n", encoding="utf-8")
        yaml_2.write_text("chart: {}\n", encoding="utf-8")

        class DummyProcessor:
            def __init__(self, *_args, **_kwargs):
                pass

            def generate_chart(self):
                return {"files": []}

        monkeypatch.setattr("tpsplots.cli.YAMLChartProcessor", DummyProcessor)

        result = runner.invoke(app, ["generate", str(yaml_1), str(yaml_2)])

        assert result.exit_code == 0
        assert "Processing 2 YAML file(s)" in result.output
        assert "[1/2]" in result.output
        assert "[2/2]" in result.output
        assert "Summary: 2 succeeded, 0 failed" in result.output
        assert "Loaded YAML config" not in result.output
        assert "Successfully generated chart" not in result.output

    def test_generate_verbose_shows_detailed_logs(self, tmp_path, monkeypatch):
        """Verbose mode should preserve detailed processor logs."""
        yaml_1 = tmp_path / "verbose.yaml"
        yaml_1.write_text("chart: {}\n", encoding="utf-8")

        class VerboseProcessor:
            def __init__(self, *_args, **_kwargs):
                pass

            def generate_chart(self):
                logging.getLogger("tpsplots.tests.verbose").info("verbose marker from processor")
                return {"files": []}

        monkeypatch.setattr("tpsplots.cli.YAMLChartProcessor", VerboseProcessor)

        result = runner.invoke(app, ["generate", "--verbose", str(yaml_1)])

        assert result.exit_code == 0
        assert "verbose marker from processor" in result.output

    def test_generate_failure_summary_is_high_signal(self, tmp_path, monkeypatch):
        """Failures should be clearly visible in default mode."""
        good_yaml = tmp_path / "good.yaml"
        bad_yaml = tmp_path / "bad.yaml"
        good_yaml.write_text("chart: {}\n", encoding="utf-8")
        bad_yaml.write_text("chart: {}\n", encoding="utf-8")

        class MixedProcessor:
            def __init__(self, yaml_path, *_args, **_kwargs):
                self.yaml_path = Path(yaml_path)

            def generate_chart(self):
                if self.yaml_path.name == "bad.yaml":
                    raise DataSourceError("network failure")
                return {"files": []}

        monkeypatch.setattr("tpsplots.cli.YAMLChartProcessor", MixedProcessor)

        result = runner.invoke(app, ["generate", str(good_yaml), str(bad_yaml)])

        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "bad.yaml" in result.output
        assert "network failure" in result.output
        assert "Summary: 1 succeeded, 1 failed" in result.output
