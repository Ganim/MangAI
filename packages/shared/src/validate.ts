import { ValidationError } from "./errors.ts";
import { isEnumValue } from "./enums.ts";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function atPath(basePath: Array<string | number>, ...keys: Array<string | number>) {
  return [...basePath, ...keys];
}

export function readObject<T extends object = Record<string, unknown>>(
  value: unknown,
  path: Array<string | number> = [],
): T {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ValidationError("Expected an object", path);
  }
  return value as T;
}

export function readString(
  value: unknown,
  path: Array<string | number> = [],
  options: { minLength?: number; allowEmpty?: boolean } = {},
) {
  const { minLength = 1, allowEmpty = false } = options;
  if (typeof value !== "string") {
    throw new ValidationError("Expected a string", path);
  }

  if (!allowEmpty && value.trim().length < minLength) {
    throw new ValidationError("Expected a non-empty string", path);
  }

  if (allowEmpty && value.length < minLength) {
    throw new ValidationError(`Expected a string of length >= ${minLength}`, path);
  }

  return value;
}

export function readBoolean(value: unknown, path: Array<string | number> = []) {
  if (typeof value !== "boolean") {
    throw new ValidationError("Expected a boolean", path);
  }
  return value;
}

export function readNumber(
  value: unknown,
  path: Array<string | number> = [],
  options: { integer?: boolean; min?: number; max?: number } = {},
) {
  const { integer = false, min, max } = options;
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new ValidationError("Expected a number", path);
  }
  if (integer && !Number.isInteger(value)) {
    throw new ValidationError("Expected an integer", path);
  }
  if (min !== undefined && value < min) {
    throw new ValidationError(`Expected a number >= ${min}`, path);
  }
  if (max !== undefined && value > max) {
    throw new ValidationError(`Expected a number <= ${max}`, path);
  }
  return value;
}

export function readEnum<T extends readonly string[]>(
  value: unknown,
  allowedValues: T,
  path: Array<string | number> = [],
): T[number] {
  if (!isEnumValue(value, allowedValues)) {
    throw new ValidationError(`Expected one of: ${allowedValues.join(", ")}`, path);
  }
  return value;
}

export function readUuid(value: unknown, path: Array<string | number> = []) {
  const stringValue = readString(value, path);
  if (!UUID_RE.test(stringValue)) {
    throw new ValidationError("Expected a UUID", path);
  }
  return stringValue;
}

export function readNullableUuid(value: unknown, path: Array<string | number> = []) {
  if (value === null || value === undefined) {
    return null;
  }
  return readUuid(value, path);
}

export function readTimestamp(value: unknown, path: Array<string | number> = []) {
  const stringValue = readString(value, path);
  if (Number.isNaN(Date.parse(stringValue))) {
    throw new ValidationError("Expected an ISO 8601 timestamp", path);
  }
  return stringValue;
}

export function readArray<T>(
  value: unknown,
  path: Array<string | number> = [],
  itemReader: (item: unknown, itemPath: Array<string | number>) => T = (item) => item as T,
  options: { minLength?: number } = {},
) {
  const { minLength = 0 } = options;
  if (!Array.isArray(value)) {
    throw new ValidationError("Expected an array", path);
  }
  if (value.length < minLength) {
    throw new ValidationError(`Expected at least ${minLength} items`, path);
  }
  return value.map((item, index) => itemReader(item, atPath(path, index)));
}

export function readOptional<T>(
  value: unknown,
  reader: (input: unknown, path: Array<string | number>) => T,
  path: Array<string | number> = [],
) {
  if (value === undefined) {
    return undefined;
  }
  return reader(value, path);
}

export function readNullable<T>(
  value: unknown,
  reader: (input: unknown, path: Array<string | number>) => T,
  path: Array<string | number> = [],
) {
  if (value === null || value === undefined) {
    return null;
  }
  return reader(value, path);
}
