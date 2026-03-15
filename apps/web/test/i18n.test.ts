import assert from "node:assert/strict";

import { SUPPORTED_UI_LOCALES } from "@mangai/shared";

import { getMessages } from "../src/i18n/index.ts";
import { getDefaultLocalePath, resolveUiLocale } from "../src/i18n/routing.ts";

assert.equal(getDefaultLocalePath(), "/en-US");

for (const locale of SUPPORTED_UI_LOCALES) {
  const messages = getMessages(locale);

  assert.equal(messages.common.appName, "MangAI");
  assert.ok(messages.home.workflowItems.length > 0);
  assert.ok(messages.home.deliveryItems.length > 0);
}

assert.equal(resolveUiLocale("en-US"), "en-US");
assert.equal(resolveUiLocale("pt-BR"), "pt-BR");
assert.equal(resolveUiLocale("es-ES"), null);
assert.equal(resolveUiLocale(""), null);
assert.equal(resolveUiLocale(undefined), null);

assert.notEqual(getMessages("en-US").home.title, getMessages("pt-BR").home.title);

console.log("WEB_I18N_TESTS_OK");
