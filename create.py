#!/usr/bin/env python
"""
Simple command-line tool for generating charts from YAML configurations.

Usage:
    python create.py yaml/chart.yaml                    # Single file
    python create.py yaml/chart1.yaml yaml/chart2.yaml  # Multiple files (auto-batch)
    python create.py yaml/                              # Directory (all .yaml files)
    python create.py --validate yaml/chart.yaml         # Validate only
    python create.py --outdir output/ yaml/             # Custom output directory
"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from tpsplots.processors import YAMLChartProcessor


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(levelname)s - %(message)s" if verbose else "%(message)s"

    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")


def validate_yaml(yaml_path: Path) -> bool:
    """Validate a YAML configuration without generating charts."""
    try:
        YAMLChartProcessor(yaml_path)  # Create processor to validate
        print(f"✅ {yaml_path.name} - Valid configuration")
        return True
    except Exception as e:
        print(f"❌ {yaml_path.name} - Invalid: {e}")
        return False


def generate_single_chart(yaml_path: Path, outdir: Path) -> bool:
    """Generate a single chart from a YAML configuration."""
    try:
        processor = YAMLChartProcessor(yaml_path, outdir=outdir)
        result = processor.generate_chart()

        if result:
            print(f"✅ Generated chart from {yaml_path.name}")
            return True
        else:
            print(f"⚠️ No output from {yaml_path.name}")
            return False

    except Exception as e:
        print(f"❌ Failed to generate chart from {yaml_path.name}")
        print(f"   Error: {e}")
        if logging.getLogger().level == logging.DEBUG:
            traceback.print_exc()
        return False


def collect_yaml_files(inputs: list[Path]) -> list[Path]:
    """Collect all YAML files from the given inputs (files and directories)."""
    yaml_files = []

    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() in [".yaml", ".yml"]:
                yaml_files.append(input_path)
            else:
                print(f"⚠️ Skipping non-YAML file: {input_path}")
        elif input_path.is_dir():
            # Find all YAML files in directory
            dir_yamls = list(input_path.glob("*.yaml")) + list(input_path.glob("*.yml"))
            if dir_yamls:
                yaml_files.extend(sorted(dir_yamls))
                print(f"📁 Found {len(dir_yamls)} YAML files in {input_path}")
            else:
                print(f"⚠️ No YAML files found in directory: {input_path}")
        else:
            print(f"❌ Path not found: {input_path}")

    return yaml_files


def main():
    """Main entry point for the create.py CLI tool."""
    parser = argparse.ArgumentParser(
        description="Generate charts from YAML configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s yaml/chart.yaml                    Generate a single chart
  %(prog)s yaml/chart1.yaml yaml/chart2.yaml  Process multiple charts
  %(prog)s yaml/                              Process all YAML files in directory
  %(prog)s --validate yaml/chart.yaml         Validate without generating
  %(prog)s --outdir output/ yaml/             Specify output directory
        """,
    )

    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="YAML configuration file(s) or directory(ies) to process",
    )

    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="Validate YAML configuration without generating charts",
    )

    parser.add_argument(
        "--outdir",
        "-o",
        type=Path,
        default=Path("charts"),
        help="Output directory for generated charts (default: charts/)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument("--list-types", action="store_true", help="List available chart types")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Suppress repetitive matplotlib categorical units INFO messages
    logging.getLogger("matplotlib.category").setLevel(logging.WARNING)

    # Handle list-types
    if args.list_types:
        print("Available chart types:")
        for chart_type in YAMLChartProcessor.VIEW_REGISTRY:
            print(f"  • {chart_type}")
        return 0

    # Require inputs for operations that need them
    if not args.inputs and not args.list_types:
        parser.print_help()
        return 1

    # Collect all YAML files from inputs (if provided)
    yaml_files = []
    if args.inputs:
        yaml_files = collect_yaml_files(args.inputs)

        if not yaml_files:
            print("❌ No YAML files found to process")
            return 1

    if yaml_files:
        print(f"📊 Processing {len(yaml_files)} YAML file(s)...")

    # Handle validation mode
    if args.validate and yaml_files:
        valid_count = 0
        invalid_count = 0

        for yaml_file in yaml_files:
            if validate_yaml(yaml_file):
                valid_count += 1
            else:
                invalid_count += 1

        print(f"\n📊 Validation complete: {valid_count} valid, {invalid_count} invalid")
        return 0 if invalid_count == 0 else 1

    # Generate charts
    if not yaml_files:
        return 0

    success_count = 0
    failure_count = 0

    # Create output directory if it doesn't exist
    args.outdir.mkdir(parents=True, exist_ok=True)

    for yaml_file in yaml_files:
        if generate_single_chart(yaml_file, args.outdir):
            success_count += 1
        else:
            failure_count += 1

    print(f"\n📊 Generation complete: {success_count} succeeded, {failure_count} failed")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
