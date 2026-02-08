/**
 * Shared mapping from JSON Schema type to field component.
 * Used by SchemaForm (top-level rendering) and UnionField (branch rendering).
 */
import { StringField } from "./StringField.js";
import { NumberField } from "./NumberField.js";
import { BooleanField } from "./BooleanField.js";
import { ObjectField } from "./ObjectField.js";
import { ArrayField } from "./ArrayField.js";

export const FIELD_COMPONENTS = {
  string: StringField,
  integer: NumberField,
  number: NumberField,
  boolean: BooleanField,
  object: ObjectField,
  array: ArrayField,
};
