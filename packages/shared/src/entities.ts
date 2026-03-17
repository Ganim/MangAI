import {
  AssetKind,
  AssignmentOrigin,
  CleanupStrategy,
  DialogueSource,
  DialogueStatus,
  ExportFormat,
  JobStatus,
  JobType,
  PageStatus,
  ProjectStatus,
  RegionOrigin,
  RegionState,
  RegionType,
  SCHEMA_VERSION,
  TextDirection,
  TranslationStatus,
} from "./enums.ts";
import { ValidationError } from "./errors.ts";
import { canonicalizeLanguageTag } from "./i18n.ts";
import {
  atPath,
  readArray,
  readBoolean,
  readEnum,
  readNullable,
  readNullableUuid,
  readNumber,
  readObject,
  readOptional,
  readString,
  readTimestamp,
  readUuid,
} from "./validate.ts";

export function parseBoundingBox(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    x: readNumber(objectValue.x, atPath(path, "x"), { min: 0 }),
    y: readNumber(objectValue.y, atPath(path, "y"), { min: 0 }),
    width: readNumber(objectValue.width, atPath(path, "width"), { min: 0 }),
    height: readNumber(objectValue.height, atPath(path, "height"), { min: 0 }),
  };
}

export function parsePolygonShape(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    type: readString(objectValue.type, atPath(path, "type")),
    points: readArray(
      objectValue.points,
      atPath(path, "points"),
      (point, pointPath) => {
        const pointValue = readObject<Record<string, unknown>>(point, pointPath);
        return {
          x: readNumber(pointValue.x, atPath(pointPath, "x"), { min: 0 }),
          y: readNumber(pointValue.y, atPath(pointPath, "y"), { min: 0 }),
        };
      },
      { minLength: 1 },
    ),
  };
}

export function parseTextStyle(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    font_family: readString(objectValue.font_family, atPath(path, "font_family")),
    font_fallbacks:
      readOptional(
        objectValue.font_fallbacks,
        (input, inputPath) =>
          readArray(input, inputPath, (item, itemPath) => readString(item, itemPath)),
        atPath(path, "font_fallbacks"),
      ) ?? [],
    font_size: readNumber(objectValue.font_size, atPath(path, "font_size"), {
      integer: true,
      min: 1,
    }),
    leading: readNumber(objectValue.leading, atPath(path, "leading"), {
      integer: true,
      min: 1,
    }),
    tracking: readNumber(objectValue.tracking, atPath(path, "tracking")),
    alignment: readString(objectValue.alignment, atPath(path, "alignment")),
    direction: readEnum(objectValue.direction, TextDirection, atPath(path, "direction")),
    rotation: readNumber(objectValue.rotation, atPath(path, "rotation")),
    fill: readString(objectValue.fill, atPath(path, "fill")),
  };
}

function parseEntityTimestamps(
  objectValue: Record<string, unknown>,
  path: Array<string | number> = [],
) {
  return {
    created_at: readTimestamp(objectValue.created_at, atPath(path, "created_at")),
    updated_at: readTimestamp(objectValue.updated_at, atPath(path, "updated_at")),
  };
}

