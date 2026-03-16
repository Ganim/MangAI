import assert from "node:assert/strict";

import {
  parseCreateMaskRevisionRequest,
  parseCreatePageJobRequest,
  SUPPORTED_SOURCE_LANGUAGE_CODES,
  SUPPORTED_TARGET_LANGUAGE_CODES,
  SUPPORTED_UI_LOCALES,
  ValidationError,
  canonicalizeLanguageTag,
  inferTextDirectionForLanguage,
  normalizeProjectSourceLanguage,
  normalizeProjectTargetLanguage,
  parseCreatePageRegionRequest,
  parseCreateProjectResponse,
  parseListPageMaskRevisionsResponse,
  parseListPageJobsResponse,
  parseListPageRegionsResponse,
  parseMaskRevisionResponse,
  parsePageRegionResponse,
  parsePageJobResponse,
  parseProjectDetailResponse,
  normalizeUiLocale,
  parseCreateProjectRequest,
  parseDetectRegionsJobPayload,
  parseListProjectsResponse,
  parseProject,
  parseRegisterProjectPagesRequest,
  parseRegisterProjectPagesResponse,
  parseUpdateMaskRevisionRequest,
  parseUpdatePageRegionRequest,
} from "../src/index.ts";

const UUID = "11111111-1111-4111-8111-111111111111";
const UUID_2 = "22222222-2222-4222-8222-222222222222";
const UUID_3 = "33333333-3333-4333-8333-333333333333";

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

const parsedRequest = parseCreateProjectRequest({
  name: "MangAI test",
  source_language: "ja-jp",
  target_language: "pt-br",
});

assert.deepEqual(parsedRequest, {
  name: "MangAI test",
  source_language: "ja-JP",
  target_language: "pt-BR",
  target_text_direction: "ltr",
});

const parsedProject = parseProject({
  id: UUID,
  schema_version: 1,
  name: "Project",
  owner_id: UUID_2,
  status: "draft",
  source_language: "ja-JP",
  target_language: "en-US",
  target_text_direction: "ltr",
  default_style_preset_id: null,
  created_at: "2026-03-15T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
});

assert.equal(parsedProject.target_language, "en-US");

const parsedProjectResponse = parseCreateProjectResponse({
  project: {
    id: UUID,
    schema_version: 1,
    name: "Project",
    status: "draft",
    source_language: "ja-JP",
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

const parsedRegionResponse = parsePageRegionResponse({
  region: {
    id: UUID_3,
    page_id: UUID_2,
    type: "speech_balloon",
    origin: "user_created",
    state: "approved",
    confidence: null,
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
});

assert.equal(parsedRegionResponse.region.state, "approved");

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

console.log("SHARED_CONTRACT_TESTS_OK");
