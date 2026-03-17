"""Generate Markdown reference documentation for chart types."""

from pathlib import Path
from typing import Annotated

import typer

from tpsplots.docs_generator import generate_all
from tpsplots.models.charts import CONFIG_REGISTRY


def docs(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Output directory for generated docs"),
    ] = Path("docs"),
    chart_type: Annotated[
        str | None,
        typer.Option("--chart-type", "-t", help="Generate docs for a single chart type"),
    ] = None,
) -> None:
    """Generate Markdown reference docs for chart configuration.

    Creates one file per chart type plus index and data config pages.

    Examples:

        tpsplots docs                              Generate all docs

        tpsplots docs --output-dir reference/      Custom output directory

        tpsplots docs --chart-type bar             Single chart type only
    """
    if chart_type and chart_type not in CONFIG_REGISTRY:
        available = ", ".join(sorted(CONFIG_REGISTRY.keys()))
        typer.secho(
            f"Unknown chart type: {chart_type}. Available: {available}", fg=typer.colors.RED
        )
        raise typer.Exit(code=2)

    types_to_generate = [chart_type] if chart_type else None
    written = generate_all(output_dir, chart_types=types_to_generate)

    typer.secho(f"Generated {len(written)} file(s) in {output_dir}/", fg=typer.colors.GREEN)
    for path in written:
        typer.echo(f"  {path.name}")
