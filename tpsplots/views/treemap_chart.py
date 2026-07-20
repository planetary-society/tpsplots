"""Treemap chart rendering view."""

import math
import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import ClassVar

import squarify
from matplotlib import pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import Rectangle

from tpsplots.models.charts.treemap import TreemapChartConfig, raise_for_geometry_overrides
from tpsplots.views.chart_view import ChartView
from tpsplots.views.mixins.color_cycle_mixin import ColorCycleMixin
from tpsplots.views.style import tokens


@dataclass(frozen=True, slots=True)
class _TreemapItem:
    """A validated tile whose related fields remain associated while sorting."""

    label: str
    value: float
    color: str


class TreemapChartView(ColorCycleMixin, ChartView):
    """Render flat treemaps for desktop, mobile, and social outputs."""

    CONFIG_CLASS: ClassVar[type] = TreemapChartConfig

    def treemap_plot(self, metadata, stem, **kwargs):
        """Generate desktop, mobile, and social treemap outputs."""
        return self.generate_chart(metadata, stem, **kwargs)

    @staticmethod
    def _as_nonempty_sequence(name: str, value) -> list:
        if (
            value is None
            or isinstance(value, (str, bytes, Mapping))
            or not isinstance(value, Iterable)
        ):
            raise ValueError(f"The '{name}' parameter must be a non-empty sequence")

        sequence = list(value)
        if not sequence:
            raise ValueError(f"The '{name}' parameter must be a non-empty sequence")
        return sequence

    def _normalize_items(self, labels, values, colors=None) -> list[_TreemapItem]:
        """Attach related fields and return a stable largest-first ordering."""
        normalized_labels = self._as_nonempty_sequence("labels", labels)
        normalized_values = self._as_nonempty_sequence("values", values)
        if len(normalized_labels) != len(normalized_values):
            raise ValueError("The 'labels' and 'values' parameters must have equal lengths")

        if any(label is None for label in normalized_labels):
            raise ValueError("Treemap labels cannot be null")

        numeric_values: list[float] = []
        for value in normalized_values:
            if isinstance(value, bool):
                raise ValueError("Treemap values must be numeric, finite, and greater than zero")
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Treemap values must be numeric, finite, and greater than zero"
                ) from exc
            if not math.isfinite(numeric_value) or numeric_value <= 0:
                raise ValueError("Treemap values must be numeric, finite, and greater than zero")
            numeric_values.append(numeric_value)

        try:
            total = math.fsum(numeric_values)
        except OverflowError as exc:
            raise ValueError("Treemap values must have a finite total") from exc
        if not math.isfinite(total):
            raise ValueError("Treemap values must have a finite total")

        explicit_colors = colors
        if colors is not None and not isinstance(colors, str):
            explicit_colors = self._as_nonempty_sequence("colors", colors)

        # Largest tiles first; the stable sort keeps equal-valued tiles in input order.
        ranked = sorted(
            enumerate(zip(normalized_labels, numeric_values, strict=True)),
            key=lambda row: row[1][1],
            reverse=True,
        )
        if colors is None:
            # The default cycle is assigned by rank so the largest tile leads the palette.
            palette = self._get_cycled_colors(len(ranked))
            return [
                _TreemapItem(str(label), value, palette[rank])
                for rank, (_source_index, (label, value)) in enumerate(ranked)
            ]

        # Explicit colors stay bound to their source position through the sort.
        palette = self._get_cycled_colors(len(ranked), colors=explicit_colors)
        return [
            _TreemapItem(str(label), value, palette[source_index])
            for source_index, (label, value) in ranked
        ]

    @staticmethod
    def _layout_items(
        items: list[_TreemapItem], width: float, height: float
    ) -> list[tuple[_TreemapItem, dict[str, float]]]:
        """Compute squarified rectangles in the requested drawing-space ratio."""
        normalized_values = squarify.normalize_sizes([item.value for item in items], width, height)
        rectangles = squarify.squarify(normalized_values, 0, 0, width, height)
        return list(zip(items, rectangles, strict=True))

    def _format_tile_text(
        self,
        item: _TreemapItem,
        total: float,
        show_labels: bool,
        show_values: bool,
        show_percentages: bool,
        value_format: str,
        wrap_length: int,
    ) -> str:
        """Build independently controlled label, value, and percentage lines."""
        lines: list[str] = []
        if show_labels:
            lines.extend(
                textwrap.wrap(item.label, width=wrap_length, break_long_words=False) or [item.label]
            )
        if show_values:
            lines.append(self._format_value(item.value, value_format))
        if show_percentages:
            lines.append(f"{item.value / total * 100:.1f}%")
        return "\n".join(lines)

    @staticmethod
    def _contrast_text_color(facecolor, alpha: float, background) -> str:
        """Choose black or white using WCAG contrast after alpha compositing."""
        foreground_rgba = to_rgba(facecolor)
        background_rgba = to_rgba(background)
        effective_alpha = foreground_rgba[3] * alpha
        rgb = tuple(
            foreground_rgba[index] * effective_alpha
            + background_rgba[index] * (1 - effective_alpha)
            for index in range(3)
        )

        def linearize(channel: float) -> float:
            return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

        red, green, blue = (linearize(channel) for channel in rgb)
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        black_contrast = (luminance + 0.05) / 0.05
        white_contrast = 1.05 / (luminance + 0.05)
        return "#000000" if black_contrast >= white_contrast else "#FFFFFF"

    def _resolve_color(self, color):
        if color in self.COLORS:
            return self.COLORS[color]
        if color in self.TPS_COLORS:
            return self.TPS_COLORS[color]
        return color

    def _draw_tiles(
        self,
        ax,
        tiles: list[tuple[_TreemapItem, dict[str, float]]],
        *,
        edgecolor,
        linewidth: float,
        alpha: float,
        patch_config: dict,
    ) -> list[tuple[_TreemapItem, Rectangle]]:
        drawn: list[tuple[_TreemapItem, Rectangle]] = []
        resolved_edgecolor = self._resolve_color(edgecolor)
        for item, rect in tiles:
            patch_kwargs = {
                "facecolor": self._resolve_color(item.color),
                "edgecolor": resolved_edgecolor,
                "linewidth": linewidth,
                "alpha": alpha,
            }
            patch_kwargs.update(patch_config)
            patch = Rectangle((rect["x"], rect["y"]), rect["dx"], rect["dy"], **patch_kwargs)
            ax.add_patch(patch)
            drawn.append((item, patch))
        return drawn

    def _draw_fitting_labels(
        self,
        ax,
        drawn_tiles: list[tuple[_TreemapItem, Rectangle]],
        *,
        total: float,
        show_labels: bool,
        show_values: bool,
        show_percentages: bool,
        value_format: str,
        label_min_area_pct: float,
        label_wrap_length: int,
        label_fontsize: float,
    ) -> None:
        """Draw candidate labels once, then hide any that exceed a 4pt tile inset."""
        if not show_labels and not show_values and not show_percentages:
            return

        candidates: list[tuple[Rectangle, object]] = []
        background = ax.get_facecolor()
        for item, patch in drawn_tiles:
            if item.value / total * 100 < label_min_area_pct:
                continue
            label_text = self._format_tile_text(
                item,
                total,
                show_labels,
                show_values,
                show_percentages,
                value_format,
                label_wrap_length,
            )
            if not label_text:
                continue

            text = ax.text(
                patch.get_x() + patch.get_width() / 2,
                patch.get_y() + patch.get_height() / 2,
                label_text,
                ha="center",
                va="center",
                fontsize=label_fontsize,
                fontweight="bold",
                color=self._contrast_text_color(patch.get_facecolor(), 1.0, background),
                clip_on=True,
            )
            candidates.append((patch, text))

        if not candidates:
            return

        figure = ax.figure
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        inset = 4 * figure.dpi / 72
        for patch, text in candidates:
            corners = ax.transData.transform(
                [
                    (patch.get_x(), patch.get_y()),
                    (
                        patch.get_x() + patch.get_width(),
                        patch.get_y() + patch.get_height(),
                    ),
                ]
            )
            tile_x0, tile_x1 = min(corners[:, 0]), max(corners[:, 0])
            tile_y0, tile_y1 = min(corners[:, 1]), max(corners[:, 1])
            text_bbox = text.get_window_extent(renderer)
            fits = (
                text_bbox.x0 >= tile_x0 + inset
                and text_bbox.x1 <= tile_x1 - inset
                and text_bbox.y0 >= tile_y0 + inset
                and text_bbox.y1 <= tile_y1 - inset
            )
            if not fits:
                text.set_visible(False)

    def _create_chart(self, metadata, style, **kwargs):
        labels = kwargs.pop("labels", None)
        values = kwargs.pop("values", None)
        colors = kwargs.pop("colors", None)
        if values is not None:
            values = self._coerce_numeric_values(values)
        items = self._normalize_items(labels, values, colors)

        edgecolor = kwargs.pop("edgecolor", tokens.TREEMAP_EDGECOLOR)
        linewidth = kwargs.pop("linewidth", 2.0)
        alpha = kwargs.pop("alpha", 1.0)
        show_labels = kwargs.pop("show_labels", True)
        show_values = kwargs.pop("show_values", False)
        show_percentages = kwargs.pop("show_percentages", True)
        value_format = kwargs.pop("value_format", "float")
        label_min_area_pct = kwargs.pop("label_min_area_pct", 1.0)
        label_wrap_length = kwargs.pop("label_wrap_length", style.get("label_wrap_length", 15))
        label_fontsize = kwargs.pop("label_fontsize", style.get("label_size", 12))
        raise_for_geometry_overrides(kwargs)

        fig = None
        try:
            fig, ax = self._setup_figure(style, kwargs)
            self._extract_metadata_from_kwargs(metadata, kwargs)
            # The pipeline flattens matplotlib_config into kwargs before the view runs,
            # so whatever survives the typed pops above is the raw tile-style override.
            patch_config = dict(kwargs)
            ax.set_axis_off()

            self._adjust_layout_for_header_footer(fig, metadata, style)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            axes_bbox = ax.get_window_extent(renderer)
            layout_height = 100.0
            layout_width = layout_height * axes_bbox.width / axes_bbox.height
            tiles = self._layout_items(items, layout_width, layout_height)
            drawn_tiles = self._draw_tiles(
                ax,
                tiles,
                edgecolor=edgecolor,
                linewidth=linewidth,
                alpha=alpha,
                patch_config=patch_config,
            )

            ax.set_xlim(0, layout_width)
            ax.set_ylim(0, layout_height)
            ax.set_aspect("equal", adjustable="box")
            ax.invert_yaxis()
            self._draw_fitting_labels(
                ax,
                drawn_tiles,
                total=math.fsum(item.value for item in items),
                show_labels=show_labels,
                show_values=show_values,
                show_percentages=show_percentages,
                value_format=value_format,
                label_min_area_pct=label_min_area_pct,
                label_wrap_length=label_wrap_length,
                label_fontsize=label_fontsize,
            )
            return fig
        except Exception:
            if fig is not None:
                plt.close(fig)
            raise
