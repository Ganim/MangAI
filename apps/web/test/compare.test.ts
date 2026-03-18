import assert from "node:assert/strict";

import {
  clampComparePosition,
  getCompareDividerStyle,
  getCompareRevealStyle,
  resolveComparePositionFromSliderValue,
} from "../src/features/projects/compare.ts";

assert.equal(clampComparePosition(40), 40);
assert.equal(clampComparePosition(-15), 0);
assert.equal(clampComparePosition(125), 100);
assert.equal(clampComparePosition(Number.NaN), 50);

assert.equal(resolveComparePositionFromSliderValue("72"), 72);
assert.equal(resolveComparePositionFromSliderValue("-2"), 0);
assert.equal(resolveComparePositionFromSliderValue("abc"), 50);

assert.deepEqual(getCompareRevealStyle(65), {
  clipPath: "inset(0 35% 0 0)",
});

assert.deepEqual(getCompareDividerStyle(65), {
  left: "65%",
});

console.log("WEB_COMPARE_TESTS_OK");
