import assert from "node:assert/strict";

import {
  SUPPORTED_UI_LOCALES,
  ValidationError,
  canonicalizeLanguageTag,
  inferTextDirectionForLanguage,
  normalizeUiLocale,
  parseCreateProjectRequest,
  parseDetectRegionsJobPayload,
  parseProject,
} from "../src/index.ts";

const UUID = "11111111-1111-4111-8111-111111111111";
const UUID_2 = "22222222-2222-4222-8222-222222222222";
const UUID_3 = "33333333-3333-4333-8333-333333333333";

assert.equal(canonicalizeLanguageTag("pt-br"), "pt-BR");
assert.deepEqual(SUPPORTED_UI_LOCALES, ["en-US", "pt-BR"]);

assert.throws(() => normalizeUiLocale("es-ES"), ValidationError);

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

const detectPayload = parseDetectRegionsJobPayload({
  job_id: UUID,
  page_id: UUID_2,
  asset_id: UUID_3,
});

assert.equal(detectPayload.page_id, UUID_2);

console.log("SHARED_CONTRACT_TESTS_OK");
