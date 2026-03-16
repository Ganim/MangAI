import {
  AssignmentOrigin,
  ExportFormat,
  JobType,
  PageStatus,
  RegionState,
  RegionType,
  TextDirection,
  TranslationStatus,
} from "./enums.ts";
import { ValidationError } from "./errors.ts";
import {
  canonicalizeLanguageTag,
  inferTextDirectionForLanguage,
  normalizeProjectSourceLanguage,
  normalizeProjectTargetLanguage,
  normalizeUiLocale,
} from "./i18n.ts";
import {
  atPath,
  readArray,
  readBoolean,
  readEnum,
  readNumber,
  readObject,
  readOptional,
  readString,
  readTimestamp,
  readNullable,
  readUuid,
} from "./validate.ts";
import {
  parseAssignment,
  parseBoundingBox,
  parseDialogue,
  parseJob,
  parseMaskRevision,
  parsePolygonShape,
  parseRegion,
  parseTextStyle,
  parseTextPlacement,
  parseTranslation,
} from "./entities.ts";

export function parseCreateProjectRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const targetLanguage = normalizeProjectTargetLanguage(
    objectValue.target_language,
    atPath(path, "target_language"),
  );

  return {
    name: readString(objectValue.name, atPath(path, "name")),
    source_language: normalizeProjectSourceLanguage(
      objectValue.source_language,
      atPath(path, "source_language"),
    ),
    target_language: targetLanguage,
    target_text_direction:
      readOptional(
        objectValue.target_text_direction,
        (input, inputPath) => readEnum(input, TextDirection, inputPath),
        atPath(path, "target_text_direction"),
      ) ?? inferTextDirectionForLanguage(targetLanguage),
  };
}

export function parseProjectSummary(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    schema_version: readNumber(objectValue.schema_version, atPath(path, "schema_version"), {
      integer: true,
      min: 1,
    }),
    name: readString(objectValue.name, atPath(path, "name")),
    status: readEnum(objectValue.status, ["draft", "active", "archived"] as const, atPath(path, "status")),
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
    page_count: readNumber(objectValue.page_count, atPath(path, "page_count"), {
      integer: true,
      min: 0,
    }),
    created_at: readTimestamp(objectValue.created_at, atPath(path, "created_at")),
    updated_at: readTimestamp(objectValue.updated_at, atPath(path, "updated_at")),
  };
}

export function parseCreateProjectResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    project: parseProjectSummary(objectValue.project, atPath(path, "project")),
  };
}

export function parseListProjectsResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    projects: readArray(
      objectValue.projects,
      atPath(path, "projects"),
      (item, itemPath) => parseProjectSummary(item, itemPath),
    ),
  };
}

export function parseRegisterProjectPagesRequest(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    pages: readArray(
      objectValue.pages,
      atPath(path, "pages"),
      (item, itemPath) => {
        const pageValue = readObject<Record<string, unknown>>(item, itemPath);
        return {
          file_name: readString(pageValue.file_name, atPath(itemPath, "file_name")),
          mime_type: readString(pageValue.mime_type, atPath(itemPath, "mime_type")),
          size_bytes: readNumber(pageValue.size_bytes, atPath(itemPath, "size_bytes"), {
            integer: true,
            min: 1,
          }),
          width:
            readNullable(
              pageValue.width,
              (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
              atPath(itemPath, "width"),
            ) ?? null,
          height:
            readNullable(
              pageValue.height,
              (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
              atPath(itemPath, "height"),
            ) ?? null,
        };
      },
      { minLength: 1 },
    ),
  };
}

export function parseRegisteredProjectPage(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    id: readUuid(objectValue.id, atPath(path, "id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    index: readNumber(objectValue.index, atPath(path, "index"), {
      integer: true,
      min: 1,
    }),
    file_name: readString(objectValue.file_name, atPath(path, "file_name")),
    mime_type: readString(objectValue.mime_type, atPath(path, "mime_type")),
    size_bytes: readNumber(objectValue.size_bytes, atPath(path, "size_bytes"), {
      integer: true,
      min: 1,
    }),
    width:
      readNullable(
        objectValue.width,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "width"),
      ) ?? null,
    height:
      readNullable(
        objectValue.height,
        (input, inputPath) => readNumber(input, inputPath, { integer: true, min: 1 }),
        atPath(path, "height"),
      ) ?? null,
    status: readEnum(objectValue.status, PageStatus, atPath(path, "status")),
    original_asset_path: readString(
      objectValue.original_asset_path,
      atPath(path, "original_asset_path"),
    ),
    active_cleaned_asset_path:
      readNullable(
        objectValue.active_cleaned_asset_path,
        (input, inputPath) => readString(input, inputPath),
        atPath(path, "active_cleaned_asset_path"),
      ) ?? null,
    created_at: readTimestamp(objectValue.created_at, atPath(path, "created_at")),
    updated_at: readTimestamp(objectValue.updated_at, atPath(path, "updated_at")),
  };
}