export function parseProject(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    schema_version: readNumber(objectValue.schema_version, atPath(path, "schema_version"), {
      integer: true,
      min: SCHEMA_VERSION,
      max: SCHEMA_VERSION,
    }),
    name: readString(objectValue.name, atPath(path, "name")),
    owner_id: readUuid(objectValue.owner_id, atPath(path, "owner_id")),
    status: readEnum(objectValue.status, ProjectStatus, atPath(path, "status")),
    source_language: canonicalizeLanguageTag(
      objectValue.source_language,
      atPath(path, "source_language"),
    ),
    target_language: canonicalizeLanguageTag(
      objectValue.target_language,
      atPath(path, "target_language"),
    ),
    target_text_direction: readEnum(
      objectValue.target_text_direction,
      TextDirection,
      atPath(path, "target_text_direction"),
    ),
    default_style_preset_id: readNullableUuid(
      objectValue.default_style_preset_id,
      atPath(path, "default_style_preset_id"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parsePage(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    index: readNumber(objectValue.index, atPath(path, "index"), { integer: true, min: 1 }),
    status: readEnum(objectValue.status, PageStatus, atPath(path, "status")),
    original_asset_id: readUuid(objectValue.original_asset_id, atPath(path, "original_asset_id")),
    active_cleaned_asset_id: readNullableUuid(
      objectValue.active_cleaned_asset_id,
      atPath(path, "active_cleaned_asset_id"),
    ),
    width: readNumber(objectValue.width, atPath(path, "width"), { integer: true, min: 1 }),
    height: readNumber(objectValue.height, atPath(path, "height"), { integer: true, min: 1 }),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseAsset(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    kind: readEnum(objectValue.kind, AssetKind, atPath(path, "kind")),
    storage_key: readString(objectValue.storage_key, atPath(path, "storage_key")),
    mime_type: readString(objectValue.mime_type, atPath(path, "mime_type")),
    width: readNumber(objectValue.width, atPath(path, "width"), { integer: true, min: 1 }),
    height: readNumber(objectValue.height, atPath(path, "height"), { integer: true, min: 1 }),
    is_active: readBoolean(objectValue.is_active, atPath(path, "is_active")),
    derived_from_asset_id: readNullableUuid(
      objectValue.derived_from_asset_id,
      atPath(path, "derived_from_asset_id"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseRegion(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const origin = readEnum(objectValue.origin, RegionOrigin, atPath(path, "origin"));
  const confidence = readNullable(
    objectValue.confidence,
    (input, inputPath) => readNumber(input, inputPath, { min: 0, max: 1 }),
    atPath(path, "confidence"),
  );

  if (origin === "detected" && confidence === null) {
    throw new ValidationError("Detected regions must include confidence", path);
  }

  const boundingBox = parseBoundingBox(objectValue.bounding_box, atPath(path, "bounding_box"));
  const textArea =
    readOptional(
      objectValue.text_area,
      (input, inputPath) => parseBoundingBox(input, inputPath),
      atPath(path, "text_area"),
    ) ?? boundingBox;
  const contextArea =
    readOptional(
      objectValue.context_area,
      (input, inputPath) => parseBoundingBox(input, inputPath),
      atPath(path, "context_area"),
    ) ?? boundingBox;

  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    type: readEnum(objectValue.type, RegionType, atPath(path, "type")),
    origin,
    state: readEnum(objectValue.state, RegionState, atPath(path, "state")),
    confidence,
    cleanup_strategy:
      readNullable(
        objectValue.cleanup_strategy,
        (input, inputPath) => readEnum(input, CleanupStrategy, inputPath),
        atPath(path, "cleanup_strategy"),
      ) ?? null,
    cleanup_confidence:
      readNullable(
        objectValue.cleanup_confidence,
        (input, inputPath) => readNumber(input, inputPath, { min: 0, max: 1 }),
        atPath(path, "cleanup_confidence"),
      ) ?? null,
    bounding_box: boundingBox,
    text_area: textArea,
    context_area: contextArea,
    shape: parsePolygonShape(objectValue.shape, atPath(path, "shape")),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseMaskRevision(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    region_id: readUuid(objectValue.region_id, atPath(path, "region_id")),
    version: readNumber(objectValue.version, atPath(path, "version"), { integer: true, min: 1 }),
    is_active: readBoolean(objectValue.is_active, atPath(path, "is_active")),
    approved: readBoolean(objectValue.approved, atPath(path, "approved")),
    shape: parsePolygonShape(objectValue.shape, atPath(path, "shape")),
    created_by: readUuid(objectValue.created_by, atPath(path, "created_by")),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseDialogue(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    source: readEnum(objectValue.source, DialogueSource, atPath(path, "source")),
    source_language: canonicalizeLanguageTag(
      objectValue.source_language,
      atPath(path, "source_language"),
    ),
    content: readString(objectValue.content, atPath(path, "content"), { allowEmpty: true }),
    reading_order: readNumber(objectValue.reading_order, atPath(path, "reading_order"), {
      integer: true,
      min: 1,
    }),
    status: readEnum(objectValue.status, DialogueStatus, atPath(path, "status")),
    source_region_id: readNullableUuid(
      objectValue.source_region_id,
      atPath(path, "source_region_id"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseTranslation(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    dialogue_id: readUuid(objectValue.dialogue_id, atPath(path, "dialogue_id")),
    target_language: canonicalizeLanguageTag(
      objectValue.target_language,
      atPath(path, "target_language"),
    ),
    text_direction: readEnum(
      objectValue.text_direction,
      TextDirection,
      atPath(path, "text_direction"),
    ),
    provider: readString(objectValue.provider, atPath(path, "provider")),
    content: readString(objectValue.content, atPath(path, "content"), { allowEmpty: true }),
    status: readEnum(objectValue.status, TranslationStatus, atPath(path, "status")),
    edited_by_user: readBoolean(objectValue.edited_by_user, atPath(path, "edited_by_user")),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseAssignment(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    dialogue_id: readUuid(objectValue.dialogue_id, atPath(path, "dialogue_id")),
    region_id: readUuid(objectValue.region_id, atPath(path, "region_id")),
    origin: readEnum(objectValue.origin, AssignmentOrigin, atPath(path, "origin")),
    confidence:
      readNullable(
        objectValue.confidence,
        (input, inputPath) => readNumber(input, inputPath, { min: 0, max: 1 }),
        atPath(path, "confidence"),
      ) ?? null,
    approved: readBoolean(objectValue.approved, atPath(path, "approved")),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseTextPlacement(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    assignment_id: readUuid(objectValue.assignment_id, atPath(path, "assignment_id")),
    is_active: readBoolean(objectValue.is_active, atPath(path, "is_active")),
    text_box: parseBoundingBox(objectValue.text_box, atPath(path, "text_box")),
    style: parseTextStyle(objectValue.style, atPath(path, "style")),
    layout_metrics: readObject<Record<string, unknown>>(
      objectValue.layout_metrics,
      atPath(path, "layout_metrics"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseJob(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    page_id: readNullableUuid(objectValue.page_id, atPath(path, "page_id")),
    type: readEnum(objectValue.type, JobType, atPath(path, "type")),
    status: readEnum(objectValue.status, JobStatus, atPath(path, "status")),
    payload: readObject<Record<string, unknown>>(objectValue.payload, atPath(path, "payload")),
    result: readNullable(
      objectValue.result,
      (input, inputPath) => readObject<Record<string, unknown>>(input, inputPath),
      atPath(path, "result"),
    ),
    error_code: readNullable(
      objectValue.error_code,
      (input, inputPath) => readString(input, inputPath),
      atPath(path, "error_code"),
    ),
    error_message: readNullable(
      objectValue.error_message,
      (input, inputPath) => readString(input, inputPath),
      atPath(path, "error_message"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseExportJob(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const scopeValue = readObject<Record<string, unknown>>(objectValue.scope, atPath(path, "scope"));

  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    format: readEnum(objectValue.format, ExportFormat, atPath(path, "format")),
    scope: {
      page_ids: readArray(
        scopeValue.page_ids,
        atPath(path, "scope", "page_ids"),
        (item, itemPath) => readUuid(item, itemPath),
        { minLength: 1 },
      ),
    },
    status: readEnum(objectValue.status, JobStatus, atPath(path, "status")),
    output_asset_id: readNullableUuid(
      objectValue.output_asset_id,
      atPath(path, "output_asset_id"),
    ),
    error_message: readNullable(
      objectValue.error_message,
      (input, inputPath) => readString(input, inputPath),
      atPath(path, "error_message"),
    ),
    ...parseEntityTimestamps(objectValue, path),
  };
}
