/**
 * Helpers for resolving local JSON-schema refs (e.g. #/$defs/Foo).
 */

function decodeJsonPointerToken(token) {
  return token.replace(/~1/g, "/").replace(/~0/g, "~");
}

function resolveJsonPointer(root, ref) {
  if (!root || typeof ref !== "string" || !ref.startsWith("#/")) return null;
  const segments = ref
    .slice(2)
    .split("/")
    .map(decodeJsonPointerToken)
    .filter(Boolean);

  let current = root;
  for (const segment of segments) {
    if (current == null || typeof current !== "object" || !(segment in current)) {
      return null;
    }
    current = current[segment];
  }
  return current ?? null;
}

export function resolveSchemaRef(schema, rootSchema) {
  if (!schema || typeof schema !== "object") return schema;
  if (!schema.$ref) return schema;

  const target = resolveJsonPointer(rootSchema, schema.$ref);
  if (!target || typeof target !== "object") return schema;

  // Keep explicit field-level metadata (description/default/etc.) on top.
  const merged = { ...target, ...schema };
  delete merged.$ref;
  return merged;
}

