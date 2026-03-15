import assert from "node:assert/strict";

import {
  buildDefaultRegionInput,
  formatRegionBounds,
  formatRegionIndexLabel,
  getPageCanvasSize,
  getRegionOverlayStyle,
} from "../src/features/projects/regions.ts";

const canvasSize = getPageCanvasSize({ width: 1600, height: 2400 });
assert.equal(canvasSize.width, 1600);
assert.equal(canvasSize.height, 2400);
assert.equal(canvasSize.usedFallback, false);

const fallbackCanvas = getPageCanvasSize({ width: null, height: null });
assert.equal(fallbackCanvas.width, 1000);
assert.equal(fallbackCanvas.height, 1400);
assert.equal(fallbackCanvas.usedFallback, true);

const defaultRegion = buildDefaultRegionInput({ width: 1600, height: 2400 });
assert.equal(defaultRegion.type, "speech_balloon");
assert.equal(defaultRegion.bounding_box.x, 256);
assert.equal(defaultRegion.bounding_box.height, 384);

const overlayStyle = getRegionOverlayStyle(
  {
    bounding_box: {
      x: 160,
      y: 240,
      width: 320,
      height: 480,
    },
  },
  { width: 1600, height: 2400 },
);

assert.equal(overlayStyle.left, "10%");
assert.equal(overlayStyle.top, "10%");
assert.equal(overlayStyle.width, "20%");
assert.equal(overlayStyle.height, "20%");
assert.equal(formatRegionBounds({ bounding_box: defaultRegion.bounding_box }), "256, 384 - 544 x 384");
assert.equal(formatRegionIndexLabel(0), "R01");
assert.equal(formatRegionIndexLabel(11), "R12");

console.log("WEB_REGION_TESTS_OK");
