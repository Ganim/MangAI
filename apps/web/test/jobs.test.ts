import assert from "node:assert/strict";

import {
  hasPendingPageJobs,
  hasQueuedPageJobs,
  hasRunningPageJobs,
} from "../src/features/projects/jobs.ts";

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

assert.equal(
  hasQueuedPageJobs([
    { status: "queued" },
    { status: "succeeded" },
  ]),
  true,
);

assert.equal(
  hasQueuedPageJobs([
    { status: "running" },
    { status: "failed" },
  ]),
  false,
);

assert.equal(
  hasRunningPageJobs([
    { status: "running" },
    { status: "queued" },
  ]),
  true,
);

assert.equal(
  hasRunningPageJobs([
    { status: "queued" },
    { status: "failed" },
  ]),
  false,
);

console.log("WEB_JOB_TESTS_OK");
