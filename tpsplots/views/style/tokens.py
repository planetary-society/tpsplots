"""Single source of truth for hardcoded chart style constants.

This module centralizes the scattered magic values (colors, line widths,
alphas, box styles, etc.) that were previously inlined across the view and
mixin modules. Consolidating them here creates one seam for later theming work.

Guidelines
----------
- Every constant here preserves the *exact* value it replaced, so hoisting a
  literal into this module is a zero-visual-change refactor.
- Consumers must read these names **at call time** -- reference ``tokens.X``
  inside a function body, or use ``None``-sentinel parameter defaults resolved
  in the body -- rather than binding them as def-time parameter defaults. That
  way a later runtime mutation of a token propagates to every consumer.
"""

from tpsplots.colors import COLORS

# ── Grid lines (GridAxisMixin) ─────────────────────────────────────
GRID_ALPHA = 1.0
GRID_LINESTYLE = "-"
GRID_LINEWIDTH = 0.8

# ── Direct line labels (DirectLineLabelsMixin) ─────────────────────
DIRECT_LABEL_BBOX_BOXSTYLE = "round,pad=0.2"
DIRECT_LABEL_BBOX_FACECOLOR = "white"
DIRECT_LABEL_BBOX_ALPHA = 0.8
DIRECT_LABEL_BBOX_LINEWIDTH = 1


def direct_label_bbox(edgecolor):
    """Return the white rounded ``bbox`` dict used behind direct line labels.

    The three label-drawing sites shared an identical bbox spec differing only
    by ``edgecolor`` (the series colour), so that is the sole parameter. Values
    are read from the module-level tokens at call time so runtime mutation of a
    token propagates here.
    """
    return dict(
        boxstyle=DIRECT_LABEL_BBOX_BOXSTYLE,
        facecolor=DIRECT_LABEL_BBOX_FACECOLOR,
        edgecolor=edgecolor,
        alpha=DIRECT_LABEL_BBOX_ALPHA,
        linewidth=DIRECT_LABEL_BBOX_LINEWIDTH,
    )


# Direct-label offset from the series endpoint: clearance beyond the
# marker/ring edge, and the floor used when markers are small.
DIRECT_LABEL_GAP_POINTS = 10
DIRECT_LABEL_MIN_OFFSET_POINTS = 12

# ── Bar charts (BarChartView, GroupedBarChartView) ─────────────────
BAR_EDGECOLOR = "white"

# ── Area charts (AreaChartView) ──────────────────────────
AREA_ALPHA = 0.65
STACKED_AREA_ALPHA = 1.0
AREA_EDGECOLOR = "none"
AREA_LINEWIDTH = 0.0

# ── Lollipop chart (LollipopChartView) ─────────────────────────────
LOLLIPOP_MARKER_EDGECOLOR = "white"

# ── Donut chart (DonutChartView) ───────────────────────────────────
DONUT_WEDGE_LINEWIDTH = 7
DONUT_WEDGE_EDGECOLOR = "white"
DONUT_HOLE_SIZE = 0.7
# Center circle fill; preserves the historical self.COLORS["light_gray"] value.
DONUT_CENTER_COLOR = COLORS["light_gray"]

# ── Treemap chart (TreemapChartView) ───────────────────────────────
# Semantic TPS colour name, resolved downstream by the colour resolver.
TREEMAP_EDGECOLOR = "Polar White"

# ── Header text (ChartView._add_header) ───────────────────────────
# Deep near-black title with a lighter gray subtitle for hierarchy on the
# brine canvas; themes override them.
TITLE_COLOR = "#101114"
SUBTITLE_COLOR = "#545454"

# ── Axis labels (GridAxisMixin._apply_axis_labels) ─────────────────
AXIS_LABEL_ITALIC = False

# ── Line endpoints (DirectLineLabelsMixin) ─────────────────────────
# When True, plain "o" endpoint markers gain an unfilled "orbit ring" in the
# series color (theme signature; on by default). Charts can also request the
# ring explicitly via ``end_point: {marker: ring}`` regardless of this token.
ENDPOINT_RING = True
ENDPOINT_RING_SCALE = 2.1  # ring diameter as a multiple of the endpoint size
ENDPOINT_RING_WIDTH = 1.2  # ring stroke width (points)

# ── Footer + logo (ChartView, logo) ────────────────────────────────
FOOTER_COLOR = "#545454"
LOGO_COLOR = "#545454"
# Full-width band painted behind the footer zone; None = no band.
FOOTER_BAND_COLOR = None

# ── Header eyebrow / kicker (ChartView._add_header) ────────────────
# Short line rendered above the title. Neptune Blue kicker in Poppins
# SemiBold (matplotlib maps the "semibold" weight name to numeric 600).
# Sized as a fraction of the device title_size.
EYEBROW_COLOR = "#037CC2"
EYEBROW_WEIGHT = "semibold"
EYEBROW_SIZE_RATIO = 0.45
# Vertical space reserved above the title for the eyebrow, as a fraction of the
# eyebrow's measured "Ag" line box. That reference box carries ascender +
# descender whitespace the all-caps kicker never occupies, so reserving the
# full box (ratio 1.0+) floats the eyebrow well above the headline. A value
# below 1.0 reclaims that dead space and pulls the kicker down to hug the
# title; ~0.6 leaves a gap comparable to the title/subtitle rhythm. Used
# identically by the measure and draw passes so reserved == drawn.
EYEBROW_STACK_RATIO = 0.6
# How far to pull the subtitle UP toward the title's baseline, as a fraction of
# a single TITLE line box. The title's box bottom is its descender line, which
# sits well below the baseline where the text body visually rests; anchoring
# the subtitle there makes titles ending in a descender ("...Funding") read as
# a large gap. Reclaiming roughly the title's descender depth pulls the
# subtitle up to hug the baseline, matching the eyebrow→title rhythm. Larger =
# tighter. The title's descender ink and the subtitle's caps are horizontally
# offset, so the overlap reads as tight leading, never a collision.
TITLE_SUBTITLE_OVERLAP_RATIO = 0.115
# Optional short accent rule drawn just above the eyebrow (theme signature;
# None = no rule). Length is a figure-width fraction.
EYEBROW_RULE_COLOR = None
EYEBROW_RULE_LENGTH = 0.028
EYEBROW_RULE_LINEWIDTH = 3

# ── Data annotations (ChartView._apply_annotations) ────────────────
# Body-text gray for on-axes annotation ink (inside the callout box).
ANNOTATION_COLOR = "#414141"
# Default callout box border + arrow colour (Lunar Soil). Overridable per
# annotation via the ChartAnnotation ``color`` field. Chosen to read as a quiet
# frame rather than competing with the data ink.
ANNOTATION_EDGE_COLOR = "#8C8C8C"
# Curved connector arrow geometry (drawarrow FancyArrowPatch). A thin 1pt line
# with a small head and a gentle arc; ``radius`` is an arc3 chord fraction so the
# curve amount is scale-independent.
ANNOTATION_ARROW_WIDTH = 1.0
ANNOTATION_ARROW_RADIUS = 0.12
ANNOTATION_ARROW_HEAD_WIDTH = 3.2
ANNOTATION_ARROW_HEAD_LENGTH = 6.5
# Layering: arrow below the box, box below the ink, all above the plotted data
# and the direct-line labels (zorder 10) so callouts stay legible on top.
ANNOTATION_ARROW_ZORDER = 10.5
ANNOTATION_BOX_ZORDER = 11.0
ANNOTATION_TEXT_ZORDER = 11.5
