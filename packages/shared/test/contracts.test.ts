import assert from "node:assert/strict";

import {
  parseAssignmentResponse,
  parseCreateMaskRevisionRequest,
  parseCreatePageJobRequest,
  parseDialogueResponse,
  parseListPageAssignmentsResponse,
  parseListPageDialoguesResponse,
  SUPPORTED_SOURCE_LANGUAGE_CODES,
  SUPPORTED_TARGET_LANGUAGE_CODES,
  SUPPORTED_UI_LOCALES,
  parseListPagePlacementsResponse,
  ValidationError,
  canonicalizeLanguageTag,
  inferReadingProfileForLanguage,
  inferTextDirectionForLanguage,
  normalizeProjectSourceLanguage,
  normalizeProjectTargetLanguage,
  parseCreatePageRegionRequest,
  parseCreateProjectResponse,
  parseCreateStylePresetRequest,
  parseListPageMaskRevisionsResponse,
  parseListPageJobsResponse,
  parseListPageRegionsResponse,
  parseListPageTranslationsResponse,
  parseListProjectStylePresetsResponse,
  parseMaskRevisionResponse,
  parsePlacementResponse,
  parsePageRegionResponse,
  parsePageJobResponse,
  parseProjectDetailResponse,
  normalizeUiLocale,
  parseCreateProjectRequest,
  parseDetectRegionsJobPayload,
  parseListProjectsResponse,
  parseMatchingJobPayload,
  parseMatchingJobResult,
  parseOcrJobPayload,
  parseOcrJobResult,
  parseProject,
  parseRegisterProjectPagesRequest,
  parseRegisterProjectPagesResponse,
  parseScriptImportApplyRequest,
  parseScriptImportApplyResponse,
  parseScriptImportParseRequest,
  parseScriptImportParseResponse,
  parseStylePresetResponse,
  parseTranslationJobPayload,
  parseTranslationJobResult,
  parseTranslationResponse,
  parseUpdateMaskRevisionRequest,
  parseUpdatePageRegionRequest,
  parseUpdateStylePresetRequest,
  parseUpsertAssignmentRequest,
  parseUpsertPlacementRequest,
  parseUpsertTranslationRequest,
  parseManualDialogueRequest,
} from "../src/index.ts";

const UUID = "11111111-1111-4111-8111-111111111111";
const UUID_2 = "22222222-2222-4222-8222-222222222222";
const UUID_3 = "33333333-3333-4333-8333-333333333333";
const UUID_4 = "44444444-4444-4444-8444-444444444444";

assert.equal(canonicalizeLanguageTag("pt-br"), "pt-BR");
assert.deepEqual(SUPPORTED_UI_LOCALES, ["en-US", "pt-BR"]);
assert.deepEqual(SUPPORTED_SOURCE_LANGUAGE_CODES, ["ja", "ko", "zh", "en"]);
assert.deepEqual(SUPPORTED_TARGET_LANGUAGE_CODES, ["pt", "en"]);

assert.throws(() => normalizeUiLocale("es-ES"), ValidationError);
assert.equal(normalizeProjectSourceLanguage("ko-kr"), "ko-KR");
assert.equal(normalizeProjectTargetLanguage("en-gb"), "en-GB");
assert.throws(() => normalizeProjectSourceLanguage("pt-BR"), ValidationError);
assert.throws(() => normalizeProjectTargetLanguage("ja-JP"), ValidationError);

assert.equal(inferTextDirectionForLanguage("en-US"), "ltr");
assert.equal(inferTextDirectionForLanguage("pt-BR"), "ltr");
assert.equal(inferTextDirectionForLanguage("ar"), "rtl");
assert.equal(inferReadingProfileForLanguage("ja-JP"), "manga");
assert.equal(inferReadingProfileForLanguage("ko-KR"), "manhwa");

const parsedRequest = parseCreateProjectRequest({
  name: "MangAI test",
  source_language: "ja-jp",
  target_language: "pt-br",
});

