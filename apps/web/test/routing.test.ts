import assert from "node:assert/strict";

import {
  buildProjectPageEditorHref,
  buildProjectWorkspaceHref,
} from "../src/features/projects/routing.ts";

assert.equal(
  buildProjectWorkspaceHref("en-US", "project-123"),
  "/en-US/projects/project-123",
);

assert.equal(
  buildProjectPageEditorHref("pt-BR", "project-123", "page-456"),
  "/pt-BR/projects/project-123/pages/page-456",
);

console.log("WEB_ROUTING_TESTS_OK");
