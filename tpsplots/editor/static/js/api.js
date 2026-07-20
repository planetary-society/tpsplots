/**
 * Centralized API client for the chart editor.
 * All fetch calls go through here for consistent error handling.
 */

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await response.json().catch(() => ({ detail: `Request failed: ${response.status}` }));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

export async function fetchSchema(chartType) {
  return request(`/api/schema?type=${encodeURIComponent(chartType)}`);
}

export async function fetchDataSchema() {
  return request("/api/data-schema");
}

export async function fetchChartTypes() {
  return request("/api/chart-types");
}

export async function fetchColors() {
  return request("/api/colors");
}

export async function fetchPreview(config, device, signal) {
  const resp = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, device }),
    signal,
  });
  if (!resp.ok) {
    // Error responses are JSON with a detail field
    const err = await resp.json().catch(() => ({ detail: `Request failed: ${resp.status}` }));
    throw new Error(err.detail || `Request failed: ${resp.status}`);
  }
  const blob = await resp.blob();
  return URL.createObjectURL(blob);
}

export async function fetchDataProfile(dataConfig) {
  return request("/api/data-profile", {
    method: "POST",
    body: JSON.stringify({ data: dataConfig }),
  });
}

export async function fetchPreflight(config, { path = null, includeYaml = false } = {}) {
  return request("/api/preflight", {
    method: "POST",
    body: JSON.stringify({ config, path, include_yaml: includeYaml }),
  });
}

export async function refreshData() {
  return request("/api/refresh-data", { method: "POST" });
}

export async function loadYaml(path) {
  return request(`/api/load?path=${encodeURIComponent(path)}`);
}

export async function saveYaml(path, config, overrides = {}) {
  // Not routed through request(): a 409 carries a structured body (kind +
  // errors) the save flow needs to branch on, which request() would flatten
  // into a bare Error. Enrich the thrown Error with status/kind/errors so the
  // caller can decide whether to re-POST with override_validation /
  // override_conflict.
  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, config, ...overrides }),
  });
  const data = await response
    .json()
    .catch(() => ({ detail: `Request failed: ${response.status}` }));
  if (!response.ok) {
    const err = new Error(data.detail || `Request failed: ${response.status}`);
    err.status = response.status;
    err.kind = data.kind || null;
    err.errors = data.errors || [];
    throw err;
  }
  return data;
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
