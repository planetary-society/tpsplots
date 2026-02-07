"""Mixin for direct line label placement and collision handling."""

import logging
import math

import matplotlib.dates as mdates
import matplotlib.path as mpath
import matplotlib.transforms
import numpy as np
from matplotlib.transforms import Bbox

logger = logging.getLogger(__name__)


class DirectLineLabelsMixin:
    """Reusable methods for placing labels near lines and endpoints."""

    def _add_direct_line_labels(
        self, ax, y_values, label_info, position="right", offset=0.02, fontsize=12, add_bbox=True
    ):
        """
        Add labels directly on horizontal lines.

        Args:
            ax: Matplotlib axes object
            y_values: List of y-coordinates for labels
            label_info: List of tuples (label_text, color)
            position: Where to place labels ('right', 'left', 'center')
            offset: Horizontal offset from edge as fraction of plot width
            fontsize: Font size for labels
            add_bbox: Whether to add background box to labels
        """
        # Get the current axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        # Calculate x position based on desired alignment
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]

        if position == "right":
            x_pos = xlim[1] - (offset * x_range)
            ha = "right"
        elif position == "left":
            x_pos = xlim[0] + (offset * x_range)
            ha = "left"
        else:  # center
            x_pos = xlim[0] + 0.5 * x_range
            ha = "center"

        # Sort labels by y-value to handle overlapping
        sorted_labels = sorted(zip(y_values, label_info, strict=False), key=lambda x: x[0])

        # Adjust y-positions to prevent overlap
        adjusted_positions = self._adjust_label_positions(
            [y for y, _ in sorted_labels],
            y_range * 0.02,  # 2% of plot height minimum spacing
        )

        # Add each label
        for _i, ((y_val, (label_text, color)), adj_y) in enumerate(
            zip(sorted_labels, adjusted_positions, strict=False)
        ):
            # Create bbox styling if requested
            bbox_props = None
            if add_bbox:
                bbox_props = dict(
                    boxstyle="round,pad=0.2",
                    facecolor="white",
                    edgecolor=color,
                    alpha=0.8,
                    linewidth=1,
                )

            # Add the text label
            ax.text(
                x_pos,
                adj_y,
                label_text,
                fontsize=fontsize,
                ha=ha,
                va="center",
                color=color,
                fontweight="bold",
                bbox=bbox_props,
                zorder=10,  # Make sure labels appear on top
            )

            # If we adjusted the position, draw a small line connecting to the actual line
            if abs(adj_y - y_val) > y_range * 0.01:  # Only if significantly moved
                # Draw a thin connecting line
                connect_x = x_pos + (0.01 * x_range if ha == "right" else -0.01 * x_range)
                ax.plot(
                    [connect_x, x_pos],
                    [y_val, adj_y],
                    color=color,
                    linewidth=1,
                    alpha=0.5,
                    zorder=5,
                )

    def _adjust_label_positions(self, y_positions, min_spacing):
        """
        Adjust label positions to prevent overlapping.

        Args:
            y_positions: List of original y-positions (sorted)
            min_spacing: Minimum spacing between labels

        Returns:
            List of adjusted y-positions
        """
        if len(y_positions) <= 1:
            return y_positions

        adjusted = [y_positions[0]]  # First position stays the same

        for i in range(1, len(y_positions)):
            current_y = y_positions[i]
            prev_adjusted = adjusted[i - 1]

            # If too close to previous label, push it up
            if current_y - prev_adjusted < min_spacing:
                adjusted.append(prev_adjusted + min_spacing)
            else:
                adjusted.append(current_y)

        return adjusted

    def _get_text_bbox_display(self, text, fontsize, color, add_bbox, renderer, ax):
        """Creates a temporary text object and returns its bounding box in display coordinates."""
        if renderer is None:
            return None

        bbox_props = None
        if add_bbox:
            bbox_props = dict(
                boxstyle="round,pad=0.2", facecolor="white", edgecolor=color, alpha=0.8, linewidth=1
            )

        temp_text = ax.text(
            0, 0, text, fontsize=fontsize, fontweight="bold", bbox=bbox_props, visible=False
        )

        try:
            bbox = temp_text.get_window_extent(renderer=renderer)
        except Exception as e:
            logger.warning(f"Could not get window extent for label '{text}': {e}")
            bbox = None
        finally:
            temp_text.remove()

        return bbox

    def _add_direct_line_endpoint_labels(
        self, ax, x_data, y_data, labels, colors, style, fig=None, **kwargs
    ):
        """
        Add labels directly on chart near line endpoints. Uses display coordinates for robust placement.
        """
        # Extract configuration options
        config = kwargs.get("direct_line_labels", {})
        if not isinstance(config, dict):
            config = {}

        position_mode = config.get("position", "auto")
        add_bbox = config.get("bbox", True)
        fontsize = config.get("fontsize", style.get("legend_size", 12))
        end_point_config = config.get("end_point", False)
        markersize_points = kwargs.get("markersize", style.get("marker_size", 6))

        # Parse end_point config - can be:
        # - False: no endpoints
        # - True: default endpoints for all series
        # - dict: same custom style for all series
        # - list: per-series styles (each element can be False, True, or dict)
        end_point_configs = None
        end_point_default_opts = {}
        if isinstance(end_point_config, list):
            end_point_configs = end_point_config
        elif isinstance(end_point_config, dict):
            end_point_configs = "all_same"
            end_point_default_opts = end_point_config
        elif end_point_config:
            end_point_configs = "all_same"

        if fig is None:
            return

        renderer = None
        try:
            renderer = fig.canvas.get_renderer()
        except Exception as e:
            logger.warning(f"Renderer not available for direct labeling: {e}")
            if position_mode == "auto":
                return

        # Handle X data conversion (Categorical to Numeric Indices for transformations)
        if x_data is None:
            if y_data and len(y_data) > 0 and len(y_data[0]) > 0:
                numeric_x = np.arange(len(y_data[0]))
            else:
                return
        elif len(x_data) > 0 and isinstance(next(iter(x_data)), str):
            numeric_x = np.arange(len(x_data))
        else:
            try:
                numeric_x = np.array(x_data)
            except Exception as e:
                logger.error(f"Could not process x_data for direct labeling: {e}")
                return

        # Prepare line data in display coordinates for collision detection (only if auto mode)
        all_line_data_display = []
        if position_mode == "auto" and renderer:
            for y_series in y_data:
                points = []
                y_series_list = list(y_series)

                min_len = min(len(numeric_x), len(y_series_list))
                for i in range(min_len):
                    x = numeric_x[i]
                    y = y_series_list[i]
                    if x is not None and y is not None:
                        try:
                            x_val, y_val = float(x), float(y)
                            if np.isfinite(x_val) and np.isfinite(y_val):
                                points.append((x_val, y_val))
                        except (TypeError, ValueError):
                            continue

                if points:
                    pixels = ax.transData.transform(points)
                    all_line_data_display.append(pixels)

        # Collect endpoint information and find optimal positions
        existing_labels_bboxes = []

        for _i, (y_series, label_text, color) in enumerate(
            zip(y_data, labels, colors, strict=False)
        ):
            if label_text is None:
                continue

            # Find the last non-None/finite point in the series
            last_x_idx = -1
            last_y = None
            y_series_list = list(y_series)

            for idx in range(len(y_series_list) - 1, -1, -1):
                y_val = y_series_list[idx]
                if idx < len(numeric_x) and numeric_x[idx] is not None and y_val is not None:
                    try:
                        y_val_float = float(y_val)
                        if np.isfinite(y_val_float):
                            last_x_idx = idx
                            last_y = y_val_float
                            break
                    except (TypeError, ValueError):
                        continue

            if last_x_idx == -1:
                continue

            last_x = numeric_x[last_x_idx]

            text_bbox = self._get_text_bbox_display(
                label_text, fontsize, color, add_bbox, renderer, ax
            )

            if position_mode == "auto":
                if text_bbox is None:
                    continue
                optimal_pos = self._find_optimal_label_position_display(
                    last_x,
                    last_y,
                    text_bbox,
                    all_line_data_display,
                    existing_labels_bboxes,
                    ax,
                    markersize_points,
                )
            else:
                optimal_pos = self._get_simple_label_position(
                    last_x, last_y, text_bbox, position_mode, ax, markersize_points
                )

            if optimal_pos:
                bbox_props = None
                if add_bbox:
                    bbox_props = dict(
                        boxstyle="round,pad=0.2",
                        facecolor="white",
                        edgecolor=color,
                        alpha=0.8,
                        linewidth=1,
                    )

                ax.text(
                    optimal_pos["x_data"],
                    optimal_pos["y_data"],
                    label_text,
                    fontsize=fontsize,
                    ha=optimal_pos["ha"],
                    va=optimal_pos["va"],
                    color=color,
                    fontweight="bold",
                    bbox=bbox_props,
                    zorder=10,
                )
                if optimal_pos["bbox_display"] is not None:
                    existing_labels_bboxes.append(optimal_pos["bbox_display"])

                # Draw endpoint marker if enabled
                show_this_endpoint = False
                this_endpoint_opts = {}

                if end_point_configs == "all_same":
                    show_this_endpoint = True
                    this_endpoint_opts = end_point_default_opts
                elif isinstance(end_point_configs, list) and _i < len(end_point_configs):
                    series_ep_config = end_point_configs[_i]
                    if isinstance(series_ep_config, dict):
                        show_this_endpoint = True
                        this_endpoint_opts = series_ep_config
                    elif series_ep_config:
                        show_this_endpoint = True

                if show_this_endpoint:
                    ep_marker = this_endpoint_opts.get("marker", "o")
                    ep_size = this_endpoint_opts.get("size", markersize_points)
                    ep_facecolor = this_endpoint_opts.get("facecolor", color)
                    ep_edgecolor = this_endpoint_opts.get("edgecolor", "white")
                    ep_edgewidth = this_endpoint_opts.get("edgewidth", 1.5)
                    ep_zorder = this_endpoint_opts.get("zorder", 9)

                    ax.plot(
                        last_x,
                        last_y,
                        marker=ep_marker,
                        markersize=ep_size,
                        color=color,
                        markerfacecolor=ep_facecolor,
                        markeredgecolor=ep_edgecolor,
                        markeredgewidth=ep_edgewidth,
                        linestyle="None",
                        zorder=ep_zorder,
                    )

    def _get_simple_label_position(
        self, x_data, y_data, text_bbox, position_mode, ax, markersize_points
    ):
        """Calculates position for simple modes using point offsets (DPI-aware)."""
        gap_points = 8
        minimum_offset_points = 12
        offset_points = max((markersize_points / 2.0) + gap_points, minimum_offset_points)

        if position_mode == "right":
            x_offset, y_offset = offset_points, 0
            ha, va = "left", "center"
        elif position_mode == "left":
            x_offset, y_offset = -offset_points, 0
            ha, va = "right", "center"
        elif position_mode == "above" or position_mode == "top":
            x_offset, y_offset = 0, offset_points
            ha, va = "center", "bottom"
        elif position_mode == "below" or position_mode == "bottom":
            x_offset, y_offset = 0, -offset_points
            ha, va = "center", "top"
        else:
            x_offset, y_offset = offset_points, 0
            ha, va = "left", "center"

        # Convert datetime to matplotlib date numbers for proper transform round-trip
        x_for_transform = x_data
        if hasattr(x_data, "dtype") and np.issubdtype(x_data.dtype, np.datetime64):
            x_for_transform = mdates.date2num(x_data)

        transform = matplotlib.transforms.offset_copy(
            ax.transData, fig=ax.get_figure(), x=x_offset, y=y_offset, units="points"
        )

        anchor_display = transform.transform((x_for_transform, y_data))
        anchor_data = ax.transData.inverted().transform(anchor_display)
        final_x = anchor_data[0]

        final_bbox = None
        if text_bbox is not None:
            width, height = text_bbox.width, text_bbox.height
            x0, y0 = anchor_display[0], anchor_display[1]

            if ha == "left":
                x_start = x0
            elif ha == "right":
                x_start = x0 - width
            else:  # center
                x_start = x0 - width / 2

            if va == "bottom":
                y_start = y0
            elif va == "top":
                y_start = y0 - height
            else:  # center
                y_start = y0 - height / 2

            final_bbox = Bbox.from_bounds(x_start, y_start, width, height)

        return {
            "x_data": final_x,
            "y_data": anchor_data[1],
            "ha": ha,
            "va": va,
            "bbox_display": final_bbox,
        }

    def _find_optimal_label_position_display(
        self,
        x_data,
        y_data,
        text_bbox,
        all_line_data_display,
        existing_labels_bboxes,
        ax,
        markersize_points,
    ):
        """
        Finds the optimal label position using a clockwise search strategy in display coordinates.
        """
        try:
            endpoint_px = ax.transData.transform([(x_data, y_data)])[0]
            ep_x_px, ep_y_px = endpoint_px[0], endpoint_px[1]
        except Exception as e:
            logger.error(f"Error transforming endpoint coordinates: {e}")
            return None

        # Define offsets in pixels (DPI-aware)
        dpi = ax.get_figure().get_dpi()
        gap_points = 8
        minimum_offset_points = 12
        offset_points = max((markersize_points / 2.0) + gap_points, minimum_offset_points)
        offset_px = offset_points * (dpi / 72.0)

        text_width_px = text_bbox.width
        text_height_px = text_bbox.height

        renderer = ax.get_figure().canvas.get_renderer()
        ax_bbox = ax.get_window_extent(renderer=renderer)

        priority_directions = [
            (0, "left", "center"),  # Right (preferred)
            (315, "left", "top"),  # Bottom-right
            (270, "center", "top"),  # Bottom
            (225, "right", "top"),  # Bottom-left
            (180, "right", "center"),  # Left
            (135, "right", "bottom"),  # Top-left
            (90, "center", "bottom"),  # Top
            (45, "left", "bottom"),  # Top-right
        ]

        best_position = None
        best_score = float("inf")

        for pref_order, (angle_deg, ha, va) in enumerate(priority_directions):
            angle_rad = math.radians(angle_deg)

            anchor_x_px = ep_x_px + offset_px * math.cos(angle_rad)
            anchor_y_px = ep_y_px + offset_px * math.sin(angle_rad)

            if ha == "left":
                bbox_x1 = anchor_x_px
            elif ha == "right":
                bbox_x1 = anchor_x_px - text_width_px
            else:  # center
                bbox_x1 = anchor_x_px - text_width_px / 2

            if va == "bottom":
                bbox_y1 = anchor_y_px
            elif va == "top":
                bbox_y1 = anchor_y_px - text_height_px
            else:  # center
                bbox_y1 = anchor_y_px - text_height_px / 2

            bbox_x2 = bbox_x1 + text_width_px
            bbox_y2 = bbox_y1 + text_height_px
            label_bbox = Bbox.from_extents(bbox_x1, bbox_y1, bbox_x2, bbox_y2)

            score = self._score_label_position_display(
                label_bbox, pref_order, all_line_data_display, existing_labels_bboxes, ax_bbox
            )

            if score < best_score:
                best_score = score
                anchor_data = ax.transData.inverted().transform([(anchor_x_px, anchor_y_px)])[0]
                best_position = {
                    "x_data": anchor_data[0],
                    "y_data": anchor_data[1],
                    "ha": ha,
                    "va": va,
                    "score": score,
                    "bbox_display": label_bbox,
                }

            if score == 0:
                break

        if best_position is None:
            logger.warning(
                "Could not find an optimal position for the label. Falling back to 'right'."
            )
            return self._get_simple_label_position(
                x_data, y_data, text_bbox, "right", ax, markersize_points
            )

        return best_position

    def _score_label_position_display(
        self, label_bbox, pref_order, all_line_data_display, existing_labels_bboxes, ax_bbox
    ):
        """Scores the label position in pixel coordinates. Lower is better."""
        score = 0

        score += pref_order * 5

        # Heavy penalty for going outside axes bounds.
        padding = 5
        if (
            label_bbox.x0 < ax_bbox.x0 + padding
            or label_bbox.x1 > ax_bbox.x1 - padding
            or label_bbox.y0 < ax_bbox.y0 + padding
            or label_bbox.y1 > ax_bbox.y1 - padding
        ):
            score += 200

        # Penalty for overlapping with existing labels.
        buffer = 4
        try:
            buffered_bbox = label_bbox.expanded(
                1 + buffer / label_bbox.width, 1 + buffer / label_bbox.height
            )
        except ZeroDivisionError:
            buffered_bbox = label_bbox

        for existing_bbox in existing_labels_bboxes:
            if buffered_bbox.overlaps(existing_bbox):
                score += 100

        # Penalty for overlapping with line segments.
        if self._label_intersects_line_display(label_bbox, all_line_data_display):
            score += 50

        return score

    def _label_intersects_line_display(self, bbox, all_line_data_display):
        """Checks whether the bounding box intersects any lines."""
        try:
            bbox_path = mpath.Path(bbox.corners(), closed=True)
        except Exception as e:
            logger.warning(f"Could not create bbox path for intersection check: {e}")
            return False

        for line_pixels in all_line_data_display:
            if len(line_pixels) < 2:
                continue

            try:
                line_path = mpath.Path(line_pixels)
                if bbox_path.intersects_path(line_path, filled=True):
                    return True
                if bbox.contains_points(line_pixels).any():
                    return True
            except Exception as e:
                logger.debug(f"Line path intersection check failed: {e}")

        return False
