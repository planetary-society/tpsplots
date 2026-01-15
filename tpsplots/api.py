"""Public API for tpsplots package."""

import logging
from pathlib import Path
from typing import Any

from tpsplots.exceptions import ConfigurationError, DataSourceError, RenderingError
from tpsplots.processors import YAMLChartProcessor

logger = logging.getLogger(__name__)


def generate(
    *sources: str | Path,
    outdir: str | Path | None = None,
    strict: bool = False,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Generate charts from YAML configuration file(s).

    This is the main entry point for the tpsplots package. It processes one or
    more YAML configuration files and generates charts based on their specifications.

    Args:
        sources: One or more YAML files or directories containing YAML files.
                 When a directory is provided, all .yaml and .yml files in
                 that directory (non-recursive) will be processed.
        outdir: Output directory for generated charts. Defaults to 'charts/'
                relative to the current working directory.
        strict: If True, raise an error on any unresolved data references.
                If False (default), unresolved references are passed through as-is.
        quiet: If True, suppress progress logging. Errors are still logged.

    Returns:
        dict: Summary of generation results:
            - 'succeeded': Number of charts successfully generated
            - 'failed': Number of charts that failed
            - 'files': List of generated file paths (on success)
            - 'errors': List of error messages (on failure)

    Raises:
        ConfigurationError: If YAML configuration is invalid.
        DataSourceError: If data cannot be loaded from specified source.
        RenderingError: If chart rendering fails.

    Examples:
        >>> import tpsplots
        >>> # Generate a single chart
        >>> result = tpsplots.generate("charts/line_chart.yaml")
        >>> print(f"Generated {result['succeeded']} charts")

        >>> # Process all YAML files in a directory
        >>> result = tpsplots.generate("yaml/", outdir="output/")

        >>> # Strict mode - fail on unresolved references
        >>> result = tpsplots.generate("config.yaml", strict=True)
    """
    if not quiet:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    else:
        logging.basicConfig(level=logging.ERROR, format="%(message)s")

    if len(sources) == 1 and isinstance(sources[0], (list, tuple, set)):
        sources = tuple(sources[0])

    if not sources:
        raise ConfigurationError("At least one YAML file or directory must be provided.")

    output_path = Path(outdir) if outdir else Path("charts")

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    result = {
        "succeeded": 0,
        "failed": 0,
        "files": [],
        "errors": [],
    }

    # Collect YAML files to process
    yaml_files: list[Path] = []
    missing_paths: list[Path] = []

    for source in sources:
        source_path = Path(source)
        if source_path.is_file():
            if source_path.suffix.lower() in [".yaml", ".yml"]:
                yaml_files.append(source_path)
            else:
                raise ConfigurationError(f"Source file is not YAML: {source_path}")
        elif source_path.is_dir():
            # Non-recursive - only direct children
            dir_yamls = list(source_path.glob("*.yaml")) + list(source_path.glob("*.yml"))
            if dir_yamls:
                yaml_files.extend(sorted(dir_yamls))
            else:
                raise ConfigurationError(f"No YAML files found in {source_path}")
        else:
            missing_paths.append(source_path)

    if missing_paths:
        missing_display = ", ".join(str(path) for path in missing_paths)
        raise ConfigurationError(f"Source path does not exist: {missing_display}")

    # Process each YAML file
    for yaml_file in yaml_files:
        try:
            if not quiet:
                logger.info(f"Processing {yaml_file.name}...")

            processor = YAMLChartProcessor(yaml_file, outdir=output_path, strict=strict)
            chart_result = processor.generate_chart()

            result["succeeded"] += 1
            if chart_result and isinstance(chart_result, dict) and "files" in chart_result:
                result["files"].extend(chart_result["files"])

        except (ConfigurationError, DataSourceError, RenderingError) as e:
            result["failed"] += 1
            error_msg = f"{yaml_file.name}: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            result["failed"] += 1
            error_msg = f"{yaml_file.name}: Unexpected error - {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

    if not quiet:
        logger.info(f"Complete: {result['succeeded']} succeeded, {result['failed']} failed")

    return result
