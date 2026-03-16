import assert from "node:assert/strict";

import {
  countAvailableMatchingRegions,
  countOcrCandidateRegions,
  countUnassignedDialogues,
} from "../src/features/projects/automation.ts";

assert.equal(
  countOcrCandidateRegions([
    { type: "speech_balloon", state: "approved" },
    { type: "sfx", state: "approved" },
    { type: "free_text", state: "rejected" },
    { type: "unknown", state: "draft" },
  ]),
  2,
);

assert.equal(
  countUnassignedDialogues(
    [{ id: "d1" }, { id: "d2" }, { id: "d3" }],
    [
      { dialogue_id: "d1", approved: true },
      { dialogue_id: "d2", approved: false },
    ],
  ),
  2,
);

assert.equal(
  countAvailableMatchingRegions(
    [
      { id: "r1", type: "speech_balloon", state: "approved" },
      { id: "r2", type: "speech_balloon", state: "approved" },
      { id: "r3", type: "sfx", state: "approved" },
    ],
    [{ dialogue_id: "d1", region_id: "r1", approved: true }],
  ),
  1,
);
