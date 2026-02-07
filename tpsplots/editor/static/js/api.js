/**
 * Centralized API client for the chart editor.
 * All fetch calls go through here for consistent error handling.
 */

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

export async function fetchSchema(chartType) {
  return request(`/api/schema?type=${encodeURIComponent(chartType)}`);
}

export async function fetchChartTypes() {
  return request("/api/chart-types");
}

export async function fetchColors() {
  return request("/api/colors");
}

export async function fetchPreview(config, device, signal) {
  return request("/api/preview", {
    method: "POST",
    body: JSON.stringify({ config, device }),
    signal,
  });
}

export async function loadYaml(path) {
  return request(`/api/load?path=${encodeURIComponent(path)}`);
}

export async function saveYaml(path, config) {
  return request("/api/save", {
    method: "POST",
    body: JSON.stringify({ path, config }),
  });
}

export async function validateConfig(config) {
  return request("/api/validate", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function listFiles() {
  return request("/api/files");
}

export async function fetchTemplate(chartType) {
  return request(`/api/templates/${encodeURIComponent(chartType)}`);
}

export async function fetchAvailableTemplates() {
  return request("/api/templates");
}
