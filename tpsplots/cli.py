"""Command-line interface for tpsplots."""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from tpsplots import __version__
from tpsplots.exceptions import ConfigurationError, DataSourceError, RenderingError
from tpsplots.processors import YAMLChartProcessor
from tpsplots.schema import get_chart_types


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging for the application."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    format_str = "%(asctime)s - %(levelname)s - %(message)s" if verbose else "%(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")

    # Suppress repetitive matplotlib categorical units INFO messages
    logging.getLogger("matplotlib.category").setLevel(logging.WARNING)


def validate_yaml(yaml_path: Path, strict: bool = False) -> bool:
    """Validate a YAML configuration without generating charts."""
    try:
        processor = YAMLChartProcessor(yaml_path)
        print(f"Valid: {yaml_path.name}")
        return True
    except (ConfigurationError, DataSourceError) as e:
        print(f"Invalid: {yaml_path.name} - {e}")
        return False
    except Exception as e:
        print(f"Error: {yaml_path.name} - {e}")
        return False


def list_chart_types() -> None:
    """Display available chart types."""
    print("Available chart types:")
    for chart_type in get_chart_types():
        print(f"  - {chart_type}")


def export_schema() -> str:
    """Generate JSON Schema from Pydantic models."""
    try:
        from tpsplots.schema import get_json_schema_string

        return get_json_schema_string()
    except Exception as e:
        return f'{{"error": "Failed to generate schema: {e}"}}'


def collect_yaml_files(inputs: list[Path]) -> list[Path]:
    """Collect all YAML files from the given inputs (files and directories)."""
    yaml_files = []
    logger = logging.getLogger(__name__)

    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() in [".yaml", ".yml"]:
                yaml_files.append(input_path)
            else:
                logger.warning(f"Skipping non-YAML file: {input_path}")
        elif input_path.is_dir():
            # Non-recursive - only direct children
            dir_yamls = list(input_path.glob("*.yaml")) + list(input_path.glob("*.yml"))
            if dir_yamls:
                yaml_files.extend(sorted(dir_yamls))
                logger.info(f"Found {len(dir_yamls)} YAML files in {input_path}")
            else:
                logger.warning(f"No YAML files found in directory: {input_path}")
        else:
            logger.error(f"Path not found: {input_path}")

    return yaml_files


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="tpsplots",
        description="Generate Planetary Society-branded charts from YAML configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s chart.yaml                       Generate a single chart
  %(prog)s chart1.yaml chart2.yaml          Process multiple charts
  %(prog)s yaml/                            Process all YAML files in directory
  %(prog)s --validate chart.yaml            Validate without generating
  %(prog)s --outdir output/ yaml/           Specify output directory
  %(prog)s --schema > schema.json           Export JSON Schema
  %(prog)s --list-types                     List available chart types
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

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Error on unresolved data references (default: pass through as-is)",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output (errors still shown)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print JSON Schema for YAML configuration and exit",
    )

    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available chart types and exit",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the tpsplots CLI.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Setup logging
    setup_logging(verbose=parsed_args.verbose, quiet=parsed_args.quiet)
    logger = logging.getLogger(__name__)

    # Handle --schema
    if parsed_args.schema:
        print(export_schema())
        return 0

    # Handle --list-types
    if parsed_args.list_types:
        list_chart_types()
        return 0

    # Require inputs for operations that need them
    if not parsed_args.inputs:
        parser.print_help()
        return 1

    # Collect all YAML files from inputs
    yaml_files = collect_yaml_files(parsed_args.inputs)

    if not yaml_files:
        logger.error("No YAML files found to process")
        return 1

    if not parsed_args.quiet:
        logger.info(f"Processing {len(yaml_files)} YAML file(s)...")

    # Handle validation mode
    if parsed_args.validate:
        valid_count = 0
        invalid_count = 0

        for yaml_file in yaml_files:
            if validate_yaml(yaml_file, strict=parsed_args.strict):
                valid_count += 1
            else:
                invalid_count += 1

        if not parsed_args.quiet:
            logger.info(f"Validation complete: {valid_count} valid, {invalid_count} invalid")
        return 0 if invalid_count == 0 else 1

    # Generate charts
    success_count = 0
    failure_count = 0

    # Create output directory if it doesn't exist
    parsed_args.outdir.mkdir(parents=True, exist_ok=True)

    for yaml_file in yaml_files:
        try:
            processor = YAMLChartProcessor(yaml_file, outdir=parsed_args.outdir)
            result = processor.generate_chart()

            if result:
                if not parsed_args.quiet:
                    logger.info(f"Generated chart from {yaml_file.name}")
                success_count += 1
            else:
                if not parsed_args.quiet:
                    logger.warning(f"No output from {yaml_file.name}")
                failure_count += 1

        except (ConfigurationError, DataSourceError, RenderingError) as e:
            logger.error(f"Failed: {yaml_file.name} - {e}")
            failure_count += 1
            if parsed_args.verbose:
                traceback.print_exc()
        except Exception as e:
            logger.error(f"Unexpected error: {yaml_file.name} - {e}")
            failure_count += 1
            if parsed_args.verbose:
                traceback.print_exc()

    if not parsed_args.quiet:
        logger.info(f"Complete: {success_count} succeeded, {failure_count} failed")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
