import assert from "node:assert/strict";

import {
  buildMaskRevisionInputFromRegion,
  countApprovedActiveMaskRevisions,
  getCleanupMaskCandidateRegions,
  getActiveMaskRevisionForRegion,
  hasApprovedActiveMaskRevisions,
} from "../src/features/projects/masks.ts";

const region = {
  id: "11111111-1111-4111-8111-111111111111",
  shape: {
    type: "polygon" as const,
    points: [
      { x: 10, y: 20 },
      { x: 110, y: 20 },
      { x: 110, y: 80 },
      { x: 10, y: 80 },
    ],
  },
};

const maskInput = buildMaskRevisionInputFromRegion(region);
assert.equal(maskInput.region_id, region.id);
assert.notEqual(maskInput.shape.points, region.shape.points);
assert.deepEqual(maskInput.shape.points[0], { x: 10, y: 20 });

const maskRevisions = [
  {
    id: "22222222-2222-4222-8222-222222222222",
    region_id: region.id,
    version: 1,
    is_active: false,
    approved: true,
    shape: region.shape,
  },
  {
    id: "33333333-3333-4333-8333-333333333333",
    region_id: region.id,
    version: 2,
    is_active: true,
    approved: false,
    shape: region.shape,
  },
  {
    id: "44444444-4444-4444-8444-444444444444",
    region_id: "55555555-5555-4555-8555-555555555555",
    version: 1,
    is_active: true,
    approved: true,
    shape: region.shape,
  },
];

assert.equal(getActiveMaskRevisionForRegion(maskRevisions, region.id)?.id, "33333333-3333-4333-8333-333333333333");
assert.equal(countApprovedActiveMaskRevisions(maskRevisions), 1);
assert.equal(hasApprovedActiveMaskRevisions(maskRevisions), true);
assert.equal(getActiveMaskRevisionForRegion(maskRevisions, "99999999-9999-4999-8999-999999999999"), null);
assert.deepEqual(
  getCleanupMaskCandidateRegions([
    { ...region, state: "approved" },
    { ...region, id: "66666666-6666-4666-8666-666666666666", state: "rejected" },
  ]).map((candidateRegion) => candidateRegion.id),
  [region.id],
);

console.log("WEB_MASK_TESTS_OK");