export function parseProjectDetailResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    project: parseProjectSummary(objectValue.project, atPath(path, "project")),
    pages: readArray(
      objectValue.pages,
      atPath(path, "pages"),
      (item, itemPath) => parseRegisteredProjectPage(item, itemPath),
    ),
  };
}

export function parseCreatePageRegionRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    type: readEnum(objectValue.type, RegionType, atPath(path, "type")),
    bounding_box: parseBoundingBox(objectValue.bounding_box, atPath(path, "bounding_box")),
  };
}

export function parseUpdatePageRegionRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const parsedValue = {
    type: readOptional(
      objectValue.type,
      (input, inputPath) => readEnum(input, RegionType, inputPath),
      atPath(path, "type"),
    ),
    state: readOptional(
      objectValue.state,
      (input, inputPath) => readEnum(input, RegionState, inputPath),
      atPath(path, "state"),
    ),
    bounding_box: readOptional(
      objectValue.bounding_box,
      (input, inputPath) => parseBoundingBox(input, inputPath),
      atPath(path, "bounding_box"),
    ),
  };

  if (
    parsedValue.type === undefined &&
    parsedValue.state === undefined &&
    parsedValue.bounding_box === undefined
  ) {
    throw new ValidationError("At least one region field must be updated", path);
  }

  return parsedValue;
}

export function parseListPageRegionsResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    regions: readArray(
      objectValue.regions,
      atPath(path, "regions"),
      (item, itemPath) => parseRegion(item, itemPath),
    ),
  };
}

export function parsePageRegionResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    region: parseRegion(objectValue.region, atPath(path, "region")),
  };
}

export function parseCreateMaskRevisionRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    region_id: readUuid(objectValue.region_id, atPath(path, "region_id")),
    shape: parsePolygonShape(objectValue.shape, atPath(path, "shape")),
  };
}

export function parseUpdateMaskRevisionRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const parsedValue = {
    approved: readOptional(
      objectValue.approved,
      (input, inputPath) => readBoolean(input, inputPath),
      atPath(path, "approved"),
    ),
    is_active: readOptional(
      objectValue.is_active,
      (input, inputPath) => readBoolean(input, inputPath),
      atPath(path, "is_active"),
    ),
    shape: readOptional(
      objectValue.shape,
      (input, inputPath) => parsePolygonShape(input, inputPath),
      atPath(path, "shape"),
    ),
  };

  if (
    parsedValue.approved === undefined &&
    parsedValue.is_active === undefined &&
    parsedValue.shape === undefined
  ) {
    throw new ValidationError("At least one mask revision field must be updated", path);
  }

  return parsedValue;
}

export function parseListPageMaskRevisionsResponse(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    mask_revisions: readArray(
      objectValue.mask_revisions,
      atPath(path, "mask_revisions"),
      (item, itemPath) => parseMaskRevision(item, itemPath),
    ),
  };
}

export function parseMaskRevisionResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    mask_revision: parseMaskRevision(objectValue.mask_revision, atPath(path, "mask_revision")),
  };
}

