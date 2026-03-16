import assert from "node:assert/strict";

import { resolveApiAssetUrl } from "../src/features/projects/api.ts";
import {
  buildUploadFormData,
  buildRegisterPagesPayload,
  createUploadQueue,
  formatBytes,
  removeUploadQueueItem,
} from "../src/features/projects/upload.ts";

const queueResult = createUploadQueue([
  { name: "002.png", type: "image/png", size: 4096 },
  { name: "001.jpg", type: "image/jpeg", size: 1024 },
  { name: "001.jpg", type: "image/jpeg", size: 1024 },
  { name: "script.txt", type: "text/plain", size: 100 },
]);

assert.equal(queueResult.accepted.length, 2);
assert.equal(queueResult.accepted[0]?.file_name, "001.jpg");
assert.equal(queueResult.accepted[1]?.file_name, "002.png");
assert.equal(queueResult.rejected.length, 2);
assert.equal(queueResult.rejected[0]?.reason, "duplicate_name");
assert.equal(queueResult.rejected[1]?.reason, "unsupported_type");

const reducedQueue = removeUploadQueueItem(queueResult.accepted, queueResult.accepted[0]!.client_id);
assert.equal(reducedQueue.length, 1);

const registerPayload = buildRegisterPagesPayload(queueResult.accepted);
assert.equal(registerPayload.pages.length, 2);
assert.equal(registerPayload.pages[0]?.width, null);

if (typeof File !== "undefined") {
  const uploadFiles = [
    new File(["alpha"], "002.png", { type: "image/png" }),
    new File(["beta"], "001.jpg", { type: "image/jpeg" }),
  ];
  const uploadQueue = createUploadQueue(uploadFiles).accepted;
  const formData = buildUploadFormData(uploadQueue);
  const entries = Array.from(formData.entries());

  assert.equal(entries.length, 2);
  assert.equal(entries[0]?.[0], "files");
}

assert.equal(formatBytes(500), "500 B");
assert.equal(formatBytes(2048), "2.0 KB");

const previousApiUrl = process.env.NEXT_PUBLIC_MANGAI_API_URL;
process.env.NEXT_PUBLIC_MANGAI_API_URL = "http://127.0.0.1:8001/api/v1";

assert.equal(
  resolveApiAssetUrl("/api/v1/projects/demo/pages/page-1/original"),
  "http://127.0.0.1:8001/api/v1/projects/demo/pages/page-1/original",
);

assert.equal(
  resolveApiAssetUrl("http://cdn.example.com/page.jpg"),
  "http://cdn.example.com/page.jpg",
);

if (previousApiUrl === undefined) {
  delete process.env.NEXT_PUBLIC_MANGAI_API_URL;
} else {
  process.env.NEXT_PUBLIC_MANGAI_API_URL = previousApiUrl;
}

console.log("WEB_PROJECT_TESTS_OK");
