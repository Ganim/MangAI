import {
  AssetKind,
  AssignmentOrigin,
  CleanupStrategy,
  DialogueSource,
  DialogueStatus,
  ExportFormat,
  JobStatus,
  JobType,
  LineBreakMode,
  PlacementLayoutStatus,
  PageStatus,
  ProjectStatus,
  ReadingProfile,
  RegionOrigin,
  RegionState,
  RegionType,
  SCHEMA_VERSION,
  StylePresetCategory,
  TextDirection,
  TranslationStatus,
} from "./enums.ts";
import { ValidationError } from "./errors.ts";
import { canonicalizeLanguageTag, inferReadingProfileForLanguage } from "./i18n.ts";
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
  const fontSize = readNumber(objectValue.font_size, atPath(path, "font_size"), {
    integer: true,
    min: 1,
  });
  const parsedStyle = {
    font_family: readString(objectValue.font_family, atPath(path, "font_family")),
    font_fallbacks:
      readOptional(
        objectValue.font_fallbacks,
        (input, inputPath) =>
          readArray(input, inputPath, (item, itemPath) => readString(item, itemPath)),
        atPath(path, "font_fallbacks"),
      ) ?? [],
    font_size: fontSize,
    min_font_size:
      readOptional(
        objectValue.min_font_size,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "min_font_size"),
      ) ?? fontSize,
    max_font_size:
      readOptional(
        objectValue.max_font_size,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "max_font_size"),
      ) ?? fontSize,
    leading: readNumber(objectValue.leading, atPath(path, "leading"), {
      integer: true,
      min: 1,
    }),
    tracking: readNumber(objectValue.tracking, atPath(path, "tracking")),
    alignment: readString(objectValue.alignment, atPath(path, "alignment")),
    direction: readEnum(objectValue.direction, TextDirection, atPath(path, "direction")),
    rotation: readNumber(objectValue.rotation, atPath(path, "rotation")),
    fill: readString(objectValue.fill, atPath(path, "fill")),
    padding_x:
      readOptional(
        objectValue.padding_x,
        (input, inputPath) => readNumber(input, inputPath, { min: 0 }),
        atPath(path, "padding_x"),
      ) ?? 0,
    padding_y:
      readOptional(
        objectValue.padding_y,
        (input, inputPath) => readNumber(input, inputPath, { min: 0 }),
        atPath(path, "padding_y"),
      ) ?? 0,
    line_break_mode:
      readOptional(
        objectValue.line_break_mode,
        (input, inputPath) => readEnum(input, LineBreakMode, inputPath),
        atPath(path, "line_break_mode"),
      ) ?? "auto",
    stroke_fill:
      readNullable(
        objectValue.stroke_fill,
        (input, inputPath) => readString(input, inputPath),
        atPath(path, "stroke_fill"),
      ) ?? null,
    stroke_width:
      readOptional(
        objectValue.stroke_width,
        (input, inputPath) => readNumber(input, inputPath, { min: 0 }),
        atPath(path, "stroke_width"),
      ) ?? 0,
    uppercase:
      readOptional(
        objectValue.uppercase,
        (input, inputPath) => readBoolean(input, inputPath),
        atPath(path, "uppercase"),
      ) ?? false,
    auto_fit:
      readOptional(
        objectValue.auto_fit,
        (input, inputPath) => readBoolean(input, inputPath),
        atPath(path, "auto_fit"),
      ) ?? true,
    vertical_bias:
      readOptional(
        objectValue.vertical_bias,
        (input, inputPath) => readNumber(input, inputPath),
        atPath(path, "vertical_bias"),
      ) ?? 0,
    allow_overflow:
      readOptional(
        objectValue.allow_overflow,
        (input, inputPath) => readBoolean(input, inputPath),
        atPath(path, "allow_overflow"),
      ) ?? false,
  };

  if (parsedStyle.min_font_size > parsedStyle.max_font_size) {
    throw new ValidationError("min_font_size cannot exceed max_font_size", path);
  }

  return parsedStyle;
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
    reading_profile:
      readOptional(
        objectValue.reading_profile,
        (input, inputPath) => readEnum(input, ReadingProfile, inputPath),
        atPath(path, "reading_profile"),
      ) ?? inferReadingProfileForLanguage(objectValue.source_language, atPath(path, "source_language")),
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
  const panelArea =
    readOptional(
      objectValue.panel_area,
      (input, inputPath) => parseBoundingBox(input, inputPath),
      atPath(path, "panel_area"),
    ) ?? contextArea;
  const balloonGroupArea =
    readOptional(
      objectValue.balloon_group_area,
      (input, inputPath) => parseBoundingBox(input, inputPath),
      atPath(path, "balloon_group_area"),
    ) ?? contextArea;

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
    panel_area: panelArea,
    balloon_group_id:
      readNullable(
        objectValue.balloon_group_id,
        (input, inputPath) => readUuid(input, inputPath),
        atPath(path, "balloon_group_id"),
      ) ?? null,
    balloon_group_area: balloonGroupArea,
    panel_order:
      readNullable(
        objectValue.panel_order,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "panel_order"),
      ) ?? null,
    balloon_group_order:
      readNullable(
        objectValue.balloon_group_order,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "balloon_group_order"),
      ) ?? null,
    order_in_balloon_group:
      readNullable(
        objectValue.order_in_balloon_group,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "order_in_balloon_group"),
      ) ?? null,
    order_in_panel:
      readNullable(
        objectValue.order_in_panel,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "order_in_panel"),
      ) ?? null,
    global_reading_order:
      readNullable(
        objectValue.global_reading_order,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "global_reading_order"),
      ) ?? null,
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
    script_row_index:
      readNullable(
        objectValue.script_row_index,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "script_row_index"),
      ) ?? null,
    page_marker:
      readNullable(
        objectValue.page_marker,
        (input, inputPath) => readString(input, inputPath),
        atPath(path, "page_marker"),
      ) ?? null,
    import_batch_id: readNullableUuid(
      objectValue.import_batch_id,
      atPath(path, "import_batch_id"),
    ),
    preferred_style_preset_id: readNullableUuid(
      objectValue.preferred_style_preset_id,
      atPath(path, "preferred_style_preset_id"),
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
    locked_by_user:
      readOptional(
        objectValue.locked_by_user,
        (input, inputPath) => readBoolean(input, inputPath),
        atPath(path, "locked_by_user"),
      ) ?? false,
    manual_line_breaks:
      readOptional(
        objectValue.manual_line_breaks,
        (input, inputPath) =>
          readArray(input, inputPath, (item, itemPath) => readString(item, itemPath)),
        atPath(path, "manual_line_breaks"),
      ) ?? [],
    layout_status:
      readOptional(
        objectValue.layout_status,
        (input, inputPath) => readEnum(input, PlacementLayoutStatus, inputPath),
        atPath(path, "layout_status"),
      ) ?? "draft",
    overflow_detected:
      readOptional(
        objectValue.overflow_detected,
        (input, inputPath) => readBoolean(input, inputPath),
        atPath(path, "overflow_detected"),
      ) ?? false,
    fit_score:
      readNullable(
        objectValue.fit_score,
        (input, inputPath) => readNumber(input, inputPath, { min: 0, max: 1 }),
        atPath(path, "fit_score"),
      ) ?? null,
    ...parseEntityTimestamps(objectValue, path),
  };
}

export function parseStylePreset(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    name: readString(objectValue.name, atPath(path, "name")),
    category: readEnum(objectValue.category, StylePresetCategory, atPath(path, "category")),
    is_default: readBoolean(objectValue.is_default, atPath(path, "is_default")),
    source_preset_id: readNullableUuid(
      objectValue.source_preset_id,
      atPath(path, "source_preset_id"),
    ),
    style: parseTextStyle(objectValue.style, atPath(path, "style")),
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