assert.deepEqual(parsedRequest, {
  name: "MangAI test",
  source_language: "ja-JP",
  reading_profile: "manga",
  target_language: "pt-BR",
  target_text_direction: "ltr",
});

const parsedManhwaRequest = parseCreateProjectRequest({
  name: "MangAI manhwa",
  source_language: "ko-KR",
  reading_profile: "manhwa",
  target_language: "en-US",
});

assert.equal(parsedManhwaRequest.reading_profile, "manhwa");

const parsedProject = parseProject({
  id: UUID,
  schema_version: 1,
  name: "Project",
  owner_id: UUID_2,
  status: "draft",
  source_language: "ja-JP",
  reading_profile: "manga",
  target_language: "en-US",
  target_text_direction: "ltr",
  default_style_preset_id: null,
  created_at: "2026-03-15T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
});

assert.equal(parsedProject.target_language, "en-US");
assert.equal(parsedProject.reading_profile, "manga");

const parsedProjectResponse = parseCreateProjectResponse({
  project: {
    id: UUID,
    schema_version: 1,
    name: "Project",
    status: "draft",
    source_language: "ja-JP",
    reading_profile: "manga",
    target_language: "pt-BR",
    target_text_direction: "ltr",
    page_count: 0,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedProjectResponse.project.page_count, 0);

const parsedProjectList = parseListProjectsResponse({
  projects: [
    {
      id: UUID,
      schema_version: 1,
      name: "Project",
      status: "draft",
      source_language: "ja-JP",
      reading_profile: "manga",
      target_language: "pt-BR",
      target_text_direction: "ltr",
      page_count: 2,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedProjectList.projects[0]?.page_count, 2);

const parsedRegisterPagesRequest = parseRegisterProjectPagesRequest({
  pages: [
    {
      file_name: "001.png",
      mime_type: "image/png",
      size_bytes: 2048,
      width: null,
      height: null,
    },
  ],
});

assert.equal(parsedRegisterPagesRequest.pages[0]?.file_name, "001.png");

const parsedRegisterPagesResponse = parseRegisterProjectPagesResponse({
  project: {
    id: UUID,
    schema_version: 1,
    name: "Project",
    status: "draft",
    source_language: "ja-JP",
    reading_profile: "manga",
    target_language: "pt-BR",
    target_text_direction: "ltr",
    page_count: 1,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
  pages: [
    {
      id: UUID_3,
      project_id: UUID,
      index: 1,
      file_name: "001.png",
      mime_type: "image/png",
      size_bytes: 2048,
      width: null,
      height: null,
      status: "uploaded",
      original_asset_path: `/api/v1/projects/${UUID}/pages/${UUID_3}/original`,
      active_cleaned_asset_path: null,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedRegisterPagesResponse.pages[0]?.status, "uploaded");
assert.equal(parsedRegisterPagesResponse.pages[0]?.original_asset_path, `/api/v1/projects/${UUID}/pages/${UUID_3}/original`);

const parsedProjectDetail = parseProjectDetailResponse({
  project: {
    id: UUID,
    schema_version: 1,
    name: "Project",
    status: "draft",
    source_language: "ja-JP",
    reading_profile: "manga",
    target_language: "pt-BR",
    target_text_direction: "ltr",
    page_count: 1,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
  pages: [
    {
      id: UUID_3,
      project_id: UUID,
      index: 1,
      file_name: "001.png",
      mime_type: "image/png",
      size_bytes: 2048,
      width: null,
      height: null,
      status: "uploaded",
      original_asset_path: `/api/v1/projects/${UUID}/pages/${UUID_3}/original`,
      active_cleaned_asset_path: null,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedProjectDetail.pages[0]?.index, 1);

const parsedAnalyzedPage = parseProjectDetailResponse({
  project: {
    id: UUID,
    schema_version: 1,
    name: "Project",
    status: "draft",
    source_language: "ja-JP",
    reading_profile: "manga",
    target_language: "pt-BR",
    target_text_direction: "ltr",
    page_count: 1,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
  pages: [
    {
      id: UUID_3,
      project_id: UUID,
      index: 1,
      file_name: "001.png",
      mime_type: "image/png",
      size_bytes: 2048,
      width: 1600,
      height: 2400,
      status: "analyzed",
      original_asset_path: `/api/v1/projects/${UUID}/pages/${UUID_3}/original`,
      active_cleaned_asset_path: `/api/v1/projects/${UUID}/assets/${UUID_2}`,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedAnalyzedPage.pages[0]?.status, "analyzed");
assert.equal(parsedAnalyzedPage.pages[0]?.active_cleaned_asset_path, `/api/v1/projects/${UUID}/assets/${UUID_2}`);

const parsedCreateRegionRequest = parseCreatePageRegionRequest({
  type: "speech_balloon",
  bounding_box: {
    x: 100,
    y: 80,
    width: 320,
    height: 180,
  },
});

assert.equal(parsedCreateRegionRequest.type, "speech_balloon");
assert.equal(parsedCreateRegionRequest.bounding_box.width, 320);

const parsedUpdateRegionRequest = parseUpdatePageRegionRequest({
  state: "approved",
});

assert.equal(parsedUpdateRegionRequest.state, "approved");
assert.throws(() => parseUpdatePageRegionRequest({}), ValidationError);

const parsedRegionsResponse = parseListPageRegionsResponse({
  regions: [
    {
      id: UUID_3,
      page_id: UUID_2,
      type: "speech_balloon",
      origin: "user_created",
      state: "draft",
      confidence: null,
      cleanup_strategy: "solid_fill",
      cleanup_confidence: 0.81,
      bounding_box: {
        x: 10,
        y: 20,
        width: 100,
        height: 60,
      },
      shape: {
        type: "polygon",
        points: [
          { x: 10, y: 20 },
          { x: 110, y: 20 },
          { x: 110, y: 80 },
          { x: 10, y: 80 },
        ],
      },
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedRegionsResponse.regions[0]?.type, "speech_balloon");
assert.equal(parsedRegionsResponse.regions[0]?.cleanup_strategy, "solid_fill");

const parsedRegionResponse = parsePageRegionResponse({
  region: {
    id: UUID_3,
    page_id: UUID_2,
    type: "speech_balloon",
    origin: "user_created",
    state: "approved",
    confidence: null,
    cleanup_strategy: "background_reconstruction",
    cleanup_confidence: 0.72,
    bounding_box: {
      x: 10,
      y: 20,
      width: 100,
      height: 60,
    },
    text_area: {
      x: 10,
      y: 20,
      width: 100,
      height: 60,
    },
    context_area: {
      x: 4,
      y: 12,
      width: 118,
      height: 82,
    },
    shape: {
      type: "polygon",
      points: [
        { x: 10, y: 20 },
        { x: 110, y: 20 },
        { x: 110, y: 80 },
        { x: 10, y: 80 },
      ],
    },
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedRegionResponse.region.state, "approved");
assert.equal(parsedRegionResponse.region.cleanup_strategy, "background_reconstruction");
assert.equal(parsedRegionResponse.region.text_area.width, 100);
assert.equal(parsedRegionResponse.region.context_area.width, 118);

const parsedRegionWithNullCleanup = parsePageRegionResponse({
  region: {
    id: UUID_4,
    page_id: UUID_2,
    type: "speech_balloon",
    origin: "detected",
    state: "draft",
    confidence: 0.84,
    cleanup_strategy: null,
    cleanup_confidence: null,
    bounding_box: {
      x: 24,
      y: 36,
      width: 80,
      height: 120,
    },
    shape: {
      type: "polygon",
      points: [
        { x: 24, y: 36 },
        { x: 104, y: 36 },
        { x: 104, y: 156 },
        { x: 24, y: 156 },
      ],
    },
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedRegionWithNullCleanup.region.cleanup_strategy, null);

const parsedCreateMaskRevision = parseCreateMaskRevisionRequest({
  region_id: UUID_3,
  shape: {
    type: "polygon",
    points: [
      { x: 10, y: 20 },
      { x: 110, y: 20 },
      { x: 110, y: 80 },
      { x: 10, y: 80 },
    ],
  },
});

assert.equal(parsedCreateMaskRevision.region_id, UUID_3);

const parsedUpdateMaskRevision = parseUpdateMaskRevisionRequest({
  approved: true,
});

assert.equal(parsedUpdateMaskRevision.approved, true);
assert.throws(() => parseUpdateMaskRevisionRequest({}), ValidationError);

const parsedMaskRevisionsResponse = parseListPageMaskRevisionsResponse({
  mask_revisions: [
    {
      id: UUID,
      region_id: UUID_3,
      version: 1,
      is_active: true,
      approved: true,
      shape: {
        type: "polygon",
        points: [
          { x: 10, y: 20 },
          { x: 110, y: 20 },
          { x: 110, y: 80 },
          { x: 10, y: 80 },
        ],
      },
      created_by: UUID_2,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedMaskRevisionsResponse.mask_revisions[0]?.approved, true);

const parsedMaskRevisionResponse = parseMaskRevisionResponse({
  mask_revision: {
    id: UUID,
    region_id: UUID_3,
    version: 2,
    is_active: true,
    approved: false,
    shape: {
      type: "polygon",
      points: [
        { x: 12, y: 22 },
        { x: 112, y: 22 },
        { x: 112, y: 82 },
        { x: 12, y: 82 },
      ],
    },
    created_by: UUID_2,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedMaskRevisionResponse.mask_revision.version, 2);

const parsedCreateJobRequest = parseCreatePageJobRequest({
  type: "detect_regions",
});

assert.equal(parsedCreateJobRequest.type, "detect_regions");

const parsedManualDialogueRequest = parseManualDialogueRequest({
  page_id: UUID_2,
  content: "Original line",
  source_language: "ja-JP",
  reading_order: 1,
});

assert.equal(parsedManualDialogueRequest.page_id, UUID_2);

const parsedDialoguesResponse = parseListPageDialoguesResponse({
  dialogues: [
    {
      id: UUID,
      page_id: UUID_2,
      source: "manual",
      source_language: "ja-JP",
      content: "Original line",
      reading_order: 1,
      status: "draft",
      source_region_id: UUID_3,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedDialoguesResponse.dialogues[0]?.content, "Original line");

const parsedDialogueResponse = parseDialogueResponse({
  dialogue: {
    id: UUID,
    page_id: UUID_2,
    source: "manual",
    source_language: "ja-JP",
    content: "Original line",
    reading_order: 1,
    status: "reviewed",
    source_region_id: UUID_3,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedDialogueResponse.dialogue.status, "reviewed");

const parsedImportedDialogue = parseDialogueResponse({
  dialogue: {
    id: UUID_4,
    page_id: UUID_2,
    source: "imported_script",
    source_language: "ja-JP",
    content: "Imported line",
    reading_order: 3,
    status: "approved",
    source_region_id: UUID_3,
    script_row_index: 7,
    page_marker: "[2]",
    import_batch_id: UUID,
    preferred_style_preset_id: UUID_2,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedImportedDialogue.dialogue.script_row_index, 7);
assert.equal(parsedImportedDialogue.dialogue.page_marker, "[2]");
assert.equal(parsedImportedDialogue.dialogue.preferred_style_preset_id, UUID_2);

const parsedTranslationRequest = parseUpsertTranslationRequest({
  dialogue_id: UUID,
  target_language: "pt-BR",
  content: "Linha traduzida",
  status: "draft",
});

assert.equal(parsedTranslationRequest.text_direction, "ltr");

const parsedTranslationsResponse = parseListPageTranslationsResponse({
  translations: [
    {
      id: UUID_2,
      dialogue_id: UUID,
      target_language: "pt-BR",
      text_direction: "ltr",
      provider: "manual",
      content: "Linha traduzida",
      status: "approved",
      edited_by_user: true,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedTranslationsResponse.translations[0]?.provider, "manual");

const parsedTranslationResponse = parseTranslationResponse({
  translation: {
    id: UUID_2,
    dialogue_id: UUID,
    target_language: "pt-BR",
    text_direction: "ltr",
    provider: "manual",
    content: "Linha traduzida",
    status: "reviewed",
    edited_by_user: true,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedTranslationResponse.translation.status, "reviewed");

const parsedAssignmentRequest = parseUpsertAssignmentRequest({
  dialogue_id: UUID,
  region_id: UUID_3,
  origin: "manual",
  approved: true,
});

assert.equal(parsedAssignmentRequest.approved, true);

const parsedAssignmentsResponse = parseListPageAssignmentsResponse({
  assignments: [
    {
      id: UUID_2,
      page_id: UUID_3,
      dialogue_id: UUID,
      region_id: UUID_3,
      origin: "manual",
      confidence: null,
      approved: true,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedAssignmentsResponse.assignments[0]?.origin, "manual");

const parsedAssignmentResponse = parseAssignmentResponse({
  assignment: {
    id: UUID_2,
    page_id: UUID_3,
    dialogue_id: UUID,
    region_id: UUID_3,
    origin: "manual",
    confidence: null,
    approved: false,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedAssignmentResponse.assignment.approved, false);

const parsedPlacementRequest = parseUpsertPlacementRequest({
  assignment_id: UUID_2,
  text_box: {
    x: 12,
    y: 20,
    width: 130,
    height: 90,
  },
  style: {
    font_family: "Komika",
    font_fallbacks: ["Arial"],
    font_size: 24,
    leading: 28,
    tracking: 0,
    alignment: "center",
    direction: "ltr",
    rotation: 0,
    fill: "#000000",
  },
});

assert.equal(parsedPlacementRequest.style.font_size, 24);
assert.equal(parsedPlacementRequest.style.min_font_size, 24);
assert.equal(parsedPlacementRequest.style.max_font_size, 24);
assert.equal(parsedPlacementRequest.style.padding_x, 0);
assert.equal(parsedPlacementRequest.style.line_break_mode, "auto");

const parsedPlacementsResponse = parseListPagePlacementsResponse({
  placements: [
    {
      id: UUID_3,
      assignment_id: UUID_2,
      is_active: true,
      text_box: {
        x: 12,
        y: 20,
        width: 130,
        height: 90,
      },
      style: {
        font_family: "Komika",
        font_fallbacks: ["Arial"],
        font_size: 24,
        leading: 28,
        tracking: 0,
        alignment: "center",
        direction: "ltr",
        rotation: 0,
        fill: "#000000",
      },
      layout_metrics: {
        mode: "manual",
      },
      locked_by_user: true,
      manual_line_breaks: ["Line 1", "Line 2"],
      layout_status: "adjusted",
      overflow_detected: false,
      fit_score: 0.93,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedPlacementsResponse.placements[0]?.is_active, true);
assert.equal(parsedPlacementsResponse.placements[0]?.locked_by_user, true);
assert.equal(parsedPlacementsResponse.placements[0]?.manual_line_breaks[1], "Line 2");
assert.equal(parsedPlacementsResponse.placements[0]?.layout_status, "adjusted");

const parsedPlacementResponse = parsePlacementResponse({
  placement: {
    id: UUID_3,
    assignment_id: UUID_2,
    is_active: true,
    text_box: {
      x: 12,
      y: 20,
      width: 130,
      height: 90,
    },
    style: {
      font_family: "Komika",
      font_fallbacks: ["Arial"],
      font_size: 24,
      leading: 28,
      tracking: 0,
      alignment: "center",
      direction: "ltr",
      rotation: 0,
      fill: "#000000",
    },
    layout_metrics: {
      mode: "manual",
    },
    locked_by_user: false,
    manual_line_breaks: [],
    layout_status: "generated",
    overflow_detected: true,
    fit_score: 0.41,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedPlacementResponse.placement.style.font_family, "Komika");
assert.equal(parsedPlacementResponse.placement.layout_status, "generated");
assert.equal(parsedPlacementResponse.placement.overflow_detected, true);
assert.equal(parsedPlacementResponse.placement.fit_score, 0.41);

const parsedCreateStylePreset = parseCreateStylePresetRequest({
  name: "Normal",
  category: "normal",
  is_default: true,
  style: {
    font_family: "Komika",
    font_fallbacks: ["Arial"],
    font_size: 26,
    min_font_size: 18,
    max_font_size: 30,
    leading: 30,
    tracking: 0,
    alignment: "center",
    direction: "ltr",
    rotation: 0,
    fill: "#000000",
    padding_x: 8,
    padding_y: 10,
    line_break_mode: "balanced",
    stroke_fill: "#ffffff",
    stroke_width: 2,
    uppercase: false,
    auto_fit: true,
    vertical_bias: -0.1,
    allow_overflow: false,
  },
});

assert.equal(parsedCreateStylePreset.category, "normal");
assert.equal(parsedCreateStylePreset.style.padding_x, 8);
assert.equal(parsedCreateStylePreset.style.stroke_fill, "#ffffff");

const parsedUpdateStylePreset = parseUpdateStylePresetRequest({
  name: "Narration",
  category: "narration_box",
});

assert.equal(parsedUpdateStylePreset.name, "Narration");
assert.equal(parsedUpdateStylePreset.category, "narration_box");
assert.throws(() => parseUpdateStylePresetRequest({}), ValidationError);

const parsedStylePresetList = parseListProjectStylePresetsResponse({
  presets: [
    {
      id: UUID,
      project_id: UUID_2,
      name: "Normal",
      category: "normal",
      is_default: true,
      source_preset_id: null,
      style: {
        font_family: "Komika",
        font_fallbacks: ["Arial"],
        font_size: 26,
        min_font_size: 18,
        max_font_size: 30,
        leading: 30,
        tracking: 0,
        alignment: "center",
        direction: "ltr",
        rotation: 0,
        fill: "#000000",
        padding_x: 8,
        padding_y: 10,
        line_break_mode: "balanced",
        stroke_fill: "#ffffff",
        stroke_width: 2,
        uppercase: false,
        auto_fit: true,
        vertical_bias: 0,
        allow_overflow: false,
      },
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedStylePresetList.presets[0]?.style.max_font_size, 30);

const parsedStylePreset = parseStylePresetResponse({
  preset: {
    id: UUID_3,
    project_id: UUID_2,
    name: "Thoughts",
    category: "thoughts",
    is_default: false,
    source_preset_id: UUID,
    style: {
      font_family: "WildWords",
      font_fallbacks: ["Arial"],
      font_size: 24,
      leading: 28,
      tracking: 5,
      alignment: "center",
      direction: "ltr",
      rotation: 0,
      fill: "#111111",
    },
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedStylePreset.preset.source_preset_id, UUID);
assert.equal(parsedStylePreset.preset.style.min_font_size, 24);

assert.throws(
  () =>
    parseCreateStylePresetRequest({
      name: "Broken",
      category: "normal",
      style: {
        font_family: "Komika",
        font_fallbacks: [],
        font_size: 24,
        min_font_size: 25,
        max_font_size: 20,
        leading: 28,
        tracking: 0,
        alignment: "center",
        direction: "ltr",
        rotation: 0,
        fill: "#000000",
      },
    }),
  ValidationError,
);

const parsedScriptParseRequest = parseScriptImportParseRequest({
  mode: "translations",
  content: "[1]\nLinha 1\nLinha 2\n\n[2]\nLinha 3",
  current_page_number: 1,
});

assert.equal(parsedScriptParseRequest.mode, "translations");
assert.equal(parsedScriptParseRequest.current_page_number, 1);

const parsedScriptParseResponse = parseScriptImportParseResponse({
  mode: "translations",
  pages: [
    {
      page_number: 1,
      marker: "[1]",
      lines: [
        { row_index: 1, content: "Linha 1" },
        { row_index: 2, content: "Linha 2" },
      ],
    },
    {
      page_number: 2,
      marker: "[2]",
      lines: [{ row_index: 3, content: "Linha 3" }],
    },
  ],
  warnings: ["Page 3 not found"],
  total_line_count: 3,
});

assert.equal(parsedScriptParseResponse.pages[0]?.lines[1]?.content, "Linha 2");
assert.equal(parsedScriptParseResponse.warnings[0], "Page 3 not found");

const parsedScriptApplyRequest = parseScriptImportApplyRequest({
  mode: "source_dialogues",
  pages: [
    {
      page_number: 1,
      marker: "[1]",
      lines: [{ row_index: 1, content: "Original 1" }],
    },
  ],
  replace_existing: true,
});

assert.equal(parsedScriptApplyRequest.replace_existing, true);

const parsedScriptApplyResponse = parseScriptImportApplyResponse({
  mode: "source_dialogues",
  pages_touched: 2,
  dialogues_upserted: 10,
  translations_upserted: 0,
});

assert.equal(parsedScriptApplyResponse.dialogues_upserted, 10);
assert.equal(parsedScriptApplyResponse.translations_upserted, 0);

const parsedJobsResponse = parseListPageJobsResponse({
  jobs: [
    {
      id: UUID,
      project_id: UUID_2,
      page_id: UUID_3,
      type: "detect_regions",
      status: "queued",
      payload: {
        job_id: UUID,
        page_id: UUID_3,
        asset_id: UUID_2,
      },
      result: null,
      error_code: null,
      error_message: null,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    },
  ],
});

assert.equal(parsedJobsResponse.jobs[0]?.type, "detect_regions");

const parsedJobResponse = parsePageJobResponse({
  job: {
    id: UUID,
    project_id: UUID_2,
    page_id: UUID_3,
    type: "detect_regions",
    status: "succeeded",
    payload: {
      job_id: UUID,
      page_id: UUID_3,
      asset_id: UUID_2,
    },
    result: {
      page_id: UUID_3,
      regions_created: 3,
      overlay_asset_id: UUID,
    },
    error_code: null,
    error_message: null,
    created_at: "2026-03-15T00:00:00Z",
    updated_at: "2026-03-15T00:00:00Z",
  },
});

assert.equal(parsedJobResponse.job.status, "succeeded");

const detectPayload = parseDetectRegionsJobPayload({
  job_id: UUID,
  page_id: UUID_2,
  asset_id: UUID_3,
});

assert.equal(detectPayload.page_id, UUID_2);

const ocrPayload = parseOcrJobPayload({
  job_id: UUID,
  page_id: UUID_2,
  asset_id: UUID_3,
  region_ids: [UUID],
  source_language: "ja-JP",
});

assert.equal(ocrPayload.region_ids[0], UUID);

const ocrResult = parseOcrJobResult({
  page_id: UUID_2,
  dialogue_ids: [UUID],
  preview_asset_id: UUID_3,
});

assert.equal(ocrResult.preview_asset_id, UUID_3);

const translationPayload = parseTranslationJobPayload({
  job_id: UUID,
  project_id: UUID_2,
  dialogue_ids: [UUID_3],
  source_language: "ja-JP",
  target_language: "pt-BR",
});

assert.equal(translationPayload.target_language, "pt-BR");

const translationResult = parseTranslationJobResult({
  project_id: UUID_2,
  translation_ids: [UUID_3],
});

assert.equal(translationResult.translation_ids[0], UUID_3);

const matchingPayload = parseMatchingJobPayload({
  job_id: UUID,
  page_id: UUID_2,
  dialogue_ids: [UUID_3],
  region_ids: [UUID],
});

assert.equal(matchingPayload.region_ids[0], UUID);

const matchingResult = parseMatchingJobResult({
  page_id: UUID_2,
  assignment_ids: [UUID],
  placement_ids: [UUID_3],
});

assert.equal(matchingResult.placement_ids[0], UUID_3);

console.log("SHARED_CONTRACT_TESTS_OK");