export function parseCreatePageJobRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    type: readEnum(objectValue.type, JobType, atPath(path, "type")),
  };
}

export function parseListPageJobsResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    jobs: readArray(
      objectValue.jobs,
      atPath(path, "jobs"),
      (item, itemPath) => parseJob(item, itemPath),
    ),
  };
}

export function parsePageJobResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job: parseJob(objectValue.job, atPath(path, "job")),
  };
}

export function parseRegisterProjectPagesResponse(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    project: parseProjectSummary(objectValue.project, atPath(path, "project")),
    pages: readArray(
      objectValue.pages,
      atPath(path, "pages"),
      (item, itemPath) => parseRegisteredProjectPage(item, itemPath),
    ),
  };
}

export function parseManualDialogueRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    content: readString(objectValue.content, atPath(path, "content"), { allowEmpty: true }),
    source_language: normalizeProjectSourceLanguage(
      objectValue.source_language,
      atPath(path, "source_language"),
    ),
    reading_order: readNumber(objectValue.reading_order, atPath(path, "reading_order"), {
      integer: true,
      min: 1,
    }),
  };
}

export function parseListPageDialoguesResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    dialogues: readArray(
      objectValue.dialogues,
      atPath(path, "dialogues"),
      (item, itemPath) => parseDialogue(item, itemPath),
    ),
  };
}

export function parseDialogueResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    dialogue: parseDialogue(objectValue.dialogue, atPath(path, "dialogue")),
  };
}

export function parseUpsertTranslationRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  const targetLanguage = normalizeProjectTargetLanguage(
    objectValue.target_language,
    atPath(path, "target_language"),
  );

  return {
    dialogue_id: readUuid(objectValue.dialogue_id, atPath(path, "dialogue_id")),
    target_language: targetLanguage,
    text_direction:
      readOptional(
        objectValue.text_direction,
        (input, inputPath) => readEnum(input, TextDirection, inputPath),
        atPath(path, "text_direction"),
      ) ?? inferTextDirectionForLanguage(targetLanguage),
    content: readString(objectValue.content, atPath(path, "content"), { allowEmpty: true }),
    status: readEnum(objectValue.status, TranslationStatus, atPath(path, "status")),
  };
}

export function parseListPageTranslationsResponse(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    translations: readArray(
      objectValue.translations,
      atPath(path, "translations"),
      (item, itemPath) => parseTranslation(item, itemPath),
    ),
  };
}

export function parseTranslationResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    translation: parseTranslation(objectValue.translation, atPath(path, "translation")),
  };
}

export function parseUpsertAssignmentRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    dialogue_id: readUuid(objectValue.dialogue_id, atPath(path, "dialogue_id")),
    region_id: readUuid(objectValue.region_id, atPath(path, "region_id")),
    origin: readEnum(objectValue.origin, AssignmentOrigin, atPath(path, "origin")),
    approved: readBoolean(objectValue.approved, atPath(path, "approved")),
  };
}

export function parseListPageAssignmentsResponse(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    assignments: readArray(
      objectValue.assignments,
      atPath(path, "assignments"),
      (item, itemPath) => parseAssignment(item, itemPath),
    ),
  };
}

export function parseAssignmentResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    assignment: parseAssignment(objectValue.assignment, atPath(path, "assignment")),
  };
}

export function parseUpsertPlacementRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    assignment_id: readUuid(objectValue.assignment_id, atPath(path, "assignment_id")),
    text_box: parseBoundingBox(objectValue.text_box, atPath(path, "text_box")),
    style: parseTextStyle(objectValue.style, atPath(path, "style")),
  };
}

export function parseListPagePlacementsResponse(
  value: unknown,
  path: Array<string | number> = [],
) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    placements: readArray(
      objectValue.placements,
      atPath(path, "placements"),
      (item, itemPath) => parseTextPlacement(item, itemPath),
    ),
  };
}

export function parsePlacementResponse(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    placement: parseTextPlacement(objectValue.placement, atPath(path, "placement")),
  };
}

