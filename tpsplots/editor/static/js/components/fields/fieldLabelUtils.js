/**
 * Shared label/tooltip helpers for editor form fields.
 */

const FIELD_LABEL_OVERRIDES = {
  x: "X-axis Data",
  y: "Y-axis Data",
  xlabel: "X-axis Label",
  ylabel: "Y-axis Label",
  xlim: "X-axis Range",
  ylim: "Y-axis Range",
  xticks: "X-axis Tick Positions",
  xticklabels: "X-axis Tick Labels",
  yticks: "Y-axis Tick Positions",
  yticklabels: "Y-axis Tick Labels",
  grid_axis: "Grid Axis",
  max_xticks: "Maximum X-axis Ticks",
  x_tick_format: "X-axis Tick Number Format",
  y_tick_format: "Y-axis Tick Number Format",
  axis_scale: "Scale Target Axis",
  hlines: "Horizontal Reference Lines",
  hline_colors: "Reference Line Colors",
  hline_styles: "Reference Line Styles",
  hline_widths: "Reference Line Widths",
  hline_labels: "Reference Line Labels",
  y_right: "Right Y-axis Data",
  ylim_right: "Right Y-axis Range",
  ylabel_right: "Right Y-axis Label",
  y_tick_format_right: "Right Y-axis Tick Format",
  scale_right: "Right Y-axis Scale",
};

const TOKEN_LABELS = {
  id: "ID",
  ids: "IDs",
  api: "API",
  csv: "CSV",
  dpi: "DPI",
  fy: "FY",
  gdp: "GDP",
  nnsi: "NNSI",
  pdf: "PDF",
  png: "PNG",
  pptx: "PPTX",
  s3: "S3",
  ui: "UI",
  url: "URL",
  urls: "URLs",
  yaml: "YAML",
  x: "X",
  y: "Y",
};

function titleizeToken(token) {
  if (!token) return "";
  const lower = token.toLowerCase();
  if (TOKEN_LABELS[lower]) return TOKEN_LABELS[lower];
  if (/^\d+$/.test(token)) return token;
  return token.charAt(0).toUpperCase() + token.slice(1);
}

export function formatFieldLabel(fieldName, schema) {
  const key = String(fieldName || "").trim();
  if (!key) return "";

  if (FIELD_LABEL_OVERRIDES[key]) return FIELD_LABEL_OVERRIDES[key];

  const schemaTitle =
    typeof schema?.title === "string" ? schema.title.trim().replace(/\s+/g, " ") : "";
  if (schemaTitle && schemaTitle.toLowerCase() !== key.toLowerCase()) {
    return schemaTitle;
  }

  return key
    .split("_")
    .filter(Boolean)
    .map((token) => titleizeToken(token))
    .join(" ");
}

export function yamlKeyTooltip(fieldName) {
  return `YAML key: ${fieldName}`;
}

