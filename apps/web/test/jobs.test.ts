import assert from "node:assert/strict";

import { hasPendingPageJobs } from "../src/features/projects/jobs.ts";

assert.equal(
  hasPendingPageJobs([
    { status: "queued" },
    { status: "succeeded" },
  ]),
  true,
);

assert.equal(
  hasPendingPageJobs([
    { status: "running" },
  ]),
  true,
);

assert.equal(
  hasPendingPageJobs([
    { status: "failed" },
    { status: "canceled" },
    { status: "succeeded" },
  ]),
  false,
);

console.log("WEB_JOB_TESTS_OK");