export function parseUiLocaleRequest(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    locale: normalizeUiLocale(objectValue.locale, atPath(path, "locale")),
  };
}

export function parseDetectRegionsJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    asset_id: readUuid(objectValue.asset_id, atPath(path, "asset_id")),
  };
}

export function parseDetectRegionsJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    regions_created: readNumber(objectValue.regions_created, atPath(path, "regions_created"), {
      integer: true,
      min: 0,
    }),
    overlay_asset_id: readUuid(objectValue.overlay_asset_id, atPath(path, "overlay_asset_id")),
  };
}

export function parseCleanupJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    source_asset_id: readUuid(objectValue.source_asset_id, atPath(path, "source_asset_id")),
    region_ids: readArray(
      objectValue.region_ids,
      atPath(path, "region_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    mask_revision_ids: readArray(
      objectValue.mask_revision_ids,
      atPath(path, "mask_revision_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseCleanupJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    cleaned_asset_id: readUuid(objectValue.cleaned_asset_id, atPath(path, "cleaned_asset_id")),
    variant_asset_ids: readArray(
      objectValue.variant_asset_ids ?? [],
      atPath(path, "variant_asset_ids"),
      (item, itemPath) => readUuid(item, itemPath),
    ),
  };
}

export function parseOcrJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    asset_id: readUuid(objectValue.asset_id, atPath(path, "asset_id")),
    region_ids: readArray(
      objectValue.region_ids,
      atPath(path, "region_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseOcrJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    dialogue_ids: readArray(
      objectValue.dialogue_ids,
      atPath(path, "dialogue_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    preview_asset_id: readUuid(
      objectValue.preview_asset_id,
      atPath(path, "preview_asset_id"),
    ),
  };
}

export function parseTranslationJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    dialogue_ids: readArray(
      objectValue.dialogue_ids,
      atPath(path, "dialogue_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    source_language: normalizeProjectSourceLanguage(
      objectValue.source_language,
      atPath(path, "source_language"),
    ),
    target_language: normalizeProjectTargetLanguage(
      objectValue.target_language,
      atPath(path, "target_language"),
    ),
  };
}

export function parseTranslationJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    translation_ids: readArray(
      objectValue.translation_ids,
      atPath(path, "translation_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseMatchingJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    dialogue_ids: readArray(
      objectValue.dialogue_ids,
      atPath(path, "dialogue_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    region_ids: readArray(
      objectValue.region_ids,
      atPath(path, "region_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseMatchingJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    assignment_ids: readArray(
      objectValue.assignment_ids,
      atPath(path, "assignment_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    placement_ids: readArray(
      objectValue.placement_ids,
      atPath(path, "placement_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseTypesettingJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    assignment_ids: readArray(
      objectValue.assignment_ids,
      atPath(path, "assignment_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
    style_preset_id:
      readOptional(
        objectValue.style_preset_id,
        (input, inputPath) => readUuid(input, inputPath),
        atPath(path, "style_preset_id"),
      ) ?? null,
  };
}

export function parseTypesettingJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    page_id: readUuid(objectValue.page_id, atPath(path, "page_id")),
    text_placement_ids: readArray(
      objectValue.text_placement_ids,
      atPath(path, "text_placement_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseExportJobPayload(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    job_id: readUuid(objectValue.job_id, atPath(path, "job_id")),
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    format: readEnum(objectValue.format, ExportFormat, atPath(path, "format")),
    page_ids: readArray(
      objectValue.page_ids,
      atPath(path, "page_ids"),
      (item, itemPath) => readUuid(item, itemPath),
      { minLength: 1 },
    ),
  };
}

export function parseExportJobResult(value: unknown, path: Array<string | number> = []) {
  const objectValue = readObject<Record<string, unknown>>(value, path);
  return {
    project_id: readUuid(objectValue.project_id, atPath(path, "project_id")),
    format: readEnum(objectValue.format, ExportFormat, atPath(path, "format")),
    output_asset_id: readUuid(objectValue.output_asset_id, atPath(path, "output_asset_id")),
  };
}
