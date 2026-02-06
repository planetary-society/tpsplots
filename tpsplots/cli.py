"""Command-line interface for tpsplots using Typer."""

import logging
import sys
import traceback
from pathlib import Path
from typing import Annotated

import typer

from tpsplots import __version__
from tpsplots.commands.s3_sync import s3_sync
from tpsplots.commands.textedit import textedit
from tpsplots.exceptions import ConfigurationError, DataSourceError, RenderingError
from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor
from tpsplots.schema import get_chart_types
from tpsplots.templates import get_available_templates, get_template

app = typer.Typer(
    name="tpsplots",
    help="Generate Planetary Society-branded charts from YAML configurations.",
    add_completion=False,
    no_args_is_help=True,
)


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


def validate_yaml(yaml_path: Path) -> bool:
    """Validate a YAML configuration without generating charts."""
    try:
        YAMLChartProcessor(yaml_path)
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


def collect_yaml_files(inputs: list[Path]) -> tuple[list[Path], list[str]]:
    """Collect all YAML files from the given inputs (files and directories)."""
    yaml_files = []
    errors: list[str] = []
    logger = logging.getLogger(__name__)

    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() in [".yaml", ".yml"]:
                yaml_files.append(input_path)
            else:
                errors.append(f"Not a YAML file: {input_path}")
        elif input_path.is_dir():
            # Non-recursive - only direct children
            dir_yamls = list(input_path.glob("*.yaml")) + list(input_path.glob("*.yml"))
            if dir_yamls:
                yaml_files.extend(sorted(dir_yamls))
                logger.info(f"Found {len(dir_yamls)} YAML files in {input_path}")
            else:
                errors.append(f"No YAML files found in directory: {input_path}")
        else:
            errors.append(f"Path not found: {input_path}")

    return yaml_files, errors


def version_callback(value: bool) -> None:
    """Display version and exit."""
    if value:
        print(f"tpsplots {__version__}")
        raise typer.Exit()


def schema_callback(value: bool) -> None:
    """Print JSON Schema and exit."""
    if value:
        print(export_schema())
        raise typer.Exit()


def list_types_callback(value: bool) -> None:
    """List chart types and exit."""
    if value:
        list_chart_types()
        raise typer.Exit()


def new_callback(chart_type: str | None) -> None:
    """Generate template and exit."""
    if chart_type:
        try:
            template = get_template(chart_type)
            print(template)
            raise typer.Exit()
        except ValueError as e:
            print(str(e), file=sys.stderr)
            print(f"Available templates: {', '.join(get_available_templates())}", file=sys.stderr)
            raise typer.Exit(code=2) from None


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
    schema: Annotated[
        bool,
        typer.Option(
            "--schema",
            callback=schema_callback,
            is_eager=True,
            help="Print JSON Schema for YAML configuration and exit",
        ),
    ] = False,
    list_types: Annotated[
        bool,
        typer.Option(
            "--list-types",
            callback=list_types_callback,
            is_eager=True,
            help="List available chart types and exit",
        ),
    ] = False,
    new: Annotated[
        str | None,
        typer.Option(
            "--new",
            callback=new_callback,
            is_eager=True,
            metavar="TYPE",
            help="Generate a YAML template for the specified chart type",
        ),
    ] = None,
) -> None:
    """Generate Planetary Society-branded charts from YAML configurations."""
    pass


@app.command("generate")
def generate(
    inputs: Annotated[
        list[Path],
        typer.Argument(help="YAML configuration file(s) or directory(ies) to process"),
    ],
    outdir: Annotated[
        Path,
        typer.Option("--outdir", "-o", help="Output directory for generated charts"),
    ] = Path("charts"),
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output (errors still shown)"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose/debug logging"),
    ] = False,
) -> None:
    """Generate charts from YAML configuration files.

    Examples:

        tpsplots generate chart.yaml                    Generate a single chart

        tpsplots generate chart1.yaml chart2.yaml       Process multiple charts

        tpsplots generate yaml/                         Process all YAML files in directory

        tpsplots generate --outdir output/ yaml/        Specify output directory
    """
    # Setup logging
    setup_logging(verbose=verbose, quiet=quiet)
    logger = logging.getLogger(__name__)

    # Collect all YAML files from inputs
    yaml_files, input_errors = collect_yaml_files(inputs)

    if input_errors:
        for error in input_errors:
            logger.error(error)
        raise typer.Exit(code=2)

    if not yaml_files:
        logger.error("No YAML files found to process")
        raise typer.Exit(code=2)

    if not quiet:
        logger.info(f"Processing {len(yaml_files)} YAML file(s)...")

    # Generate charts
    success_count = 0
    failure_count = 0
    config_error_count = 0

    # Create output directory if it doesn't exist
    outdir.mkdir(parents=True, exist_ok=True)

    for yaml_file in yaml_files:
        try:
            processor = YAMLChartProcessor(yaml_file, outdir=outdir)
            result = processor.generate_chart()

            if result:
                if not quiet:
                    logger.info(f"Generated chart from {yaml_file.name}")
                success_count += 1
            else:
                if not quiet:
                    logger.warning(f"No output from {yaml_file.name}")
                failure_count += 1

        except ConfigurationError as e:
            logger.error(f"Config error: {yaml_file.name} - {e}")
            config_error_count += 1
            if verbose:
                traceback.print_exc()
        except (DataSourceError, RenderingError) as e:
            logger.error(f"Failed: {yaml_file.name} - {e}")
            failure_count += 1
            if verbose:
                traceback.print_exc()
        except Exception as e:
            logger.error(f"Unexpected error: {yaml_file.name} - {e}")
            failure_count += 1
            if verbose:
                traceback.print_exc()

    if not quiet:
        logger.info(f"Complete: {success_count} succeeded, {failure_count} failed")

    if config_error_count > 0:
        raise typer.Exit(code=2)
    if failure_count > 0:
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    inputs: Annotated[
        list[Path],
        typer.Argument(help="YAML configuration file(s) or directory(ies) to validate"),
    ],
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output (errors still shown)"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose/debug logging"),
    ] = False,
) -> None:
    """Validate YAML configuration files without generating charts.

    Examples:

        tpsplots validate chart.yaml                    Validate a single chart

        tpsplots validate chart1.yaml chart2.yaml       Validate multiple charts

        tpsplots validate yaml/                         Validate all YAML files in directory
    """
    # Setup logging
    setup_logging(verbose=verbose, quiet=quiet)
    logger = logging.getLogger(__name__)

    # Collect all YAML files from inputs
    yaml_files, input_errors = collect_yaml_files(inputs)

    if input_errors:
        for error in input_errors:
            logger.error(error)
        raise typer.Exit(code=2)

    if not yaml_files:
        logger.error("No YAML files found to process")
        raise typer.Exit(code=2)

    valid_count = 0
    invalid_count = 0

    for yaml_file in yaml_files:
        if validate_yaml(yaml_file):
            valid_count += 1
        else:
            invalid_count += 1

    if not quiet:
        logger.info(f"Validation complete: {valid_count} valid, {invalid_count} invalid")

    raise typer.Exit(code=0 if invalid_count == 0 else 2)


# Register s3-sync subcommand
app.command("s3-sync")(s3_sync)
app.command("textedit")(textedit)


def cli_main() -> None:
    """Entry point for pyproject.toml."""
    app()


if __name__ == "__main__":
    cli_main()
