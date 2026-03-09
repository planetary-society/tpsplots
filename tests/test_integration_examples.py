"""Integration tests that generate charts from all example YAML files.

Run with: pytest -m integration
Excluded from default test runs (requires network access for data sources).
"""

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "yaml" / "examples"
YAML_FILES = sorted(EXAMPLES_DIR.glob("*.yaml"))


@pytest.mark.integration
@pytest.mark.parametrize(
    "yaml_file",
    YAML_FILES,
    ids=[f.stem for f in YAML_FILES],
)
def test_example_chart_generates(yaml_file, tmp_path):
    """Each example YAML should produce desktop, mobile, and social output files."""
    from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

    processor = YAMLChartProcessor(yaml_file, outdir=tmp_path)
    result = processor.generate_chart()

    # Verify all three device variants were created
    assert "desktop" in result, f"Missing desktop figure for {yaml_file.name}"
    assert "mobile" in result, f"Missing mobile figure for {yaml_file.name}"
    assert "social" in result, f"Missing social figure for {yaml_file.name}"

    # Verify output files were actually written to disk
    output_files = list(tmp_path.iterdir())
    assert len(output_files) >= 3, (
        f"Expected at least 3 output files, got {len(output_files)}: "
        f"{[f.name for f in output_files]}"
    )

    # Verify expected file types exist
    png_files = list(tmp_path.glob("*.png"))
    assert len(png_files) >= 3, f"Expected at least 3 PNG files, got {len(png_files)}"
