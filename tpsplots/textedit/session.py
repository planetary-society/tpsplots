"""In-memory preview session for chart text editing."""

from __future__ import annotations

import io
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
except ImportError:
    YAML = None
    DoubleQuotedScalarString = None

from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.processors.resolvers import (
    ColorResolver,
    DataResolver,
    MetadataResolver,
    ParameterResolver,
)
from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

PreviewDevice = Literal["desktop", "mobile"]


class TextEditSession:
    """Prepare a chart once, then render fast text-only previews."""

    def __init__(self, yaml_path: Path, outdir: Path | None = None):
        self.yaml_path = Path(yaml_path)
        self.outdir = outdir or Path("charts")
        self.processor = YAMLChartProcessor(self.yaml_path, outdir=self.outdir)

        self.output_name: str = ""
        self.metadata: dict[str, Any] = {}
        self.parameters: dict[str, Any] = {}
        self._plot_method = None
        self._prepare_render_context()

    def _prepare_render_context(self) -> None:
        """Resolve data and chart params once for rapid preview rendering."""
        self.data = DataResolver.resolve(self.processor.config.data)

        chart = self.processor.config.chart
        chart_dict = chart.model_dump(exclude_none=True)

        metadata_fields = {"title", "subtitle", "source"}
        metadata = {k: chart_dict.pop(k) for k in metadata_fields if k in chart_dict}

        chart_type_v2 = chart_dict.pop("type")
        self.output_name = chart_dict.pop("output")
        chart_type_v1 = CHART_TYPES.get(chart_type_v2, f"{chart_type_v2}_plot")

        self.parameters = ParameterResolver.resolve(chart_dict, self.data)
        self.parameters = ColorResolver.resolve_deep(self.parameters)
        self.metadata = MetadataResolver.resolve(metadata, self.data)

        view = self.processor._get_view(chart_type_v1)
        self._plot_method = getattr(view, chart_type_v1)

    def get_initial_text(self) -> dict[str, str]:
        """Return current text fields for pre-populating the UI."""
        return {
            "title": str(self.metadata.get("title") or ""),
            "subtitle": str(self.metadata.get("subtitle") or ""),
            "source": str(self.metadata.get("source") or ""),
        }

    def render_svg(
        self,
        *,
        device: PreviewDevice,
        title: str | None = None,
        subtitle: str | None = None,
        source: str | None = None,
    ) -> str:
        """Render a desktop or mobile SVG preview in-memory."""
        if device not in {"desktop", "mobile"}:
            raise ValueError(f"Unsupported preview device: {device}")

        metadata = dict(self.metadata)
        if title is not None:
            metadata["title"] = title
        if subtitle is not None:
            metadata["subtitle"] = subtitle
        if source is not None:
            metadata["source"] = source

        result: dict[str, Any] | None = None
        try:
            result = self._plot_method(
                metadata=metadata,
                stem=f"{self.output_name}_textedit_preview",
                preview=True,
                **deepcopy(self.parameters),
            )

            fig = result[device]
            svg_buffer = io.StringIO()
            fig.savefig(svg_buffer, format="svg", dpi=150)
            return svg_buffer.getvalue()
        finally:
            if result is not None:
                for figure_key in ("desktop", "mobile"):
                    figure = result.get(figure_key)
                    if figure is not None:
                        plt.close(figure)

    def save_text(
        self, *, title: str, subtitle: str | None = None, source: str | None = None
    ) -> None:
        """Persist title/subtitle/source back to the source YAML file in place."""
        normalized_title = (title or "").strip()
        if not normalized_title:
            raise ValueError("chart.title is required and cannot be empty")

        normalized_subtitle = None if subtitle is None else subtitle.strip()
        normalized_source = None if source is None else source.strip()

        # Prefer in-place editing to preserve comments/order and avoid unrelated rewrites.
        # Fall back to ruamel round-trip only when in-place editing cannot proceed.
        try:
            self._save_text_in_place(
                title=normalized_title,
                subtitle=normalized_subtitle,
                source=normalized_source,
            )
        except Exception:
            if YAML is not None and DoubleQuotedScalarString is not None:
                self._save_text_with_ruamel(
                    title=normalized_title,
                    subtitle=normalized_subtitle,
                    source=normalized_source,
                )
            else:
                raise

        self.metadata["title"] = normalized_title
        self.metadata["subtitle"] = normalized_subtitle or ""
        self.metadata["source"] = normalized_source or ""

    def _save_text_with_ruamel(
        self, *, title: str, subtitle: str | None, source: str | None
    ) -> None:
        """Use ruamel round-trip editing when the dependency is available."""
        yaml_rt = YAML()
        yaml_rt.preserve_quotes = True

        with self.yaml_path.open(encoding="utf-8") as file:
            config = yaml_rt.load(file)

        if not isinstance(config, dict):
            raise ValueError("Invalid YAML structure: expected a top-level mapping")

        chart = config.get("chart")
        if not isinstance(chart, dict):
            raise ValueError("Invalid YAML structure: missing 'chart' mapping")

        chart["title"] = DoubleQuotedScalarString(title)
        if subtitle:
            chart["subtitle"] = DoubleQuotedScalarString(subtitle)
        else:
            chart.pop("subtitle", None)

        if source:
            chart["source"] = DoubleQuotedScalarString(source)
        else:
            chart.pop("source", None)

        with self.yaml_path.open("w", encoding="utf-8") as file:
            yaml_rt.dump(config, file)

    def _save_text_in_place(self, *, title: str, subtitle: str | None, source: str | None) -> None:
        """Fallback: edit only chart text lines in-place without reserializing YAML."""
        text = self.yaml_path.read_text(encoding="utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        lines = text.splitlines(keepends=True)

        chart_start_idx, chart_indent = self._find_chart_block(lines)
        chart_end_idx = self._find_chart_block_end(lines, chart_start_idx, chart_indent)
        child_indent = self._detect_chart_child_indent(
            lines, chart_start_idx, chart_end_idx, chart_indent
        )

        block_lines = lines[chart_start_idx + 1 : chart_end_idx]
        updated_block_lines = self._update_chart_text_lines(
            block_lines=block_lines,
            child_indent=child_indent,
            title=title,
            subtitle=subtitle,
            source=source,
            newline=newline,
        )

        lines[chart_start_idx + 1 : chart_end_idx] = updated_block_lines
        self.yaml_path.write_text("".join(lines), encoding="utf-8")

    @staticmethod
    def _line_indent_len(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _find_chart_block(self, lines: list[str]) -> tuple[int, str]:
        chart_pattern = re.compile(r"^(\s*)chart:\s*(?:#.*)?(?:\r?\n)?$")
        for idx, line in enumerate(lines):
            match = chart_pattern.match(line)
            if match:
                return idx, match.group(1)
        raise ValueError("Invalid YAML structure: missing 'chart' mapping")

    def _find_chart_block_end(
        self, lines: list[str], chart_start_idx: int, chart_indent: str
    ) -> int:
        chart_indent_len = len(chart_indent)
        for idx in range(chart_start_idx + 1, len(lines)):
            raw = lines[idx]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if self._line_indent_len(raw) <= chart_indent_len:
                return idx
        return len(lines)

    def _detect_chart_child_indent(
        self, lines: list[str], chart_start_idx: int, chart_end_idx: int, chart_indent: str
    ) -> str:
        chart_indent_len = len(chart_indent)
        for idx in range(chart_start_idx + 1, chart_end_idx):
            raw = lines[idx]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent_len = self._line_indent_len(raw)
            if indent_len > chart_indent_len:
                return raw[:indent_len]
        return chart_indent + "  "

    def _update_chart_text_lines(
        self,
        *,
        block_lines: list[str],
        child_indent: str,
        title: str,
        subtitle: str | None,
        source: str | None,
        newline: str,
    ) -> list[str]:
        key_order = ["title", "subtitle", "source"]
        values = {"title": title, "subtitle": subtitle, "source": source}
        key_line_pattern = re.compile(
            rf"^(?P<indent>{re.escape(child_indent)})(?P<key>title|subtitle|source)\s*:\s*"
            r"(?P<value>.*?)(?P<comment>\s+#.*)?(?P<newline>\r?\n?)$"
        )

        def collect_indices(lines: list[str]) -> dict[str, int]:
            idx_map: dict[str, int] = {}
            for line_idx, line in enumerate(lines):
                match = key_line_pattern.match(line)
                if match and match.group("key") not in idx_map:
                    idx_map[match.group("key")] = line_idx
            return idx_map

        def quoted_yaml_string(value: str) -> str:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        output_anchor_idx = None
        output_pattern = re.compile(rf"^{re.escape(child_indent)}output\s*:")
        for idx, line in enumerate(block_lines):
            if output_pattern.match(line):
                output_anchor_idx = idx
                break

        mutable = list(block_lines)
        for key in key_order:
            current_indices = collect_indices(mutable)
            line_idx = current_indices.get(key)
            value = values[key]
            should_remove = key in {"subtitle", "source"} and (value is None or value == "")

            if should_remove:
                if line_idx is not None:
                    mutable.pop(line_idx)
                continue

            if value is None:
                continue

            comment = ""
            line_newline = newline
            if line_idx is not None:
                match = key_line_pattern.match(mutable[line_idx])
                if match:
                    comment = match.group("comment") or ""
                    line_newline = match.group("newline") or newline
                mutable[line_idx] = (
                    f"{child_indent}{key}: {quoted_yaml_string(value)}{comment}{line_newline}"
                )
                continue

            insert_idx = None
            for next_key in key_order[key_order.index(key) + 1 :]:
                next_idx = current_indices.get(next_key)
                if next_idx is not None:
                    insert_idx = next_idx
                    break
            if insert_idx is None:
                for prev_key in reversed(key_order[: key_order.index(key)]):
                    prev_idx = current_indices.get(prev_key)
                    if prev_idx is not None:
                        insert_idx = prev_idx + 1
                        break
            if insert_idx is None and output_anchor_idx is not None:
                insert_idx = output_anchor_idx + 1
            if insert_idx is None:
                insert_idx = 0

            mutable.insert(insert_idx, f"{child_indent}{key}: {quoted_yaml_string(value)}{newline}")

        return mutable
